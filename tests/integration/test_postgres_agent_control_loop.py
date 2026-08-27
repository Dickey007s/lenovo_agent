from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import psycopg
import pytest

from packages.contracts.harness_models import AgentControlLoopControlRequest
from services.api.app.application.harness_runtime import HarnessRuntime
from services.api.app.application.harness_storage import PostgresHarnessStateStore
from tests.unit.test_harness_runtime import (
    AmbiguousCatalog,
    BlockingPlanner,
    FakeAnalyst,
    FakeCatalog,
    FakePlanner,
    MixedEvidenceAnalyst,
    confirm_evidence_gate,
    start_request,
    wait_status,
    wait_terminal,
)


DATABASE_DSN = os.getenv("TEST_DATABASE_DSN", "").strip()
pytestmark = pytest.mark.skipif(
    not DATABASE_DSN,
    reason="TEST_DATABASE_DSN is required for real PostgreSQL restart validation",
)


@pytest.mark.asyncio
async def test_postgres_recovers_loop_artifacts_commits_and_restore_pointer() -> None:
    owner = f"postgres-restart-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    try:
        blocking = BlockingPlanner()
        first = HarnessRuntime(
            FakeCatalog(),
            blocking,
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        request = start_request(
            idempotency_key=f"postgres-start-{uuid4().hex}",
        )
        started = await first.start(owner, request)
        run_id = started.run.run_id
        await asyncio.wait_for(blocking.started.wait(), timeout=3)
        await first.close()

        second = HarnessRuntime(
            FakeCatalog(),
            FakePlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        recovered = await second.get(owner, run_id)
        assert recovered.status == "paused"
        assert recovered.events[-1].event_name == "checkpoint_recovered"
        await second.control(
            owner,
            run_id,
            AgentControlLoopControlRequest(
                command="resume",
                idempotency_key=f"postgres-resume-{uuid4().hex}",
                expected_version=recovered.version,
            ),
        )
        await confirm_evidence_gate(
            second,
            owner,
            run_id,
            f"postgres-gate-{uuid4().hex}",
        )
        terminal = await wait_terminal(second, owner, run_id)
        assert terminal.status == "completed"
        assert terminal.last_commit and terminal.last_commit.artifact_version == 2
        await second.close()

        third_store = PostgresHarnessStateStore(DATABASE_DSN)
        third = HarnessRuntime(
            FakeCatalog(), FakePlanner(), FakeAnalyst(), third_store
        )
        runtimes.append(third)
        await third.setup()
        after_restart = await third.get(owner, run_id)
        assert after_restart.status == "completed"
        assert len(await third_store.load_artifact_versions(owner, run_id)) == 2
        assert len(await third_store.load_task_commits(owner, run_id)) == 1
        restored = await third.control(
            owner,
            run_id,
            AgentControlLoopControlRequest(
                command="rollback",
                artifact_version=1,
                idempotency_key=f"postgres-rollback-{uuid4().hex}",
                expected_version=after_restart.version,
            ),
        )
        assert restored.run.last_commit
        assert restored.run.last_commit.artifact_version == 1
        await third.close()

        fourth = HarnessRuntime(
            FakeCatalog(),
            FakePlanner(),
            FakeAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(fourth)
        await fourth.setup()
        final = await fourth.get(owner, run_id)
        assert final.last_commit and final.last_commit.artifact_version == 1
        assert len(final.commits) == 2
    finally:
        for runtime in reversed(runtimes):
            await runtime.close()
        if DATABASE_DSN and run_id:
            async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
                async with connection.cursor() as cursor:
                    for table in (
                        "harness_idempotency",
                        "harness_task_commit",
                        "harness_artifact_version",
                        "harness_run_state",
                    ):
                        await cursor.execute(
                            f"DELETE FROM {table} WHERE owner_id = %s",  # nosec B608
                            (owner,),
                        )


class TripleAmbiguousCatalog(AmbiguousCatalog):
    """Keep three identical excerpts so the test cannot pass by picking one at random."""

    def agent_file_inputs(self, file_refs: list[str]) -> list[dict[str, object]]:
        inputs = super().agent_file_inputs(file_refs)
        for item in inputs:
            if item["file_ref"] == "forte-2222222222222222":
                item["text"] = "复核说明\n其他内容\n复核说明\n附加说明\n复核说明"
        return inputs


class PostgresRecoveryAnalyst(MixedEvidenceAnalyst):
    """Return the ambiguous quote until the resumed branch gets a clean quote."""

    total_calls = 0

    async def analyze(self, *, instruction, plan, files, validation_feedback=None):
        type(self).total_calls += 1
        result = await super().analyze(
            instruction=instruction,
            plan=plan,
            files=files,
            validation_feedback=validation_feedback,
        )
        if type(self).total_calls < 3:
            return result
        finding = result.findings[1].model_copy(
            update={
                "evidence_quotes": [
                    result.findings[1].evidence_quotes[0].model_copy(
                        update={"quote": "附加说明"}
                    )
                ]
            }
        )
        return result.model_copy(
            update={"findings": [result.findings[0], finding]}
        )


@pytest.mark.asyncio
async def test_postgres_restarts_with_pending_decision_and_resumes_only_target_branch() -> None:
    """A real PostgreSQL gate for DR-0032's pending decision and local recovery path."""

    owner = f"postgres-decision-{uuid4().hex}"
    run_id = ""
    runtimes: list[HarnessRuntime] = []
    PostgresRecoveryAnalyst.total_calls = 0
    try:
        first = HarnessRuntime(
            TripleAmbiguousCatalog(),
            FakePlanner(),
            PostgresRecoveryAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(first)
        await first.setup()
        started = await first.start(
            owner,
            start_request(idempotency_key=f"decision-start-{uuid4().hex}"),
        )
        run_id = started.run.run_id
        waiting = await wait_status(first, owner, run_id, "waiting_input")
        resolution = waiting.rounds[0].next_step.evidence_resolutions[0]
        assert resolution.status == "ambiguous"
        assert len(resolution.candidates) == 3
        assert waiting.artifact_versions
        assert waiting.artifact_versions[0].version == 1
        assert waiting.branches[0].status == "completed"
        requests = getattr(waiting, "decision_requests", ())
        assert requests, "pending DecisionRequest must be in the authoritative Snapshot"
        assert requests[0].state == "open"
        await first.close()
        # The resumed provider call represents the post-decision clean locator;
        # seed the deterministic fixture past its two ambiguous attempts.
        PostgresRecoveryAnalyst.total_calls = 2

        second = HarnessRuntime(
            TripleAmbiguousCatalog(),
            FakePlanner(),
            PostgresRecoveryAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(second)
        await second.setup()
        restored = await second.get(owner, run_id)
        assert restored.status == "waiting_input"
        restored_resolution = restored.rounds[0].next_step.evidence_resolutions[0]
        assert restored_resolution.status == "ambiguous"
        assert {item.candidate_id for item in restored_resolution.candidates} == {
            item.candidate_id for item in resolution.candidates
        }
        restored_requests = getattr(restored, "decision_requests", ())
        assert restored_requests and restored_requests[0].state == "open"

        selected = restored_resolution.candidates[0].candidate_id
        decision = await second.control(
            owner,
            run_id,
            AgentControlLoopControlRequest(
                command="decision",
                decision_action="accept",
                finding_id=restored_resolution.finding_id,
                resolution_id=restored_resolution.resolution_id,
                branch_id=restored_resolution.branch_id,
                selected_candidate_id=selected,
                expected_version=restored.version,
                idempotency_key=f"decision-accept-{uuid4().hex}",
            ),
        )
        assert decision.run.decision_records[-1].action == "accept"
        assert decision.run.decision_records[-1].selected_candidate_id == selected
        target_branch_id = restored_resolution.branch_id
        assert target_branch_id
        assert all(
            branch.status == "completed"
            for branch in decision.run.branches
            if branch.branch_id != target_branch_id
        )

        after_decision = decision.run
        target_branch = next(
            branch for branch in after_decision.branches if branch.branch_id == target_branch_id
        )
        if target_branch.status != "completed":
            await second.control(
                owner,
                run_id,
                AgentControlLoopControlRequest(
                    command="resume",
                    branch_id=target_branch_id,
                    expected_version=after_decision.version,
                    idempotency_key=f"decision-resume-{uuid4().hex}",
                ),
            )
        terminal = await wait_terminal(second, owner, run_id)
        assert terminal.status == "completed"
        assert terminal.last_commit and terminal.last_commit.artifact_version == 2
        assert [item.version for item in terminal.artifact_versions] == [1, 2]
        assert all(item.status == "completed" for item in terminal.branches)
        assert any(
            event.event_name == "branch_resumed_from_checkpoint"
            and event.details.get("branch_id") == target_branch_id
            for event in terminal.events
        )

        await second.close()
        third = HarnessRuntime(
            TripleAmbiguousCatalog(),
            FakePlanner(),
            PostgresRecoveryAnalyst(),
            PostgresHarnessStateStore(DATABASE_DSN),
        )
        runtimes.append(third)
        await third.setup()
        final = await third.get(owner, run_id)
        assert final.status == "completed"
        assert [item.version for item in final.artifact_versions] == [1, 2]
        assert len(final.decision_records) == 1
        final_resolution = final.rounds[0].next_step.evidence_resolutions[0]
        assert final_resolution.resolution_id == resolution.resolution_id
        assert final_resolution.status == "exact"
    finally:
        for runtime in reversed(runtimes):
            await runtime.close()
        if DATABASE_DSN and run_id:
            async with await psycopg.AsyncConnection.connect(DATABASE_DSN) as connection:
                async with connection.cursor() as cursor:
                    for table in (
                        "harness_idempotency",
                        "harness_task_commit",
                        "harness_artifact_version",
                        "harness_run_state",
                    ):
                        await cursor.execute(
                            f"DELETE FROM {table} WHERE owner_id = %s",  # nosec B608
                            (owner,),
                        )
