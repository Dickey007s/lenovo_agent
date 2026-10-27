"""Single execution can delegate after evidence, without a second runtime."""

import asyncio

import pytest

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.harness_runtime import HarnessRunStart, HarnessRuntime
from tests.acceptance.test_adaptive_progress import AdaptivePlanner, start
from tests.acceptance.test_demo1_demo2_fixed_scenarios import _ten_file_cross_function_catalog, _wait_for
from tests.acceptance.test_demo12_output_and_dependencies import ContextAnalyst


class SinglePlanner(AdaptivePlanner):
    async def plan(self, **kwargs):
        plan = await super().plan(**kwargs)
        return plan.model_copy(update={"units": plan.units[:1]})


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["add", "none", "outside", "unknown", "error", "always"])
async def test_single_agent_can_delegate_only_valid_result_driven_work(mode):
    planner, analyst = SinglePlanner(mode), ContextAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, analyst)
    try:
        started = await start(runtime)
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        expanded = mode in {"add", "always"}
        expected_count = 3 if mode == "always" else 2 if expanded else 1
        assert len(final.worker_runs) == len(analyst.inputs) == expected_count
        assert final.adaptive_reviews[0].origin == "single_agent"
        assert final.topology_admission.mode == ("adaptive_readonly_workers" if expanded else "single_controller")
        assert final.adaptive_reviews[0].status == ("expanded" if expanded else "unchanged" if mode == "none" else "blocked")
        assert final.status == ("completed" if expanded or mode == "none" else "waiting_input")
        assert all(unit.attempt == 1 for unit in final.work_units)
        assert final.artifact_versions[0].findings
        assert final.budget.model_calls_used == 1 + expected_count + len(planner.contexts)
        first_admission = next(e for e in final.events if e.event_name == "topology_admission")
        assert first_admission.details["mode"] == "single_controller"
        if expanded:
            assert final.worker_runs[1].input_contribution_ids
            assert final.adaptive_reviews[1].origin == "worker_wave"
            assert final.artifact_versions[0].findings[0] in final.artifact_versions[-1].findings
        before = len(analyst.inputs)
        await runtime._execute_automatic_worker_waves("adaptive", final.run_id)
        assert len(analyst.inputs) == before
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("calls", [2, 3])
async def test_single_keeps_execution_budget_before_optional_review(calls):
    planner = SinglePlanner()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await start(runtime, calls=calls)
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert final.status == "completed"
        assert final.budget.model_calls_used == 2
        assert not planner.contexts
        assert not final.adaptive_reviews
        assert final.topology_admission.mode == "single_controller"
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["pause", "stop"])
async def test_single_late_review_cannot_promote_after_control(command):
    planner = SinglePlanner("hold")
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await start(runtime)
        await asyncio.wait_for(planner.entered.wait(), 5)
        current = await runtime.get("adaptive", started.run.run_id)
        await runtime.control("adaptive", current.run_id, AgentControlLoopControlRequest(
            command=command, expected_version=current.version, idempotency_key=f"single-{command}"))
        planner.release.set()
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert len(final.worker_runs) == 1
        assert final.topology_admission.mode == "single_controller"
        assert final.adaptive_reviews[0].status == "discarded"
        assert not final.adaptive_reviews[0].added_branch_ids
    finally:
        planner.release.set()
        await runtime.close()


@pytest.mark.asyncio
async def test_manual_single_route_does_not_gain_automatic_delegation():
    planner = SinglePlanner()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await runtime.start("manual", HarnessRunStart(
            instruction="整理办公资料中的需要关注的事项", idempotency_key="single-manual",
            output_preference="analysis_only"))
        final = await _wait_for(runtime, "manual", started.run.run_id,
                                lambda snapshot: snapshot.analysis_receipt is not None
                                and snapshot.status in {"completed", "waiting_input", "failed"})
        assert not final.worker_runs
        assert not final.adaptive_reviews
        assert not planner.contexts
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_single_review_checkpoint_is_not_replayed():
    planner = SinglePlanner("hold")
    catalog = _ten_file_cross_function_catalog()
    runtime = HarnessRuntime(catalog, planner, ContextAnalyst())
    restored = None
    try:
        started = await start(runtime)
        await asyncio.wait_for(planner.entered.wait(), 5)
        await runtime.close()
        next_planner = SinglePlanner()
        restored = HarnessRuntime(catalog, next_planner, ContextAnalyst(), state_store=runtime.state_store)
        await restored.setup()
        final = await restored.get("adaptive", started.run.run_id)
        assert final.control_state == "paused"
        assert final.adaptive_reviews[0].status == "discarded"
        assert final.topology_admission.mode == "single_controller"
        assert len(final.plan.units) == 1
        assert not next_planner.contexts
    finally:
        await runtime.close()
        if restored:
            await restored.close()


@pytest.mark.asyncio
async def test_single_dispatch_eligibility_keeps_scope_and_human_boundaries():
    planner = SinglePlanner("none")
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await start(runtime)
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert runtime._single_agent_delegation_eligible(final)
        for patch in ({"requires_human_gate": True}, {"side_effect": "external_action"}, {"depends_on": ["other"]}):
            plan = final.plan.model_copy(update={"units": [final.plan.units[0].model_copy(update=patch)]})
            assert not runtime._single_agent_delegation_eligible(final.model_copy(update={"plan": plan}))
        for field in ("deferred_requirements", "uncovered_requirements"):
            plan = final.plan.model_copy(update={field: [object()]})
            assert not runtime._single_agent_delegation_eligible(final.model_copy(update={"plan": plan}))
        assert not runtime._single_agent_delegation_eligible(final.model_copy(update={"execution_policy": "manual"}))
        assert not runtime._single_agent_delegation_eligible(final.model_copy(update={
            "contract": final.contract.model_copy(update={"output_policy": "workspace_files_allowed"})}))
    finally:
        await runtime.close()
