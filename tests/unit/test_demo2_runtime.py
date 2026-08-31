from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time

import httpx
import pytest
from fastapi.routing import APIRoute

from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessPlan,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessPlanUnit,
    HarnessRunStart,
    HarnessRuntime,
)
from packages.contracts.harness_models import (
    AgentControlLoopArtifactFinding,
    AgentControlLoopArtifactVersion,
    AgentControlLoopControlRequest,
)
from services.api.app.application.readonly_workers import (
    ReadonlyWorkerContribution,
    ReadonlyWorkerRequest,
    execute_readonly_workers,
    merge_adopted_contributions,
)
from services.api.app.application.topology_admission import admit_topology
from services.api.app.application.workunit_ledger import WorkUnitState
from services.api.app.application.harness_storage import InMemoryHarnessStateStore
from packages.contracts.harness_models import AgentControlLoopNarrativeReconciliation
from services.api.app.main import create_app
from services.api.app.api.harness_routes import get_harness_runtime


def _cross_function_catalog():
    """Give runtime admission explicit, server-frozen cross-function facts."""
    from tests.unit.test_harness_runtime import FakeCatalog

    class CrossFunctionCatalog(FakeCatalog):
        def public_file(self, file_ref: str):
            payload = super().public_file(file_ref)
            first_ref = self.files[0]["file_ref"]
            payload["display_group"] = "销售" if file_ref == first_ref else "工程"
            return payload

    return CrossFunctionCatalog()


def _plan(*, risky: bool = False) -> HarnessPlan:
    return HarnessPlan(
        summary="两个独立的只读核对工作包",
        selection_reason="来自服务端已校验的计划。",
        units=[
            HarnessPlanUnit(
                unit_id="u1",
                title="核对一",
                objective="核对第一份资料",
                input_file_refs=["forte-1111111111111111"],
                tool="file.read",
                side_effect="run_workspace_write" if risky else "none",
            ),
            HarnessPlanUnit(
                unit_id="u2",
                title="核对二",
                objective="核对第二份资料",
                input_file_refs=["forte-2222222222222222"],
                tool="file.read",
            ),
        ],
    )


def test_admission_uses_validated_facts_and_never_admits_risky_workers() -> None:
    admitted = admit_topology(_plan(), remaining_model_calls=8, remaining_time_seconds=120)
    assert admitted.mode == "adaptive_readonly_workers"
    assert admitted.independent_branch_count == 2
    assert admitted.external_action == "none"
    assert admitted.user_confirmation_required is True

    fixed = admit_topology(_plan(risky=True), remaining_model_calls=8, remaining_time_seconds=120)
    assert fixed.mode == "fixed_workflow"
    assert fixed.user_confirmation_required is False
    assert any("人工门" in reason or "副作用" in reason for reason in fixed.reasons)

    low_budget = admit_topology(_plan(), remaining_model_calls=1, remaining_time_seconds=120)
    assert low_budget.mode == "fixed_workflow"

    oversized = HarnessPlan(
        summary="四个只读工作包",
        selection_reason="服务端验证",
        units=[
            HarnessPlanUnit(
                unit_id=f"u{index}",
                title=f"工作包 {index}",
                objective="独立核对资料",
                input_file_refs=[f"forte-{index:016x}"],
                tool="file.read",
            )
            for index in range(4)
        ],
    )
    assert admit_topology(oversized, remaining_model_calls=20, remaining_time_seconds=120).mode == "fixed_workflow"


def test_single_controller_is_selected_when_only_one_independent_branch_exists() -> None:
    plan = _plan()
    plan.units[1].depends_on = ["u1"]
    admitted = admit_topology(plan, remaining_model_calls=8, remaining_time_seconds=120)
    assert admitted.mode == "single_controller"
    assert admitted.independent_branch_count == 1


def test_same_schema_finance_is_fixed_but_cross_function_independent_work_can_adapt() -> None:
    finance_plan = HarnessPlan(
        summary="三期同结构财务资料",
        selection_reason="服务端验证",
        units=[
            HarnessPlanUnit(
                unit_id=f"period-{index}",
                title=f"第 {index} 期",
                objective="核对同结构财务明细",
                input_file_refs=[f"forte-{index:016x}"],
                tool="file.read",
            )
            for index in range(1, 4)
        ],
    )
    same_schema = {
        f"forte-{index:016x}": {
            "display_group": "财务管理",
            "display_path": f"财务管理/{index}期.csv",
            "mime": "text/csv",
            "kind": "table",
            "columns": ["客商", "余额"],
        }
        for index in range(1, 4)
    }
    fixed = admit_topology(
        finance_plan,
        remaining_model_calls=20,
        remaining_time_seconds=120,
        source_facts=same_schema,
    )
    assert fixed.mode == "fixed_workflow"
    assert any("同结构" in reason for reason in fixed.reasons)

    cross_function = finance_plan.model_copy(
        update={
            "units": [
                item.model_copy(update={"input_file_refs": [f"forte-{index:016x}"]})
                for index, item in enumerate(finance_plan.units, start=1)
            ]
        }
    )
    cross_facts = {
        f"forte-{index:016x}": {
            "display_group": group,
            "display_path": f"{group}/input-{index}.txt",
            "mime": "text/plain",
            "kind": "text",
            "columns": [],
        }
        for index, group in enumerate(("财务管理", "法务审查", "工程交付"), start=1)
    }
    adaptive = admit_topology(
        cross_function,
        remaining_model_calls=20,
        remaining_time_seconds=120,
        source_facts=cross_facts,
    )
    assert adaptive.mode == "adaptive_readonly_workers"


def test_demo2_uses_unified_harness_routes_not_a_demo_selector() -> None:
    paths: set[str] = set()
    for included in create_app().routes:
        router = getattr(included, "original_router", included)
        routes = getattr(router, "routes", [router])
        paths.update(route.path for route in routes if isinstance(route, APIRoute))
    assert "/v1/harness/runs/{run_id}/workers" in paths
    assert "/v1/harness/runs/{run_id}/continue" in paths
    assert not any(path.startswith("/v1/demo2") for path in paths)


@pytest.mark.asyncio
async def test_adaptive_wait_persists_plan_and_override_reuses_same_round() -> None:
    from tests.unit.test_harness_runtime import FakeAnalyst

    class TwoIndependentPlanner:
        model = "test-planner"

        def __init__(self) -> None:
            self.calls = 0

        async def plan(self, *, scenario, files):
            self.calls += 1
            refs = [str(item["file_ref"]) for item in files[:2]]
            return HarnessPlanCandidate(
                summary="两个独立只读工作包",
                selection_reason="服务端计划校验",
                units=[
                    HarnessPlanCandidateUnit(
                        unit_id=f"independent-{index}",
                        title="独立资料核对",
                        objective="核对一份批准来源",
                        input_file_refs=[ref],
                        tool="file.read",
                    )
                    for index, ref in enumerate(refs, start=1)
                ],
            )

    class CountingAnalyst(FakeAnalyst):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        async def analyze(self, *, instruction, plan, files, validation_feedback=None):
            self.calls += 1
            return await super().analyze(
                instruction=instruction,
                plan=plan,
                files=files,
                validation_feedback=validation_feedback,
            )

    planner = TwoIndependentPlanner()
    analyst = CountingAnalyst()
    runtime = HarnessRuntime(_cross_function_catalog(), planner, analyst)
    request = HarnessRunStart(
        idempotency_key="adaptive-plan-start-0001",
        instruction="核对两份独立资料",
        loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 4, "deadline_seconds": 120},
    )
    started = await runtime.start("alice", request)
    waiting = None
    for _ in range(300):
        candidate = await runtime.get("alice", started.run.run_id)
        if candidate.status == "waiting_input" and candidate.topology_admission is not None:
            waiting = candidate
            break
        await asyncio.sleep(0.01)
    assert waiting is not None
    assert waiting.topology_admission.mode == "adaptive_readonly_workers"
    assert waiting.rounds[0].plan is not None
    assert analyst.calls == 0
    override = await runtime.control(
        "alice",
        started.run.run_id,
        AgentControlLoopControlRequest(
            command="topology_override",
            topology_mode="single_controller",
            idempotency_key="adaptive-override-0001",
            expected_version=waiting.version,
        ),
    )
    assert override.run.run_sequence == waiting.run_sequence
    for _ in range(300):
        final = await runtime.get("alice", started.run.run_id)
        if final.status in {"completed", "failed", "stopped", "ready_to_execute"}:
            break
        await asyncio.sleep(0.01)
    assert planner.calls == 1
    assert analyst.calls == 1, (final.status, final.control_state, [(e.event_name, e.message) for e in final.events], final.validation_errors)


@pytest.mark.asyncio
async def test_demo1_continuation_creates_child_run_with_exact_carried_branch_scope() -> None:
    """A bounded terminal Run continues as a new Run, never as an in-place resume."""
    from tests.unit.test_harness_runtime import AlwaysUnlocatableAnalyst, FakeCatalog, FakePlanner

    class RevisableCatalog(FakeCatalog):
        revision = "revision-v1"

        def internal_workspace(self) -> dict[str, object]:
            workspace = super().internal_workspace()
            workspace["dataset_version"] = self.revision
            return workspace

    catalog = RevisableCatalog()
    runtime = HarnessRuntime(catalog, FakePlanner(), AlwaysUnlocatableAnalyst())
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="demo1-parent-start-0001",
            instruction="核对跨期资料并保留未完成分支",
            loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 6, "deadline_seconds": 120},
        ),
    )
    parent = None
    for _ in range(400):
        candidate = await runtime.get("alice", started.run.run_id)
        if candidate.status in {"waiting_input", "stopped"}:
            parent = candidate
            break
        await asyncio.sleep(0.01)
    assert parent is not None
    if parent.status == "stopped":
        terminal = parent
    else:
        stopped = await runtime.control(
            "alice",
            parent.run_id,
            AgentControlLoopControlRequest(
                command="stop",
                idempotency_key="demo1-parent-stop-0001",
                expected_version=parent.version,
            ),
        )
        terminal = None
        for _ in range(400):
            candidate = await runtime.get("alice", stopped.run.run_id)
            if candidate.status == "stopped":
                terminal = candidate
                break
            await asyncio.sleep(0.01)
        assert terminal is not None
    branch = next(item for item in terminal.branches if item.status != "completed")
    old_dump = terminal.model_dump(mode="json")
    expected_refs = tuple(branch.missing_file_refs or branch.input_file_refs)
    catalog.revision = "revision-v2"
    child = await runtime.continue_unfinished_task(
        "alice",
        terminal.run_id,
        branch.branch_id,
        idempotency_key="demo1-child-continue-0001",
        expected_version=terminal.version,
        expected_task_version=terminal.task_version,
    )
    assert child.run.task_id == terminal.task_id
    assert child.run.run_id != terminal.run_id
    assert child.run.run_sequence == terminal.run_sequence + 1
    assert tuple(child.run.recheck_file_refs) == expected_refs
    assert child.run.carried_branch_id == branch.branch_id
    assert child.run.source_revision_changed is True
    assert terminal.model_dump(mode="json") == old_dump
    public_child = runtime.public_snapshot(child.run)
    assert public_child.source_revision_changed is True
    assert tuple(public_child.recheck_file_refs) == expected_refs
    with pytest.raises(HarnessConflictError, match="版本"):
        await runtime.continue_unfinished_task(
            "alice", terminal.run_id, branch.branch_id,
            idempotency_key="demo1-child-stale-0001", expected_version=terminal.version - 1,
            expected_task_version=terminal.task_version,
        )
    with pytest.raises(Exception, match="不存在"):
        await runtime.continue_unfinished_task(
            "bob", terminal.run_id, branch.branch_id,
            idempotency_key="demo1-child-owner-0001", expected_version=terminal.version,
            expected_task_version=terminal.task_version,
        )
    replay = await runtime.continue_unfinished_task(
        "alice",
        terminal.run_id,
        branch.branch_id,
        idempotency_key="demo1-child-continue-0001",
        expected_version=terminal.version,
        expected_task_version=terminal.task_version,
    )
    assert replay.run.run_id == child.run.run_id
    await runtime.close()


@pytest.mark.asyncio
async def test_demo1_continuation_http_route_returns_same_task_child_run() -> None:
    from tests.unit.test_harness_runtime import AlwaysUnlocatableAnalyst, FakeCatalog, FakePlanner

    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), AlwaysUnlocatableAnalyst())
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="demo1-http-parent-0001",
            instruction="为未完成分支创建连续任务",
            loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 6, "deadline_seconds": 120},
        ),
    )
    terminal = None
    for _ in range(500):
        candidate = await runtime.get("alice", started.run.run_id)
        if candidate.status in {"stopped", "failed", "completed"}:
            terminal = candidate
            break
        await asyncio.sleep(0.01)
    assert terminal is not None and terminal.status == "stopped"
    branch = next(item for item in terminal.branches if item.status != "completed")
    app = create_app()
    app.dependency_overrides[get_harness_runtime] = lambda: runtime
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/v1/harness/runs/{terminal.run_id}/continue",
                headers={"X-User-Id": "alice"},
                json={
                        "branch_id": branch.branch_id,
                        "idempotency_key": "demo1-http-child-0001",
                        "expected_version": terminal.version,
                        "expected_task_version": terminal.task_version,
                },
            )
        assert response.status_code == 202
        child = response.json()["run"]
        assert child["task_id"] == terminal.task_id
        assert child["run_id"] != terminal.run_id
        assert child["run_sequence"] == terminal.run_sequence + 1
        assert child["source_revision_changed"] is False
        assert child["recheck_file_refs"] == list(branch.missing_file_refs or branch.input_file_refs)
    finally:
        app.dependency_overrides.clear()
        await runtime.close()


@pytest.mark.asyncio
async def test_five_unit_dag_runtime_advances_from_roots_to_second_worker_wave() -> None:
    from tests.unit.test_harness_runtime import FakeAnalyst

    class FiveUnitDagPlanner:
        model = "test-planner"

        async def plan(self, *, scenario, files):
            refs = [str(item["file_ref"]) for item in files]
            roots = [
                HarnessPlanCandidateUnit(
                    unit_id=f"u{index}", title=f"独立分支 {index}", objective=f"核对独立事实 {index}",
                    input_file_refs=[refs[(index - 1) % len(refs)]], tool="file.read",
                )
                for index in (1, 2, 3)
            ]
            dependents = [
                HarnessPlanCandidateUnit(
                    unit_id="u4", title="依赖分支 4", objective="在独立事实 1 上继续复核",
                    input_file_refs=[refs[0]], depends_on=["u1"], tool="file.read",
                ),
                HarnessPlanCandidateUnit(
                    unit_id="u5", title="依赖分支 5", objective="在独立事实 2 上继续复核",
                    input_file_refs=[refs[1]], depends_on=["u2"], tool="file.read",
                ),
            ]
            return HarnessPlanCandidate(
                summary="三条独立分支与两条依赖分支",
                selection_reason="服务端校验的 DAG",
                units=roots + dependents,
            )

    runtime = HarnessRuntime(_cross_function_catalog(), FiveUnitDagPlanner(), FakeAnalyst())
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="five-unit-runtime-start-0001",
            instruction="核对五条有依赖关系的办公事实",
            loop={"max_rounds": 2, "max_files_per_round": 2, "max_model_calls": 8, "deadline_seconds": 120},
        ),
    )
    deadline = time.monotonic() + 3
    waiting = None
    while time.monotonic() < deadline:
        candidate = await runtime.get("alice", started.run.run_id)
        if candidate.status == "waiting_input" and candidate.topology_admission is not None:
            waiting = candidate
            break
        await asyncio.sleep(0.01)
    assert waiting is not None
    assert waiting.topology_admission.mode == "adaptive_readonly_workers"
    by_unit = {item.unit_id: item for item in waiting.branches}
    by_branch = {item.branch_id: item for item in waiting.branches}
    assert [by_unit[f"u{index}"].status for index in (1, 2, 3)] == ["running"] * 3
    assert [by_unit[f"u{index}"].status for index in (4, 5)] == ["pending"] * 2

    async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        return ReadonlyWorkerContribution(
            worker_run_id=request.worker_run_id,
            branch_id=request.branch_id,
            outcome="adopted",
            summary="已通过服务端来源核对",
            source_file_refs=request.source_file_refs,
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
            findings=(
                AgentControlLoopArtifactFinding(
                    finding_id=f"finding-{request.branch_id[-12:]}",
                        plan_unit_id=by_branch[request.branch_id].unit_id,
                    affected_branch_ids=[request.branch_id],
                        title=f"{request.branch_id} 已核对",
                    detail="该分支贡献已通过来源定位门。",
                    file_refs=list(request.source_file_refs),
                ),
            ),
        )

    def requests_for(snapshot, unit_ids, suffix):
        return [
            ReadonlyWorkerRequest(
                worker_run_id=f"worker-{unit_id}-{suffix}", branch_id=by_unit[unit_id].branch_id,
                goal=by_unit[unit_id].objective, source_file_refs=tuple(by_unit[unit_id].input_file_refs),
                expected_version=snapshot.version,
            )
            for unit_id in unit_ids
        ]

    first = await runtime.execute_admitted_readonly_workers(
        "alice", started.run.run_id, expected_version=waiting.version,
        idempotency_key="five-unit-wave-0001", worker_requests=requests_for(waiting, ("u1", "u2", "u3"), "one"),
        handler=handler, user_confirmed=True,
    )
    assert len(first.work_units) == 5
    first_units = {item.unit_id: item for item in first.work_units}
    assert [first_units[f"u{index}"].state for index in (1, 2, 3)] == [WorkUnitState.ADOPTED] * 3
    assert [first_units[f"u{index}"].state for index in (4, 5)] == [WorkUnitState.READY] * 2
    assert len(first.contributions) == 3
    ready_units = {item.unit_id for item in first.branches if item.status == "running"}
    assert ready_units == {"u4", "u5"}, [(item.unit_id, item.status) for item in first.branches]
    assert set(first.rounds[-1].next_step.ready_branch_ids) == {
        by_unit[unit_id].branch_id for unit_id in ready_units
    }

    by_unit = {item.unit_id: item for item in first.branches}
    by_branch = {item.branch_id: item for item in first.branches}
    second = await runtime.execute_admitted_readonly_workers(
        "alice", started.run.run_id, expected_version=first.version,
        idempotency_key="five-unit-wave-0002", worker_requests=requests_for(first, ("u4", "u5"), "two"),
        handler=handler, user_confirmed=True,
    )
    assert second.status == "completed"
    assert all(item.status == "completed" for item in second.branches)
    assert [item.version for item in second.artifact_versions] == [1, 2]
    assert [item.version for item in second.shared_artifacts] == [1, 2]
    assert len({item.artifact_id for item in second.artifact_versions}) == 1
    assert second.artifact_versions[0].finding_count == 3
    assert second.artifact_versions[1].finding_count == 5
    assert len(second.work_units) == 5
    assert {item.state for item in second.work_units} == {"adopted"}
    assert len(second.contributions) == 5
    assert all(item.artifact_version in {1, 2} for item in second.contributions)
    assert [event.event_name for event in second.events].count("worker_wave_reserved") == 2
    assert [event.event_name for event in second.events].count("worker_wave_committed") == 2


@pytest.mark.asyncio
async def test_runtime_artifact_version_keeps_eleven_worker_findings() -> None:
    """The normal Runtime ArtifactVersion contract must not reintroduce a top-10 cap."""

    class TwoUnitPlanner:
        model = "test-planner"

        async def plan(self, *, scenario, files):
            refs = [str(item["file_ref"]) for item in files[:2]]
            return HarnessPlanCandidate(
                summary="两个只读工作包",
                selection_reason="服务端计划校验",
                units=[
                    HarnessPlanCandidateUnit(
                        unit_id=f"unit-{index}",
                        title=f"工作包 {index}",
                        objective="核对一份批准资料",
                        input_file_refs=[ref],
                        tool="file.read",
                    )
                    for index, ref in enumerate(refs, start=1)
                ],
            )

    runtime = HarnessRuntime(_cross_function_catalog(), TwoUnitPlanner(), None)
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="artifact-eleven-start-0001",
            instruction="核对两份独立资料",
            loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 4, "deadline_seconds": 120},
        ),
    )
    waiting = None
    for _ in range(300):
        candidate = await runtime.get("alice", started.run.run_id)
        if candidate.status == "waiting_input" and candidate.topology_admission is not None:
            waiting = candidate
            break
        await asyncio.sleep(0.01)
    assert waiting is not None
    branches = [item for item in waiting.branches if item.status == "running"]
    assert len(branches) == 2

    async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        branch = next(item for item in branches if item.branch_id == request.branch_id)
        findings = tuple(
            AgentControlLoopArtifactFinding(
                finding_id=f"finding-{index:012x}",
                plan_unit_id=branch.unit_id,
                affected_branch_ids=[branch.branch_id],
                title=f"逐项发现 {index}",
                detail="运行时保留的逐项可审查事实。",
                file_refs=list(request.source_file_refs),
            )
            for index in range(1, 12)
        ) if branch is branches[0] else ()
        return ReadonlyWorkerContribution(
            worker_run_id=request.worker_run_id,
            branch_id=request.branch_id,
            outcome="adopted",
            summary="已通过服务端来源核对",
            source_file_refs=request.source_file_refs,
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
            findings=findings,
        )

    requests = [
        ReadonlyWorkerRequest(
            worker_run_id=f"worker-eleven-{index}",
            branch_id=branch.branch_id,
            goal=branch.objective,
            source_file_refs=tuple(branch.input_file_refs),
            expected_version=waiting.version,
        )
        for index, branch in enumerate(branches, start=1)
    ]
    with pytest.raises(HarnessConflictError, match="重复派发"):
        await runtime.execute_admitted_readonly_workers(
            "alice",
            started.run.run_id,
            expected_version=waiting.version,
            idempotency_key="artifact-eleven-workers-duplicate",
            worker_requests=[requests[0], requests[0].model_copy(update={"worker_run_id": "worker-eleven-duplicate"})],
            handler=handler,
            user_confirmed=True,
        )
    result = await runtime.execute_admitted_readonly_workers(
        "alice",
        started.run.run_id,
        expected_version=waiting.version,
        idempotency_key="artifact-eleven-workers-0001",
        worker_requests=requests,
        handler=handler,
        user_confirmed=True,
    )
    assert result.artifact_versions[-1].finding_count == 11
    assert len(result.artifact_versions[-1].findings) == 11
    await runtime.close()


@pytest.mark.asyncio
async def test_worker_reservation_and_merge_restore_memory_on_storage_failure() -> None:
    """A rejected aggregate write must not advance the process-local snapshot."""
    from tests.unit.test_harness_runtime import FakeAnalyst

    class FailingStore(InMemoryHarnessStateStore):
        fail_next = False

        async def commit(self, *args, **kwargs):
            if self.fail_next:
                self.fail_next = False
                raise RuntimeError("injected aggregate storage failure")
            return await super().commit(*args, **kwargs)

    class TwoBranchPlanner:
        model = "test-planner"

        async def plan(self, *, scenario, files):
            refs = [str(item["file_ref"]) for item in files[:2]]
            return HarnessPlanCandidate(
                summary="两个独立只读工作包",
                selection_reason="服务端校验的跨职能来源结构",
                units=[
                    HarnessPlanCandidateUnit(
                        unit_id=f"unit-{index}",
                        title=f"工作包 {index}",
                        objective="核对批准来源",
                        input_file_refs=[ref],
                        tool="file.read",
                    )
                    for index, ref in enumerate(refs, 1)
                ],
            )

    async def waiting_runtime():
        store = FailingStore()
        runtime = HarnessRuntime(_cross_function_catalog(), TwoBranchPlanner(), FakeAnalyst(), store)
        started = await runtime.start(
            "alice",
            HarnessRunStart(
                idempotency_key="worker-atomic-start-0001",
                instruction="核对两个独立来源",
                loop={"max_rounds": 1, "max_files_per_round": 2, "max_model_calls": 4, "deadline_seconds": 120},
            ),
        )
        waiting = None
        for _ in range(400):
            candidate = await runtime.get("alice", started.run.run_id)
            if candidate.status == "waiting_input" and candidate.topology_admission is not None:
                waiting = candidate
                break
            await asyncio.sleep(0.01)
        assert waiting is not None
        return runtime, store, waiting

    runtime, store, waiting = await waiting_runtime()
    try:
        branch = next(item for item in waiting.branches if item.status == "running")
        request = ReadonlyWorkerRequest(
            worker_run_id="worker-reservation-failure",
            branch_id=branch.branch_id,
            goal=branch.objective,
            source_file_refs=tuple(branch.input_file_refs),
            expected_version=waiting.version,
        )
        before = waiting.model_dump(mode="json")
        calls = 0

        async def handler(_: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            nonlocal calls
            calls += 1
            raise AssertionError("reservation failure must happen before dispatch")

        store.fail_next = True
        with pytest.raises(RuntimeError, match="injected aggregate"):
            await runtime.execute_admitted_readonly_workers(
                "alice",
                waiting.run_id,
                expected_version=waiting.version,
                idempotency_key="worker-reservation-failure-0001",
                worker_requests=[request],
                handler=handler,
                user_confirmed=True,
            )
        assert calls == 0
        assert (await runtime.get("alice", waiting.run_id)).model_dump(mode="json") == before
    finally:
        await runtime.close()

    runtime, store, waiting = await waiting_runtime()
    try:
        branch = next(item for item in waiting.branches if item.status == "running")
        request = ReadonlyWorkerRequest(
            worker_run_id="worker-merge-failure",
            branch_id=branch.branch_id,
            goal=branch.objective,
            source_file_refs=tuple(branch.input_file_refs),
            expected_version=waiting.version,
        )

        async def handler(_: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            store.fail_next = True
            return ReadonlyWorkerContribution(
                worker_run_id="worker-merge-failure",
                branch_id=branch.branch_id,
                outcome="adopted",
                summary="已返回可核对贡献",
                source_file_refs=tuple(branch.input_file_refs),
                evidence_anchors=("line:1",),
                model_called=True,
                output_used=True,
                findings=(
                    AgentControlLoopArtifactFinding(
                        finding_id="finding-merge-failure",
                        plan_unit_id=branch.unit_id,
                        affected_branch_ids=[branch.branch_id],
                        title="可核对贡献",
                        detail="贡献写入时注入存储失败。",
                        file_refs=list(branch.input_file_refs),
                    ),
                ),
            )

        reserved = None
        # The reservation is durable before the handler runs; capture it in
        # the handler's first invocation through the next event-loop turn.
        async def capture_reserved(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
            nonlocal reserved
            reserved = await runtime.get("alice", waiting.run_id)
            return await handler(request)

        with pytest.raises(RuntimeError, match="injected aggregate"):
            await runtime.execute_admitted_readonly_workers(
                "alice",
                waiting.run_id,
                expected_version=waiting.version,
                idempotency_key="worker-merge-failure-0001",
                worker_requests=[request],
                handler=capture_reserved,
                user_confirmed=True,
            )
        assert reserved is not None
        restored = await runtime.get("alice", waiting.run_id)
        assert restored.model_dump(mode="json") == reserved.model_dump(mode="json")
        assert restored.worker_idempotency.get("worker-merge-failure-0001", "").startswith("reserved:")
        assert restored.contributions == []
        assert restored.artifact_versions == []
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_workers_are_branch_isolated_and_partial_merge_is_preserved() -> None:
    requests = [
        ReadonlyWorkerRequest(
            worker_run_id="worker-1",
            branch_id="branch-1",
            goal="核对第一份资料",
            source_file_refs=("forte-1111111111111111",),
            expected_version=2,
        ),
        ReadonlyWorkerRequest(
            worker_run_id="worker-2",
            branch_id="branch-2",
            goal="核对第二份资料",
            source_file_refs=("forte-2222222222222222",),
            expected_version=2,
        ),
    ]
    seen: list[tuple[str, tuple[str, ...]]] = []

    async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        seen.append((request.branch_id, request.source_file_refs))
        if request.branch_id == "branch-2":
            raise RuntimeError("source location unavailable")
        return ReadonlyWorkerContribution(
            worker_run_id=request.worker_run_id,
            branch_id=request.branch_id,
            outcome="adopted",
            summary="已形成可核对贡献",
            source_file_refs=request.source_file_refs,
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
            elapsed_ms=5,
        )

    results = await execute_readonly_workers(requests, handler)
    assert seen == [("branch-1", ("forte-1111111111111111",)), ("branch-2", ("forte-2222222222222222",))]
    merged = merge_adopted_contributions(results)
    assert merged.adopted_worker_run_ids == ("worker-1",)
    assert merged.failed_worker_run_ids == ("worker-2",)
    assert merged.waiting_branch_ids == ("branch-2",)


@pytest.mark.asyncio
async def test_worker_limit_is_hard_and_exception_does_not_fail_group() -> None:
    requests = [
        ReadonlyWorkerRequest(
            worker_run_id=f"worker-{index}",
            branch_id=f"branch-{index}",
            goal="独立核对",
            source_file_refs=(f"forte-{index:016x}",),
            expected_version=1,
        )
        for index in range(4)
    ]

    async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        await asyncio.sleep(0)
        return ReadonlyWorkerContribution(
            worker_run_id=request.worker_run_id,
            branch_id=request.branch_id,
            outcome="adopted",
            summary="通过",
            source_file_refs=request.source_file_refs,
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
        )

    with pytest.raises(ValueError, match="hard cap"):
        await execute_readonly_workers(requests, handler, max_workers=3)


@pytest.mark.asyncio
async def test_worker_source_scope_violation_is_rejected_and_branch_waits() -> None:
    request = ReadonlyWorkerRequest(
        worker_run_id="worker-scope",
        branch_id="branch-scope",
        goal="核对资料",
        source_file_refs=("forte-1111111111111111",),
        expected_version=1,
    )

    async def handler(_: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        return ReadonlyWorkerContribution(
            worker_run_id="worker-scope",
            branch_id="branch-scope",
            outcome="adopted",
            summary="越权候选",
            source_file_refs=("forte-9999999999999999",),
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
        )

    result = (await execute_readonly_workers([request], handler))[0]
    assert result.outcome == "rejected"
    assert result.output_used is False
    merged = merge_adopted_contributions([result])
    assert merged.adopted_worker_run_ids == ()
    assert merged.waiting_branch_ids == ("branch-scope",)


@pytest.mark.asyncio
async def test_worker_adoption_gate_normalizes_missing_anchor_to_rejected() -> None:
    request = ReadonlyWorkerRequest(
        worker_run_id="worker-no-anchor",
        branch_id="branch-no-anchor",
        goal="核对资料",
        source_file_refs=("forte-1111111111111111",),
        expected_version=1,
    )

    async def handler(_: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        return ReadonlyWorkerContribution(
            worker_run_id="worker-no-anchor",
            branch_id="branch-no-anchor",
            outcome="adopted",
            summary="模型返回但没有可定位 Anchor",
            source_file_refs=("forte-1111111111111111",),
            model_called=True,
            output_used=True,
        )

    result = (await execute_readonly_workers([request], handler))[0]
    assert result.outcome == "rejected"
    assert result.output_used is False
    assert result.error is not None


def test_worker_merge_is_a_normal_artifact_and_keeps_reconciliation_receipt() -> None:
    reconciliation = AgentControlLoopNarrativeReconciliation(
        reconciliation_id="narrative-reconciliation-0123456789ab",
        round_number=1,
        status="not_applicable",
        authority="model_only",
        model_disposition="adopted",
        model_returned=True,
        message="没有确定性成果，保留模型回执供审阅。",
        checked_at=datetime.now(timezone.utc),
    )
    results = [
        ReadonlyWorkerContribution(
            worker_run_id="worker-success-1",
            branch_id="branch-success-1",
            outcome="adopted",
            summary="已通过 Anchor 核对",
            source_file_refs=("forte-1111111111111111",),
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
            narrative_reconciliation=reconciliation,
        ),
        ReadonlyWorkerContribution(
            worker_run_id="worker-success-2",
            branch_id="branch-success-2",
            outcome="adopted",
            summary="已通过 Anchor 核对",
            source_file_refs=("forte-2222222222222222",),
            evidence_anchors=("line:2",),
            model_called=True,
            output_used=True,
            narrative_reconciliation=reconciliation,
        ),
        ReadonlyWorkerContribution(
            worker_run_id="worker-ambiguous",
            branch_id="branch-ambiguous",
            outcome="ambiguous",
            summary="原文位置不唯一",
            source_file_refs=("forte-3333333333333333",),
            model_called=True,
            output_used=False,
            narrative_reconciliation=reconciliation,
        ),
    ]
    merged = merge_adopted_contributions(results, version=3)
    assert merged.artifact_id.startswith("artifact-")
    assert merged.version == 3
    assert merged.adopted_worker_run_ids == ("worker-success-1", "worker-success-2")
    assert merged.waiting_branch_ids == ("branch-ambiguous",)
    assert all(item.narrative_reconciliation is not None for item in results)


def test_rejected_narrative_or_missing_anchor_never_enters_merge() -> None:
    rejected = AgentControlLoopNarrativeReconciliation(
        reconciliation_id="narrative-reconciliation-fedcba987654",
        round_number=1,
        status="contradictory",
        authority="deterministic_outcome",
        model_disposition="rejected",
        model_returned=True,
        message="模型叙述与服务端事实冲突。",
        checked_at=datetime.now(timezone.utc),
    )
    result = ReadonlyWorkerContribution(
        worker_run_id="worker-rejected",
        branch_id="branch-rejected",
        outcome="adopted",
        summary="候选结论被对账拒绝",
        source_file_refs=("forte-1111111111111111",),
        evidence_anchors=("line:1",),
        model_called=True,
        output_used=True,
        narrative_reconciliation=rejected,
    )
    merged = merge_adopted_contributions([result])
    assert merged.adopted_worker_run_ids == ()
    assert merged.waiting_branch_ids == ("branch-rejected",)


@pytest.mark.parametrize("status", ["stale", "contradictory"])
def test_stale_or_contradictory_narrative_never_enters_merge_even_if_marked_adopted(
    status: str,
) -> None:
    reconciliation = AgentControlLoopNarrativeReconciliation(
        reconciliation_id="narrative-reconciliation-abcdef123456",
        round_number=1,
        status=status,
        authority="deterministic_outcome",
        model_disposition="adopted",
        model_returned=True,
        message="模型叙述不能作为当前结论。",
        checked_at=datetime.now(timezone.utc),
    )
    result = ReadonlyWorkerContribution(
        worker_run_id=f"worker-{status}",
        branch_id=f"branch-{status}",
        outcome="adopted",
        summary="状态异常的候选贡献",
        source_file_refs=("forte-1111111111111111",),
        evidence_anchors=("line:1",),
        model_called=True,
        output_used=True,
        narrative_reconciliation=reconciliation,
    )

    merged = merge_adopted_contributions([result])

    assert merged.adopted_worker_run_ids == ()
    assert merged.waiting_branch_ids == (f"branch-{status}",)


def test_worker_merge_receipts_keep_prior_wave_and_align_versions() -> None:
    wave_one = ReadonlyWorkerContribution(
        worker_run_id="worker-wave-one",
        branch_id="branch-wave-one",
        outcome="adopted",
        summary="第一批已核对",
        source_file_refs=("forte-1111111111111111",),
        evidence_anchors=("line:1",),
        model_called=True,
        output_used=True,
    )
    wave_two = ReadonlyWorkerContribution(
        worker_run_id="worker-wave-two",
        branch_id="branch-wave-two",
        outcome="adopted",
        summary="第二批已核对",
        source_file_refs=("forte-2222222222222222",),
        evidence_anchors=("line:2",),
        model_called=True,
        output_used=True,
    )
    receipt_v1 = merge_adopted_contributions([wave_one], version=1)
    receipt_v2 = merge_adopted_contributions([wave_two], version=2)
    assert receipt_v1.version == 1
    assert receipt_v1.adopted_worker_run_ids == ("worker-wave-one",)
    assert receipt_v2.version == 2
    assert receipt_v2.adopted_worker_run_ids == ("worker-wave-two",)
    assert receipt_v1.model_dump() != receipt_v2.model_dump()


def test_worker_contribution_keeps_more_than_ten_findings_without_silent_top_n() -> None:
    retained_refs = tuple(f"forte-{index:016x}" for index in range(1, 25))
    contribution = ReadonlyWorkerContribution(
        worker_run_id="worker-many-findings",
        branch_id="branch-many-findings",
        outcome="adopted",
        summary="保留全部逐项发现",
        source_file_refs=retained_refs,
        evidence_anchors=("line:1",),
        model_called=True,
        output_used=True,
        findings=tuple(
            AgentControlLoopArtifactFinding(
                finding_id=f"finding-{index:012x}",
                plan_unit_id="unit-many",
                affected_branch_ids=["branch-many-findings"],
                title=f"发现 {index}",
                detail="逐项可审查事实",
                file_refs=[retained_refs[(index - 1) % len(retained_refs)]],
            )
            for index in range(1, 12)
        ),
    )
    merged = merge_adopted_contributions([contribution])
    assert len(merged.adopted_contributions[0].findings) == 11
    artifact = AgentControlLoopArtifactVersion(
        artifact_id="artifact-0123456789ab",
        version=1,
        title="逐项成果",
        status="committed",
        summary="不截断的逐项成果",
        findings=list(contribution.findings),
        finding_count=11,
        source_file_refs=list(retained_refs),
        created_at=datetime.now(timezone.utc),
    )
    assert artifact.finding_count == len(artifact.findings) == 11
    assert len(artifact.source_file_refs) == len(retained_refs)
    assert set(artifact.source_file_refs) == set(retained_refs)
