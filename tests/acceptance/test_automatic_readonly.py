"""Automatic authorization is explicit; decisions and retries remain bounded."""

import asyncio

import pytest
from pydantic import ValidationError
from packages.contracts.harness_models import AgentControlLoopControlRequest

from services.api.app.application.harness_runtime import HarnessRunStart, HarnessRuntime
from tests.acceptance.test_demo12_output_and_dependencies import ContextAnalyst
from tests.acceptance.test_demo12_reviewed_collaboration import RepairAnalyst
from tests.acceptance.test_demo1_demo2_fixed_scenarios import (
    FiveUnitFailurePlanner, _ten_file_cross_function_catalog, _wait_for,
)


def test_automatic_policy_requires_analysis_only_and_legacy_digest_unchanged():
    with pytest.raises(ValidationError, match="只读"):
        HarnessRunStart(instruction="分析资料", idempotency_key="auto-invalid", execution_policy="automatic_readonly")
    assert "execution_policy" not in HarnessRunStart(instruction="分析资料", idempotency_key="legacy-policy").model_dump()


@pytest.mark.asyncio
async def test_auto_executes_two_real_runtime_waves_without_workers_http_confirmation():
    analyst = ContextAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        request = HarnessRunStart(instruction="核对上线风险", idempotency_key="automatic-two-waves",
                                  output_preference="analysis_only", execution_policy="automatic_readonly")
        started = await runtime.start("auto", request)
        final = await _wait_for(runtime, "auto", started.run.run_id, lambda run: run.status in {"completed", "failed"})
        assert final.status == "completed", final.validation_errors
        assert len(final.worker_runs) == 5
        assert all(item.output_used for item in final.worker_runs)
        assert len(final.artifact_versions) == 2
        assert final.budget.model_calls_used == 6
        assert final.budget.files_verified == len({ref for branch in final.branches for ref in branch.verified_file_refs}) > 0
        assert final.rounds[-1].verified_file_refs
        assert not final.topology_admission.user_confirmation_required
        assert final.execution_policy == "automatic_readonly"
        assert not final.workspace_artifacts
        assert (await runtime.start("auto", request)).replayed
        assert len(analyst.inputs) == 5
        assert not any(event.event_name == "topology_confirmation_required" for event in final.events)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_auto_failure_never_replays_bad_branch_and_preserves_adopted_results():
    analyst = RepairAnalyst(always=True)
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        started = await runtime.start("auto", HarnessRunStart(instruction="核对上线风险", idempotency_key="automatic-failure",
            output_preference="analysis_only", execution_policy="automatic_readonly"))
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("auto", started.run.run_id)
        assert final.status == "waiting_input"
        assert analyst.counts[analyst.target] == 2  # Existing one bounded output repair.
        assert sum(item.output_used for item in final.worker_runs) >= 2
        assert final.artifact_versions
        before = len(analyst.inputs)
        await runtime._execute_automatic_worker_waves("auto", final.run_id)
        assert len(analyst.inputs) == before
    finally:
        await runtime.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["pause", "stop"])
async def test_user_control_prevents_automatic_downstream_wave(command):
    class HeldAnalyst(ContextAnalyst):
        def __init__(self):
            super().__init__()
            self.entered = 0
            self.ready = asyncio.Event()
            self.release = asyncio.Event()

        async def analyze(self, **kwargs):
            self.entered += 1
            if self.entered == 3:
                self.ready.set()
            await self.release.wait()
            return await super().analyze(**kwargs)

    analyst = HeldAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), FiveUnitFailurePlanner(), analyst)
    try:
        started = await runtime.start("auto", HarnessRunStart(instruction="核对上线风险", idempotency_key=f"automatic-{command}",
            output_preference="analysis_only", execution_policy="automatic_readonly"))
        await asyncio.wait_for(analyst.ready.wait(), 5)
        current = await runtime.get("auto", started.run.run_id)
        await runtime.control("auto", current.run_id, AgentControlLoopControlRequest(
            command=command, expected_version=current.version, idempotency_key=f"control-{command}"))
        task = runtime._tasks[current.run_id]
        analyst.release.set()
        await asyncio.wait_for(task, 5)
        final = await runtime.get("auto", current.run_id)
        assert len(analyst.inputs) == 3
        assert len(final.artifact_versions) == 1
        assert final.control_state == ("stopped" if command == "stop" else "paused")
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_automatic_authorization_does_not_bypass_human_gate():
    class HumanPlanner(FiveUnitFailurePlanner):
        async def plan(self, **kwargs):
            result = await super().plan(**kwargs)
            return result.model_copy(update={"units": [unit.model_copy(update={"requires_human_gate": True}) for unit in result.units]})

    analyst = ContextAnalyst()
    runtime = HarnessRuntime(_ten_file_cross_function_catalog(), HumanPlanner(), analyst)
    try:
        started = await runtime.start("auto", HarnessRunStart(instruction="核对上线风险", idempotency_key="automatic-human-gate",
            output_preference="analysis_only", execution_policy="automatic_readonly"))
        await runtime._tasks[started.run.run_id]
        final = await runtime.get("auto", started.run.run_id)
        assert final.status == "waiting_input"
        assert not analyst.inputs and not final.worker_runs and not final.workspace_artifacts
        assert any(event.event_name == "automatic_scope_blocked" for event in final.events)
    finally:
        await runtime.close()
