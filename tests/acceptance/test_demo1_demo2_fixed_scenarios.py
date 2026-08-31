"""Repeatable acceptance gates for the Demo 1/2 product views.

These tests intentionally use the normal HarnessRuntime and HTTP routes with
small allowlisted test catalogs. They do not call a provider or an external
connector; the assertions are on server-owned lineage, admission, events and
artifact history.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from packages.contracts.harness_models import (
    AgentControlLoopArtifactFinding,
    AgentControlLoopCommit,
    AgentControlLoopControlRequest,
)
from services.api.app.api.harness_routes import get_harness_runtime
from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessRunStart,
    HarnessRuntime,
)
from services.api.app.application.readonly_workers import (
    ReadonlyWorkerContribution,
    ReadonlyWorkerRequest,
)
from services.api.app.main import create_app
from tests.unit.test_demo2_runtime import _cross_function_catalog
from tests.unit.test_harness_runtime import (
    AmbiguousCatalog,
    FakeAnalyst,
    FakeCatalog,
    FakePlanner,
    MixedEvidenceAnalyst,
)


async def _wait_for(runtime: HarnessRuntime, owner: str, run_id: str, predicate, *, seconds: float = 5):
    deadline = asyncio.get_running_loop().time() + seconds
    last = None
    while asyncio.get_running_loop().time() < deadline:
        snapshot = await runtime.get(owner, run_id)
        last = snapshot
        if predicate(snapshot):
            return snapshot
        await asyncio.sleep(0.01)
    raise AssertionError(
        f"run {run_id} did not reach the expected state: "
        f"status={getattr(last, 'status', None)!r}, "
        f"phase={getattr(last.rounds[-1], 'phase', None) if last and last.rounds else None!r}, "
        f"errors={getattr(last, 'validation_errors', None)!r}"
    )


class RevisionCatalog(AmbiguousCatalog):
    revision = "catalog-rev-1"

    def internal_workspace(self) -> dict[str, object]:
        workspace = super().internal_workspace()
        workspace["dataset_version"] = self.revision
        return workspace


@pytest.mark.asyncio
async def test_demo1_http_continuation_preserves_parent_and_limits_changed_source_scope() -> None:
    """The real /continue route creates a same-task child and preserves the parent."""

    owner = "demo1-acceptance-owner"
    catalog = RevisionCatalog()
    runtime = HarnessRuntime(catalog, FakePlanner(), MixedEvidenceAnalyst())
    try:
        started = await runtime.start(
            owner,
            HarnessRunStart(
                idempotency_key="demo1-acceptance-parent-0001",
                instruction="保留已完成事实并继续一个未完成分支",
                loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 6, "deadline_seconds": 120},
            ),
        )
        waiting = await _wait_for(
            runtime,
            owner,
            started.run.run_id,
            lambda item: item.status in {"waiting_input", "stopped"},
        )
        branch = next(item for item in waiting.branches if item.status != "completed")
        if waiting.status == "waiting_input":
            stopped = await runtime.control(
                owner,
                waiting.run_id,
                AgentControlLoopControlRequest(
                    command="stop",
                    expected_version=waiting.version,
                    idempotency_key="demo1-acceptance-stop-0001",
                ),
            )
            parent = await _wait_for(runtime, owner, stopped.run.run_id, lambda item: item.status == "stopped")
        else:
            parent = waiting

        # The bounded parent is intentionally seeded with the prior logical
        # commit so this gate covers preservation of both v1 and its pointer.
        if parent.last_commit is None:
            seeded_commit = AgentControlLoopCommit(
                commit_id="commit-000000000001",
                artifact_id=parent.artifact_versions[0].artifact_id,
                artifact_version=1,
                summary="父 Run 已保留的 v1 成果提交。",
                committed_at=datetime.now(timezone.utc),
            )
            async with runtime._lock:
                stored_run = runtime._runs[(owner, parent.run_id)]
                stored_run.snapshot = stored_run.snapshot.model_copy(
                    update={"commits": [seeded_commit], "last_commit": seeded_commit}
                )
                await runtime._persist_locked(stored_run)
            parent = await runtime.get(owner, parent.run_id)
        parent_dump = parent.model_dump(mode="json")
        parent_task_id = parent.task_id
        carried_refs = list(branch.missing_file_refs or branch.input_file_refs)
        assert any(item.status == "completed" for item in parent.branches)
        assert len(parent.artifact_versions) == 1
        assert parent.artifact_versions[0].version == 1
        assert parent.last_commit is not None
        parent_artifact_dump = parent.artifact_versions[0].model_dump(mode="json")
        parent_commit_dump = parent.last_commit.model_dump(mode="json")

        # A changed catalog revision requires rechecking the selected refs, but
        # does not turn continuation into a new task or broaden its scope.
        catalog.revision = "catalog-rev-2"
        app = create_app()
        app.dependency_overrides[get_harness_runtime] = lambda: runtime
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post(
                    f"/v1/harness/runs/{parent.run_id}/continue",
                    headers={"X-User-Id": owner},
                    json={
                        "branch_id": branch.branch_id,
                        "expected_version": parent.version,
                        "expected_task_version": parent.task_version,
                        "idempotency_key": "demo1-acceptance-child-0001",
                        "instruction": "请重新检查整个资料库并扩大范围。",
                    },
                )
            assert response.status_code == 202, response.text
            child = response.json()["run"]
            assert child["task_id"] == parent_task_id
            assert child["run_id"] != parent.run_id
            assert child["run_sequence"] == parent.run_sequence + 1
            assert child["parent_run_id"] == parent.run_id
            assert child["carried_branch_id"] == branch.branch_id
            assert child["source_revision_changed"] is True
            assert child["recheck_file_refs"] == carried_refs
            assert child["workspace_revision"] == catalog.revision
            child_snapshot = await runtime.get(owner, child["run_id"])
            child_refs = {
                ref
                for item in child_snapshot.branches
                for ref in (item.input_file_refs + item.missing_file_refs)
            }
            assert child_refs <= set(carried_refs)
            # Parent history is byte-for-byte unchanged after child creation.
            parent_after = await runtime.get(owner, parent.run_id)
            assert parent_after.model_dump(mode="json") == parent_dump
            assert parent_after.artifact_versions[0].model_dump(mode="json") == parent_artifact_dump
            assert parent_after.last_commit.model_dump(mode="json") == parent_commit_dump

            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                replay = await client.post(
                    f"/v1/harness/runs/{parent.run_id}/continue",
                    headers={"X-User-Id": owner},
                    json={
                        "branch_id": branch.branch_id,
                        "expected_version": parent.version,
                        "expected_task_version": parent.task_version,
                        "idempotency_key": "demo1-acceptance-child-0001",
                        "instruction": "请重新检查整个资料库并扩大范围。",
                    },
                )
                stale = await client.post(
                    f"/v1/harness/runs/{parent.run_id}/continue",
                    headers={"X-User-Id": owner},
                    json={
                        "branch_id": branch.branch_id,
                        "expected_version": parent.version - 1,
                        "expected_task_version": parent.task_version,
                        "idempotency_key": "demo1-acceptance-stale-0001",
                    },
                )
                forbidden = await client.post(
                    f"/v1/harness/runs/{parent.run_id}/continue",
                    headers={"X-User-Id": "other-owner"},
                    json={
                        "branch_id": branch.branch_id,
                        "expected_version": parent.version,
                        "expected_task_version": parent.task_version,
                        "idempotency_key": "demo1-acceptance-owner-0001",
                    },
                )
            assert replay.status_code == 202
            assert replay.json()["run"]["run_id"] == child["run_id"]
            assert stale.status_code == 409
            assert forbidden.status_code in {403, 404}

            # A historical parent cannot fork a second child after its task
            # pointer advanced, even when the source revision is unchanged.
            catalog.revision = "catalog-rev-1"
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                unchanged_response = await client.post(
                    f"/v1/harness/runs/{parent.run_id}/continue",
                    headers={"X-User-Id": owner},
                    json={
                        "branch_id": branch.branch_id,
                        "expected_version": parent.version,
                        "expected_task_version": 2,
                        "idempotency_key": "demo1-acceptance-child-0002",
                    },
                )
            # The task pointer now targets the first child; attempting to
            # continue the historical parent is rejected even at the same
            # source revision, so no second child can fork stale lineage.
            assert unchanged_response.status_code == 409, unchanged_response.text
        finally:
            app.dependency_overrides.clear()
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_demo1_unchanged_revision_continuation_succeeds_in_independent_runtime() -> None:
    """An unchanged source revision is a successful child flow, not a stale-parent fork."""

    owner = "demo1-unchanged-acceptance-owner"
    catalog = RevisionCatalog()
    runtime = HarnessRuntime(catalog, FakePlanner(), MixedEvidenceAnalyst())
    try:
        started = await runtime.start(
            owner,
            HarnessRunStart(
                idempotency_key="demo1-unchanged-parent-0001",
                instruction="保留已完成事实并继续一个未完成分支",
                loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 6, "deadline_seconds": 120},
            ),
        )
        waiting = await _wait_for(runtime, owner, started.run.run_id, lambda item: item.status in {"waiting_input", "stopped"})
        branch = next(item for item in waiting.branches if item.status != "completed")
        parent = waiting
        if waiting.status == "waiting_input":
            stopped = await runtime.control(
                owner,
                waiting.run_id,
                AgentControlLoopControlRequest(
                    command="stop",
                    expected_version=waiting.version,
                    idempotency_key="demo1-unchanged-stop-0001",
                ),
            )
            parent = await _wait_for(runtime, owner, stopped.run.run_id, lambda item: item.status == "stopped")
        child = await runtime.continue_unfinished_task(
            owner,
            parent.run_id,
            branch.branch_id,
            idempotency_key="demo1-unchanged-child-0001",
            expected_version=parent.version,
            expected_task_version=parent.task_version,
        )
        assert child.run.task_id == parent.task_id
        assert child.run.run_sequence == parent.run_sequence + 1
        assert child.run.source_revision_changed is False
        assert child.run.recheck_file_refs == list(branch.missing_file_refs or branch.input_file_refs)
    finally:
        await runtime.close()


class FiveUnitFailurePlanner:
    model = "test-planner"

    def __init__(self) -> None:
        self.calls = 0

    async def plan(self, *, scenario, files):
        self.calls += 1
        refs = [str(item["file_ref"]) for item in files]
        return HarnessPlanCandidate(
            summary="三条独立分支与两条依赖分支",
            selection_reason="服务端冻结来源结构允许首波并行",
            units=[
                *[
                    HarnessPlanCandidateUnit(
                        unit_id=f"root-{index}",
                        title=f"独立工作包 {index}",
                        objective="只读核对批准来源",
                        input_file_refs=[refs[(index - 1) % len(refs)]],
                        tool="file.read",
                    )
                    for index in (1, 2, 3)
                ],
                HarnessPlanCandidateUnit(
                    unit_id="dependent-blocked",
                    title="依赖歧义分支",
                    objective="等待第三个根分支确定后继续",
                    input_file_refs=[refs[0]],
                    depends_on=["root-3"],
                    tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="dependent-ready",
                    title="依赖已采用分支",
                    objective="在第一个根分支后继续核对",
                    input_file_refs=[refs[1]],
                    depends_on=["root-1"],
                    tool="file.read",
                ),
            ],
        )


@pytest.mark.asyncio
async def test_demo2_failure_wave_keeps_adopted_contributions_and_blocks_only_downstream() -> None:
    """A mixed worker wave creates a partial v1, not a group failure."""

    owner = "demo2-acceptance-owner"
    planner = FiveUnitFailurePlanner()

    class CountingAnalyst(FakeAnalyst):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def analyze(self, **kwargs):
            self.calls += 1
            kwargs.pop("verified_effect_context", None)
            return await super().analyze(**kwargs)

    analyst = CountingAnalyst()
    runtime = HarnessRuntime(_cross_function_catalog(), planner, analyst)
    try:
        started = await runtime.start(
            owner,
            HarnessRunStart(
                idempotency_key="demo2-acceptance-start-0001",
                instruction="核对五个跨职能工作包并保留局部成果",
                loop={"max_rounds": 2, "max_files_per_round": 3, "max_model_calls": 8, "deadline_seconds": 120},
            ),
        )
        waiting = await _wait_for(runtime, owner, started.run.run_id, lambda item: item.status == "waiting_input")
        assert waiting.topology_admission is not None
        assert waiting.topology_admission.mode == "adaptive_readonly_workers"
        roots = {item.unit_id: item for item in waiting.branches if item.status == "running"}
        assert set(roots) == {"root-1", "root-2", "root-3"}
        assert len(waiting.worker_runs) == 0
        assert any(event.event_name == "topology_confirmation_required" for event in waiting.events)
        assert planner.calls == 1
        assert analyst.calls == 0
        worker_calls = 0

        async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            nonlocal worker_calls
            worker_calls += 1
            branch = next(item for item in waiting.branches if item.branch_id == request.branch_id)
            adopted = branch.unit_id in {"root-1", "root-2", "dependent-ready"}
            if not adopted:
                return ReadonlyWorkerContribution(
                    worker_run_id=request.worker_run_id,
                    branch_id=request.branch_id,
                    outcome="ambiguous",
                    summary="原文位置有多个候选，等待人工选择。",
                    source_file_refs=request.source_file_refs,
                    evidence_anchors=(),
                    model_called=True,
                    output_used=False,
                    elapsed_ms=2,
                )
            finding = AgentControlLoopArtifactFinding(
                finding_id=f"finding-{branch.branch_id[-12:]}",
                plan_unit_id=branch.unit_id,
                affected_branch_ids=[branch.branch_id],
                title=f"{branch.title} 已核对",
                detail="只读 Worker 贡献通过来源范围与 Anchor 门。",
                file_refs=list(request.source_file_refs),
            )
            return ReadonlyWorkerContribution(
                worker_run_id=request.worker_run_id,
                branch_id=request.branch_id,
                outcome="adopted",
                summary="已形成可审查贡献。",
                source_file_refs=request.source_file_refs,
                evidence_anchors=("line:1",),
                model_called=True,
                output_used=True,
                elapsed_ms=2,
                findings=(finding,),
            )

        requests = [
            ReadonlyWorkerRequest(
                worker_run_id=f"acceptance-worker-{unit}",
                branch_id=roots[unit].branch_id,
                goal=roots[unit].objective,
                source_file_refs=tuple(roots[unit].input_file_refs),
                expected_version=waiting.version,
            )
            for unit in ("root-1", "root-2", "root-3")
        ]
        first = await runtime.execute_admitted_readonly_workers(
            owner,
            started.run.run_id,
            expected_version=waiting.version,
            idempotency_key="demo2-acceptance-wave-0001",
            worker_requests=requests,
            handler=handler,
            user_confirmed=True,
        )
        assert planner.calls == 1
        assert analyst.calls == 0
        assert worker_calls == 3
        assert first.status == "waiting_input"
        assert len(first.worker_runs) == 3
        assert len(first.artifact_versions) == 1
        assert first.artifact_versions[0].version == 1
        assert first.artifact_versions[0].finding_count == 2
        assert first.shared_artifacts[-1].version == 1
        assert {item.outcome for item in first.worker_runs} == {"adopted", "ambiguous"}
        branches = {item.unit_id: item for item in first.branches}
        assert branches["root-1"].status == "completed"
        assert branches["root-2"].status == "completed"
        assert branches["root-3"].status == "waiting_input"
        assert branches["dependent-ready"].status == "running"
        assert branches["dependent-blocked"].status == "blocked"
        assert set(first.rounds[-1].next_step.ready_branch_ids) == {branches["dependent-ready"].branch_id}
        assert any(event.event_name == "contribution_adopted" for event in first.events)
        assert any(event.event_name == "contribution_waiting" for event in first.events)
        assert first.last_commit is not None
        assert first.last_commit.artifact_version == 1

        # The ready dependent is the only legal second-wave dispatch.  The
        # ambiguous root keeps its downstream blocked and cannot be smuggled
        # into the next batch by a client-selected branch list.
        v1_dump = first.artifact_versions[0].model_dump(mode="json")
        ready = next(item for item in first.branches if item.unit_id == "dependent-ready")
        blocked = next(item for item in first.branches if item.unit_id == "dependent-blocked")
        assert blocked.status == "blocked"
        blocked_before = first.model_dump(mode="json")
        with pytest.raises(HarnessConflictError):
            await runtime.execute_admitted_readonly_workers(
                owner,
                started.run.run_id,
                expected_version=first.version,
                idempotency_key="demo2-acceptance-blocked-0001",
                worker_requests=[
                    ReadonlyWorkerRequest(
                        worker_run_id="acceptance-worker-dependent-blocked",
                        branch_id=blocked.branch_id,
                        goal=blocked.objective,
                        source_file_refs=tuple(blocked.input_file_refs),
                        expected_version=first.version,
                    )
                ],
                handler=handler,
                user_confirmed=True,
            )
        assert (await runtime.get(owner, started.run.run_id)).model_dump(mode="json") == blocked_before
        second = await runtime.execute_admitted_readonly_workers(
            owner,
            started.run.run_id,
            expected_version=first.version,
            idempotency_key="demo2-acceptance-wave-0002",
            worker_requests=[
                ReadonlyWorkerRequest(
                    worker_run_id="acceptance-worker-dependent-ready",
                    branch_id=ready.branch_id,
                    goal=ready.objective,
                    source_file_refs=tuple(ready.input_file_refs),
                    expected_version=first.version,
                )
            ],
            handler=handler,
            user_confirmed=True,
        )
        assert [item.version for item in second.artifact_versions] == [1, 2]
        assert second.artifact_versions[0].model_dump(mode="json") == v1_dump
        assert second.artifact_versions[1].finding_count == 3
        assert second.last_commit is not None and second.last_commit.artifact_version == 2
        assert len(second.worker_runs) == 4
        assert worker_calls == 4
        assert analyst.calls == 0
        assert planner.calls == 1
        statuses = {item.unit_id: item.status for item in second.branches}
        assert statuses["dependent-ready"] == "completed"
        assert statuses["dependent-blocked"] == "blocked"
        assert any(event.event_name == "topology_workers_completed" for event in second.events)
    finally:
        await runtime.close()


class ThreePeriodFinanceCatalog(FakeCatalog):
    def __init__(self) -> None:
        super().__init__()
        extra = dict(self.files[0])
        extra.update(
            file_ref="forte-3333333333333333",
            path="Finance-018/input/2024.csv",
            display_label="2024 往来明细.csv",
            display_path="财务管理/2024 往来明细.csv",
            sha256="c" * 64,
        )
        self.files.append(extra)


class ThreePeriodPlanner:
    model = "test-planner"
    calls = 0

    async def plan(self, *, scenario, files):
        self.calls += 1
        refs = [str(item["file_ref"]) for item in files]
        return HarnessPlanCandidate(
            summary="三期同结构财务顺序核对",
            selection_reason="同一目录、同一表结构和同一只读工具",
            units=[
                HarnessPlanCandidateUnit(
                    unit_id=f"period-{index}",
                    title=f"第 {index} 期",
                    objective="核对同口径财务明细",
                    input_file_refs=[ref],
                    tool="file.read",
                )
                for index, ref in enumerate(refs, 1)
            ],
        )


@pytest.mark.asyncio
async def test_demo2_same_schema_three_period_finance_stays_fixed_without_worker_route() -> None:
    """Three same-structure periods use the conservative fixed workflow."""

    owner = "demo2-finance-acceptance-owner"
    planner = ThreePeriodPlanner()
    class CountingAnalyst(FakeAnalyst):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def analyze(self, **kwargs):
            self.calls += 1
            kwargs.pop("verified_effect_context", None)
            return await super().analyze(**kwargs)

    analyst = CountingAnalyst()
    runtime = HarnessRuntime(ThreePeriodFinanceCatalog(), planner, analyst)
    try:
        started = await runtime.start(
            owner,
            HarnessRunStart(
                idempotency_key="demo2-finance-start-0001",
                instruction="顺序核对三期同结构财务明细，请用多个 Agent 并行处理。",
                loop={"max_rounds": 1, "max_files_per_round": 3, "max_model_calls": 6, "deadline_seconds": 120},
            ),
        )
        final = await _wait_for(
            runtime,
            owner,
            started.run.run_id,
            lambda item: item.status in {"completed", "waiting_input", "stopped", "failed"},
        )
        assert final.topology_admission is not None
        assert final.topology_admission.mode == "fixed_workflow"
        assert final.topology_admission.user_confirmation_required is False
        assert final.worker_runs == []
        assert not any(event.event_name == "topology_confirmation_required" for event in final.events)
        assert planner.calls == 1
        assert final.model_receipt is not None and final.model_receipt.called is True
        assert final.analysis_receipt is not None and final.analysis_receipt.called is True
        assert analyst.calls == 1
        assert not any(
            "worker" in event.event_name or "contribution" in event.event_name
            for event in final.events
        )
        assert final.status != "failed"
    finally:
        await runtime.close()
