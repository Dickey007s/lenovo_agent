"""Result-driven additions use real Runtime gates, with controlled model outputs."""

import asyncio

import pytest

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.adaptive_review import AdaptiveReviewProposal
from services.api.app.application.harness_runtime import HarnessPlan, HarnessPlanUnit, HarnessRunStart, HarnessRuntime
from services.api.app.application.topology_admission import admit_topology
from tests.acceptance.test_demo1_demo2_fixed_scenarios import FiveUnitFailurePlanner, _ten_file_cross_function_catalog
from tests.acceptance.test_demo12_output_and_dependencies import ContextAnalyst


class AdaptivePlanner(FiveUnitFailurePlanner):
    def __init__(self, mode="add"):
        super().__init__()
        self.mode = mode
        self.contexts = []
        self.entered = asyncio.Event()
        self.release = asyncio.Event()

    async def plan(self, **kwargs):
        plan = await super().plan(**kwargs)
        return plan.model_copy(update={"units": [u for u in plan.units if not u.depends_on]})

    async def review_progress(self, *, context):
        self.contexts.append(context)
        if self.mode == "hold":
            self.entered.set()
            await self.release.wait()
        if self.mode == "error":
            raise RuntimeError("test coordinator failure")
        if self.mode == "none" or (len(self.contexts) > 1 and self.mode != "always"):
            return AdaptiveReviewProposal(summary="已有结果覆盖当前目标，不再增加工作。")
        fact = context["findings"][0]
        parent = next(u for u in context["existing_work"] if u["unit_id"] == fact["plan_unit_id"])
        addition = dict(title="补核现有结论的适用条件", objective=f"核对 {parent['unit_id']} 结论对应的适用条件，不重做其他工作。",
            reason="本批结果出现适用范围说明，需要核对其对应条件。",
            parent_unit_ids=[parent["unit_id"]], trigger_finding_ids=[fact["finding_id"]],
            input_file_refs=parent["input_file_refs"])
        if self.mode == "outside":
            addition["input_file_refs"] = ["unapproved-file"]
        if self.mode == "unknown":
            addition["trigger_finding_ids"] = ["invented-finding"]
        return AdaptiveReviewProposal(summary="根据已返回的适用范围说明，补充一项核对。", additions=[addition])


async def start(runtime, key="adaptive", calls=12):
    return await runtime.start("adaptive", HarnessRunStart(instruction="整理办公资料中的需要关注的事项",
        idempotency_key=key, output_preference="analysis_only", execution_policy="automatic_readonly",
        loop={"max_model_calls": calls, "max_rounds": 3, "max_files_per_round": 16, "deadline_seconds": 120}))


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["add", "none", "outside", "unknown", "error"])
async def test_adaptive_result_addition_and_fail_closed(mode):
    planner, analyst = AdaptivePlanner(mode), ContextAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, analyst)
    try:
        started = await start(runtime)
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert len(final.worker_runs) == (4 if mode == "add" else 3)
        assert all(item.output_used for item in final.worker_runs)
        assert final.adaptive_reviews[0].status == ("expanded" if mode == "add" else "unchanged" if mode == "none" else "blocked")
        assert final.status == ("waiting_input" if mode in {"outside", "unknown", "error"} else "completed")
        assert final.artifact_versions
        if mode == "add":
            assert len(final.plan.units) == 4
            assert len(final.adaptive_reviews) == 2
            assert final.budget.model_calls_used == 7
            added = final.adaptive_reviews[0].added_branch_ids[0]
            assert any(w.branch_id == added and w.input_contribution_ids for w in final.worker_runs)
            assert len(analyst.inputs) == 4
            assert all(u.attempt == 1 for u in final.work_units)
            assert len(final.artifact_versions) == 2
            assert runtime.public_snapshot(final).adaptive_reviews[0].added_branch_ids == [added]
        before = len(analyst.inputs)
        await runtime._execute_automatic_worker_waves("adaptive", final.run_id)
        assert len(analyst.inputs) == before
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_no_review_call_when_budget_reserved_for_existing_work():
    planner = AdaptivePlanner()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await start(runtime, calls=5)
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert not planner.contexts
        assert not final.adaptive_reviews
        assert final.budget.model_calls_used == 4
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["pause", "stop"])
async def test_control_during_review_never_starts_new_agent(command):
    planner = AdaptivePlanner("hold")
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await start(runtime)
        await asyncio.wait_for(planner.entered.wait(), 5)
        current = await runtime.get("adaptive", started.run.run_id)
        await runtime.control("adaptive", current.run_id, AgentControlLoopControlRequest(
            command=command, expected_version=current.version, idempotency_key=f"during-review-{command}"))
        planner.release.set()
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert len(final.worker_runs) == 3
        assert final.adaptive_reviews[0].status == "discarded"
        assert not final.adaptive_reviews[0].added_branch_ids
        assert len(final.plan.units) == 3
    finally:
        planner.release.set()
        await runtime.close()


@pytest.mark.asyncio
async def test_more_than_three_roots_are_not_a_concurrency_cap():
    plan = HarnessPlan(summary="四项独立工作", selection_reason="来源彼此独立",
        units=[HarnessPlanUnit(unit_id=f"r{i}", title=f"工作{i}", objective=f"核对资料{i}",
            input_file_refs=[f"file{i}"], tool="evidence.verify") for i in range(4)])
    facts = {f"file{i}": {"display_group": f"group{i}"} for i in range(4)}
    legacy = admit_topology(plan, remaining_model_calls=12, remaining_time_seconds=120, source_facts=facts)
    adaptive = admit_topology(plan, remaining_model_calls=12, remaining_time_seconds=120, source_facts=facts, allow_adaptive_waves=True)
    assert legacy.mode == "fixed_workflow"
    assert adaptive.mode == "adaptive_readonly_workers"


@pytest.mark.asyncio
async def test_two_reviews_bound_expansion_without_repeating_roots():
    planner = AdaptivePlanner("always")
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), planner, ContextAnalyst())
    try:
        started = await start(runtime)
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("adaptive", started.run.run_id)
        assert final.status == "completed", final.validation_errors
        assert len(planner.contexts) == len(final.adaptive_reviews) == 2
        assert len(final.worker_runs) == 5
        assert final.budget.model_calls_used == 8
        assert all(u.attempt == 1 for u in final.work_units)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_checkpoint_during_review_is_not_replayed_or_left_reviewing():
    planner = AdaptivePlanner("hold")
    catalog = _ten_file_cross_function_catalog()
    runtime = HarnessRuntime(catalog, planner, ContextAnalyst())
    restored = None
    try:
        started = await start(runtime)
        await asyncio.wait_for(planner.entered.wait(), 5)
        await runtime.close()
        new_planner = AdaptivePlanner()
        restored = HarnessRuntime(catalog, new_planner, ContextAnalyst(), state_store=runtime.state_store)
        await restored.setup()
        final = await restored.get("adaptive", started.run.run_id)
        assert final.control_state == "paused"
        assert final.adaptive_reviews[0].status == "discarded"
        assert not final.adaptive_reviews[0].output_used
        assert not new_planner.contexts
        assert len(final.plan.units) == 3
    finally:
        await runtime.close()
        if restored:
            await restored.close()
