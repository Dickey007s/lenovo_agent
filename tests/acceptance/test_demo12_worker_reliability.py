"""Deterministic controls for gaps found in the real-provider Demo 1/2 replay."""

import asyncio

import pytest

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.harness_runtime import HarnessConflictError, HarnessPlanCandidate, HarnessRunStart, HarnessRuntime
from services.api.app.application.readonly_workers import ReadonlyWorkerContribution, ReadonlyWorkerRequest
from tests.acceptance.test_demo1_demo2_fixed_scenarios import FiveUnitFailurePlanner, _ten_file_cross_function_catalog, _wait_for
from tests.unit.test_harness_runtime import FakeAnalyst


async def admitted(runtime):
    started = await runtime.start("reliability", HarnessRunStart(
        instruction="只读核对五个相互依赖的工作包",
        idempotency_key="worker-reliability-start",
        loop={"max_rounds": 2, "max_files_per_round": 10, "max_model_calls": 8, "deadline_seconds": 120},
    ))
    waiting = await _wait_for(runtime, "reliability", started.run.run_id, lambda run: run.status == "waiting_input")
    await asyncio.sleep(0)
    return waiting


@pytest.mark.asyncio
async def test_explicit_numbered_dependent_requirements_keep_the_validated_dag():
    class NumberedPlanner(FiveUnitFailurePlanner):
        async def plan(self, **kwargs):
            candidate = await super().plan(**kwargs)
            payload = candidate.model_dump()
            payload["requirement_coverage"] = [
                {"requirement_index": index, "title": unit.title, "objective": unit.objective,
                 "status": "planned", "unit_id": unit.unit_id, "reason": "本轮来源与依赖已列明"}
                for index, unit in enumerate(candidate.units, start=1)
            ]
            return HarnessPlanCandidate.model_validate(payload)

    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), NumberedPlanner(), FakeAnalyst())
    try:
        started = await runtime.start("reliability", HarnessRunStart(
            instruction="请分别核对以下要求：\n1. 产品上线\n2. 搜索风险\n3. 交互问题\n4. 根据第2项形成待办\n5. 比较第1项和第3项影响",
            idempotency_key="numbered-dependencies-start",
        ))
        waiting = await _wait_for(runtime, "reliability", started.run.run_id, lambda run: run.status in {"waiting_input", "failed"})
        assert waiting.status == "waiting_input", waiting.validation_errors
        assert len(waiting.plan.units) == 5
        assert len(waiting.plan.requirement_coverage) == 5
        assert sum(branch.status == "running" for branch in waiting.branches) == 3
        assert sum(branch.status == "pending" for branch in waiting.branches) == 2
        assert len(waiting.rounds[-1].next_step.ready_branch_ids) == 3
        assert not waiting.work_units
        assert not waiting.plan.deferred_requirements
        assert not waiting.worker_runs
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_admission_and_between_wave_waits_freeze_active_time(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("services.api.app.application.harness_runtime.perf_counter", lambda: clock[0])
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), FakeAnalyst())
    try:
        waiting = await admitted(runtime)
        clock[0] += 1000
        roots = [branch for branch in waiting.branches if branch.status == "running"]

        async def handler(request):
            clock[0] += 2
            return ReadonlyWorkerContribution(
                worker_run_id=request.worker_run_id, branch_id=request.branch_id,
                source_file_refs=request.source_file_refs, summary="本分支原文位置尚未唯一确定",
                outcome="ambiguous", model_called=True, elapsed_ms=2000,
            )

        for index, branch in enumerate(roots[:2]):
            result = await runtime.execute_admitted_readonly_workers(
                "reliability", waiting.run_id, expected_version=waiting.version,
                idempotency_key=f"worker-clock-{index}", user_confirmed=True,
                worker_requests=[ReadonlyWorkerRequest(
                    worker_run_id=f"worker-clock-{index}", branch_id=branch.branch_id,
                    goal=branch.objective, source_file_refs=tuple(branch.input_file_refs),
                    expected_version=waiting.version,
                )], handler=handler,
            )
            assert result.budget.elapsed_ms == (index + 1) * 2000
            assert result.status == "waiting_input" and result.control_state == "paused"
            assert runtime._runs[("reliability", waiting.run_id)].active_since_perf is None
            clock[0] += 1000
            waiting = result
        stopped = await runtime.control("reliability", result.run_id, AgentControlLoopControlRequest(
            command="stop", expected_version=result.version, idempotency_key="worker-idle-stop",
        ))
        terminal = await _wait_for(runtime, "reliability", stopped.run.run_id, lambda run: run.status == "stopped")
        assert terminal.budget.elapsed_ms == 4000
        assert terminal.worker_runs == result.worker_runs
        assert terminal.budget.model_calls_used == result.budget.model_calls_used
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_expired_worker_budget_fails_before_dispatch():
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), FakeAnalyst())
    try:
        waiting = await admitted(runtime)
        runtime._runs[("reliability", waiting.run_id)].active_elapsed_base_ms = 120000
        with pytest.raises(HarnessConflictError, match="执行时间预算已耗尽"):
            await runtime.execute_admitted_workers_from_branches(
                "reliability", waiting.run_id, branch_ids=[], expected_version=waiting.version,
                idempotency_key="worker-expired", user_confirmed=True,
            )
        after = await runtime.get("reliability", waiting.run_id)
        assert not after.worker_runs and not after.work_units
        assert after.budget.model_calls_used == waiting.budget.model_calls_used
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_worker_scope_rejection_keeps_actual_call_receipt():
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), FakeAnalyst(invalid_reference=True))
    try:
        waiting = await admitted(runtime)
        branch = next(branch for branch in waiting.branches if branch.status == "running")
        result = await runtime.execute_admitted_workers_from_branches(
            "reliability", waiting.run_id, branch_ids=[branch.branch_id], expected_version=waiting.version,
            idempotency_key="worker-invalid-scope", user_confirmed=True,
        )
        assert result.worker_runs[0].outcome == "failed"
        assert result.worker_runs[0].model_called is True
        assert result.worker_runs[0].output_used is False
        assert result.contributions[0].model_receipt.called is True
        assert not result.artifact_versions
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_seven_anchored_findings_do_not_hit_old_six_anchor_worker_limit():
    class SevenFindingsAnalyst(FakeAnalyst):
        async def analyze(self, **kwargs):
            kwargs.pop("verified_effect_context", None)
            result = await super().analyze(**kwargs)
            finding = result.findings[0]
            return result.model_copy(update={"findings": [
                finding.model_copy(update={"title": f"来源核对 {index}"}) for index in range(7)
            ]})

    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), SevenFindingsAnalyst())
    try:
        waiting = await admitted(runtime)
        branch = next(branch for branch in waiting.branches if branch.status == "running")
        result = await runtime.execute_admitted_workers_from_branches(
            "reliability", waiting.run_id, branch_ids=[branch.branch_id], expected_version=waiting.version,
            idempotency_key="worker-seven-findings", user_confirmed=True,
        )
        contribution = result.worker_runs[0]
        assert contribution.outcome == "adopted"
        assert len(contribution.findings) == 7
        assert len(contribution.evidence_anchors) == 7
        assert len(result.artifact_versions[-1].findings) == 7
    finally:
        await runtime.close()
