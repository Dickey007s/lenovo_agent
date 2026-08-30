from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import time

import pytest
from fastapi.routing import APIRoute

from services.api.app.application.harness_runtime import (
    HarnessEvidenceQuote,
    HarnessFinding,
    HarnessPlan,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessPlanUnit,
    HarnessRunStart,
    HarnessTaskResult,
    HarnessRuntime,
)
from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.readonly_workers import (
    ReadonlyWorkerContribution,
    ReadonlyWorkerRequest,
    execute_readonly_workers,
    merge_adopted_contributions,
)
from services.api.app.application.topology_admission import admit_topology
from packages.contracts.harness_models import AgentControlLoopNarrativeReconciliation
from services.api.app.main import create_app


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
    from tests.unit.test_harness_runtime import FakeAnalyst, FakeCatalog

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

        async def analyze(self, **kwargs):
            self.calls += 1
            return await super().analyze(**kwargs)

    planner = TwoIndependentPlanner()
    analyst = CountingAnalyst()
    runtime = HarnessRuntime(FakeCatalog(), planner, analyst)
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

    runtime = HarnessRuntime(FakeCatalog(), FakePlanner(), AlwaysUnlocatableAnalyst())
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
    child = await runtime.continue_unfinished_task(
        "alice",
        terminal.run_id,
        branch.branch_id,
        idempotency_key="demo1-child-continue-0001",
        expected_version=terminal.version,
    )
    assert child.run.task_id == terminal.task_id
    assert child.run.run_id != terminal.run_id
    assert child.run.run_sequence == terminal.run_sequence + 1
    assert tuple(child.run.recheck_file_refs) == expected_refs
    assert child.run.carried_branch_id == branch.branch_id
    assert terminal.model_dump(mode="json") == old_dump
    replay = await runtime.continue_unfinished_task(
        "alice",
        terminal.run_id,
        branch.branch_id,
        idempotency_key="demo1-child-continue-0001",
        expected_version=terminal.version,
    )
    assert replay.run.run_id == child.run.run_id
    await runtime.close()


@pytest.mark.asyncio
async def test_demo2_five_unit_dag_runs_two_scheduler_owned_waves_and_accumulates_v2() -> None:
    """Three ready units run first; two dependents become ready only afterwards."""
    from tests.unit.test_harness_runtime import FakeCatalog

    refs = tuple(f"forte-{index:016x}" for index in range(1, 6))

    class WaveCatalog(FakeCatalog):
        def __init__(self) -> None:
            super().__init__()
            self.files = [
                {
                    "file_ref": ref,
                    "folder_id": f"folder-{index}",
                    "path": f"group-{index}/input.txt",
                    "role": "input",
                    "mime": "text/plain",
                    "size": 20,
                    "sha256": f"{index:x}" * 64,
                    "display_label": f"资料 {index}",
                    "display_group": f"业务组 {index}",
                    "display_path": f"业务组 {index}/资料 {index}.txt",
                    "display_summary": "文本文件",
                }
                for index, ref in enumerate(refs, start=1)
            ]

        def public_workspace(self) -> dict[str, object]:
            workspace = super().public_workspace()
            workspace["file_count"] = len(self.files)
            workspace["folders"] = []
            return workspace

        def internal_workspace(self) -> dict[str, object]:
            workspace = super().internal_workspace()
            workspace["files"] = self.files
            return workspace

        def public_file(self, file_ref: str) -> dict[str, object]:
            item = next(item for item in self.files if item["file_ref"] == file_ref)
            return {
                **item,
                "kind": "text",
                "columns": [],
                "text": f"证据 {file_ref}",
                "rows": [],
                "total_rows": None,
            }

        def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, object]]:
            return [
                {
                    "file_ref": ref,
                    "display_label": next(item["display_label"] for item in self.files if item["file_ref"] == ref),
                    "kind": "text",
                    "columns": [],
                    "text": f"证据 {ref}",
                }
                for ref in file_refs
            ]

    class FiveWavePlanner:
        model = "test-planner"

        def __init__(self) -> None:
            self.calls = 0

        async def plan(self, *, scenario, files):
            self.calls += 1
            return HarnessPlanCandidate(
                summary="五个工作包的两波依赖计划",
                selection_reason="服务端验证的有向依赖图",
                units=[
                    *[
                        HarnessPlanCandidateUnit(
                            unit_id=f"u{index}",
                            title=f"独立工作包 {index}",
                            objective=f"核对第 {index} 份资料",
                            input_file_refs=[refs[index - 1]],
                            tool="file.read",
                        )
                        for index in range(1, 4)
                    ],
                    HarnessPlanCandidateUnit(
                        unit_id="u4",
                        title="依赖工作包 4",
                        objective="在工作包 1 完成后核对资料 4",
                        input_file_refs=[refs[3]],
                        depends_on=["u1"],
                        tool="file.read",
                    ),
                    HarnessPlanCandidateUnit(
                        unit_id="u5",
                        title="依赖工作包 5",
                        objective="在工作包 2 完成后核对资料 5",
                        input_file_refs=[refs[4]],
                        depends_on=["u2"],
                        tool="file.read",
                    ),
                ],
            )

    class WaveAnalyst:
        model = "test-analyst"

        async def analyze(self, *, instruction, plan, files, validation_feedback=None):
            item = files[0]
            unit = plan.units[0]
            ref = str(item["file_ref"])
            return HarnessTaskResult(
                summary=f"已核对 {ref}",
                findings=[
                    HarnessFinding(
                        plan_unit_id=unit.unit_id,
                        title=f"已定位 {unit.unit_id}",
                        detail="该工作包有一处可回开的只读事实。",
                        file_refs=[ref],
                        evidence_quotes=[
                            HarnessEvidenceQuote(
                                file_ref=ref,
                                role="support",
                                label="工作包证据",
                                quote=f"证据 {ref}",
                            )
                        ],
                    )
                ],
                review_required=True,
            )

    runtime = HarnessRuntime(WaveCatalog(), FiveWavePlanner(), WaveAnalyst())
    started = await runtime.start(
        "alice",
        HarnessRunStart(
            idempotency_key="demo2-five-wave-start-0001",
            instruction="核对五个相互关联的资料分支",
            loop={"max_rounds": 1, "max_files_per_round": 8, "max_model_calls": 10, "deadline_seconds": 120},
        ),
    )
    waiting = None
    for _ in range(500):
        candidate = await runtime.get("alice", started.run.run_id)
        if candidate.status == "waiting_input" and candidate.topology_admission:
            waiting = candidate
            break
        await asyncio.sleep(0.01)
    assert waiting is not None
    assert waiting.topology_admission.mode == "adaptive_readonly_workers"
    assert waiting.rounds[0].next_step.ready_branch_ids == [
        item.branch_id for item in waiting.branches if item.status == "running"
    ]
    assert [item.status for item in waiting.branches] == ["running", "running", "running", "pending", "pending"]
    first = await runtime.execute_admitted_workers_from_branches(
        "alice", waiting.run_id, branch_ids=[], expected_version=waiting.version,
        idempotency_key="demo2-five-wave-workers-0001", user_confirmed=True,
    )
    assert first.status == "waiting_input"
    assert len(first.worker_runs) == 3
    assert len(first.shared_artifacts) == 1
    assert [item.status for item in first.branches] == ["completed", "completed", "completed", "running", "running"]
    assert first.rounds[0].next_step.ready_branch_ids == [first.branches[3].branch_id, first.branches[4].branch_id]
    second = await runtime.execute_admitted_workers_from_branches(
        "alice", first.run_id, branch_ids=[], expected_version=first.version,
        idempotency_key="demo2-five-wave-workers-0002", user_confirmed=True,
    )
    assert second.status == "completed"
    assert len(second.worker_runs) == 5
    assert len(second.shared_artifacts) == 2
    assert [item.version for item in second.artifact_versions] == [1, 2]
    assert second.artifact_versions[0].artifact_id == second.artifact_versions[1].artifact_id
    assert second.artifact_versions[1].finding_count == 5
    assert second.budget.model_calls_used == 8  # planner + 3 + 2 workers, with one bounded repair
    assert {event.event_name for event in second.events}.issuperset({"worker_returned", "contribution_adopted"})
    await runtime.close()


@pytest.mark.asyncio
async def test_five_unit_dag_runtime_advances_from_roots_to_second_worker_wave() -> None:
    from tests.unit.test_harness_runtime import FakeAnalyst, FakeCatalog

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

    runtime = HarnessRuntime(FakeCatalog(), FiveUnitDagPlanner(), FakeAnalyst())
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
    ready_units = {item.unit_id for item in first.branches if item.status == "running"}
    assert ready_units == {"u4", "u5"}, [(item.unit_id, item.status) for item in first.branches]
    assert set(first.rounds[-1].next_step.ready_branch_ids) == {
        by_unit[unit_id].branch_id for unit_id in ready_units
    }

    by_unit = {item.unit_id: item for item in first.branches}
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
