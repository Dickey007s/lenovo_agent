"""Offline integration gates for research and single-action tasks in one runtime."""

import pytest

from packages.contracts.office_actions import OfficeActionControl
from services.api.app.application.harness_runtime import (
    HarnessConflictError,
    HarnessPlanCandidate,
    HarnessPlanCandidateUnit,
    HarnessRunStart,
    HarnessRuntime,
)
from tests.acceptance.test_demo1_demo2_fixed_scenarios import _wait_for
from tests.unit.test_demo2_runtime import _cross_function_catalog
from tests.unit.test_harness_runtime import FakeAnalyst


class ResearchPlanner:
    model = "offline-integration-planner"

    def __init__(self, swarm):
        self.swarm = swarm
        self.calls = 0

    async def plan(self, *, scenario, files):
        self.calls += 1
        return HarnessPlanCandidate(
            summary="Read approved sources independently.",
            selection_reason="The fixture uses bounded independent source scopes.",
            units=[HarnessPlanCandidateUnit(
                unit_id=f"source-{index}", title=f"Source review {index}",
                objective="Review this approved source without writing files.",
                input_file_refs=[item["file_ref"]], tool="file.read",
            ) for index, item in enumerate(files[:2 if self.swarm else 1], start=1)],
        )


class CountingAnalyst(FakeAnalyst):
    def __init__(self):
        super().__init__()
        self.calls = 0

    async def analyze(self, **kwargs):
        self.calls += 1
        return await super().analyze(**{
            key: kwargs[key] for key in ("instruction", "plan", "files", "validation_feedback")
        })


@pytest.mark.parametrize("swarm", [False, True], ids=["control-loop", "adaptive-swarm"])
async def test_office_action_preserves_research_task_and_idempotency(swarm):
    planner, analyst = ResearchPlanner(swarm), CountingAnalyst()
    runtime = HarnessRuntime(_cross_function_catalog(), planner, analyst)
    owner = "shared-demo-owner"
    research_request = HarnessRunStart(
        instruction="Review the approved material without external actions.",
        output_preference="analysis_only", idempotency_key="shared-research-start",
        loop={"max_rounds": 2, "max_files_per_round": 2,
              "max_model_calls": 8, "deadline_seconds": 120},
    )
    try:
        started = await runtime.start(owner, research_request)
        research = await _wait_for(runtime, owner, started.run.run_id,
                                   lambda run: run.status in {"completed", "waiting_input", "failed"})
        if swarm:
            assert research.status == "waiting_input"
            assert research.topology_admission.mode == "adaptive_readonly_workers"
            research = await runtime.execute_admitted_workers_from_branches(
                owner, research.run_id, branch_ids=[], expected_version=research.version,
                idempotency_key="shared-research-workers", user_confirmed=True,
            )
            assert len(research.contributions) == 2
            assert all(item.gate_status == "adopted" for item in research.contributions)
        assert research.status == "completed", research.validation_errors
        assert research.artifact_versions
        assert research.contract.output_policy == "analysis_only"
        assert not research.workspace_artifacts and not research.effect_receipts
        research_before = research.model_dump(mode="json")
        task_before = (await runtime.get_task(owner, research.task_id)).model_dump(mode="json")
        calls_before = (planner.calls, analyst.calls)
        assert calls_before == (1, 2 if swarm else 1)

        action_request = HarnessRunStart(
            instruction="Prepare a local test task.", output_preference="analysis_only",
            idempotency_key="shared-action-start",
            action={"operation": "create_task", "title": "Review delivery notes",
                    "content": "Check the documented source boundary.",
                    "target": "wang-engineering", "due_date": "2026-10-09"},
        )
        action_run = (await runtime.start(owner, action_request)).run
        assert action_run.task_id != research.task_id
        assert action_run.contract.output_policy == "analysis_only"
        assert action_run.office_action.status == "awaiting_confirmation"
        confirmation = OfficeActionControl(
            command="confirm", expected_version=action_run.version,
            action_revision=action_run.office_action.revision,
            idempotency_key="shared-action-confirm",
        )
        confirmed = await runtime.office_action_control(owner, action_run.run_id, confirmation)
        assert confirmed.run.status == "completed"
        assert confirmed.run.office_action.receipt.kind == "test_task"
        assert confirmed.run.office_action.external_action == "none"
        assert not confirmed.run.office_action.model_called
        assert not confirmed.run.workspace_artifacts and not confirmed.run.effect_receipts
        assert not confirmed.run.work_units and not confirmed.run.contributions

        # Replaying either protocol must not rewind its current Snapshot or its neighbour.
        research_replay = await runtime.start(owner, research_request)
        action_replay = await runtime.start(owner, action_request)
        control_replay = await runtime.office_action_control(owner, action_run.run_id, confirmation)
        assert research_replay.replayed and action_replay.replayed and control_replay.replayed
        assert research_replay.run.run_id == research.run_id
        assert action_replay.run.run_id == action_run.run_id
        assert control_replay.run.model_dump(mode="json") == confirmed.run.model_dump(mode="json")
        with pytest.raises(HarnessConflictError):
            await runtime.office_action_control(owner, action_run.run_id,
                                                confirmation.model_copy(update={"command": "cancel"}))
        with pytest.raises(HarnessConflictError):
            await runtime.start(owner, research_request.model_copy(update={"action": action_request.action}))
        assert (planner.calls, analyst.calls) == calls_before
        assert (await runtime.get(owner, research.run_id)).model_dump(mode="json") == research_before
        assert (await runtime.get_task(owner, research.task_id)).model_dump(mode="json") == task_before
        assert ((await runtime.get(owner, action_run.run_id)).model_dump(mode="json")
                == confirmed.run.model_dump(mode="json"))
    finally:
        await runtime.close()
