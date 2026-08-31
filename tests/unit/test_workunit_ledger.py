from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from services.api.app.application.harness_storage import InMemoryHarnessStateStore, StoredHarnessRun
from services.api.app.application.workunit_ledger import (
    ContributionGateStatus,
    ContributionRecord,
    WorkUnitLedgerConflict,
    WorkUnitRecord,
    WorkUnitState,
    WorkerModelReceipt,
    public_contribution,
    public_work_unit,
)


OWNER = "ledger-test-owner"
TASK = "task-aaaaaaaaaaaa"
RUN = "harness:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
BRANCH = "branch-aaaaaaaaaaaa"


def work_unit() -> WorkUnitRecord:
    return WorkUnitRecord(
        owner_id=OWNER,
        task_id=TASK,
        run_id=RUN,
        work_unit_id=BRANCH,
        branch_id=BRANCH,
        unit_id="u1",
        approved_file_refs=["forte-aaaaaaaaaaaaaaaa"],
    )


def contribution() -> ContributionRecord:
    return ContributionRecord(
        owner_id=OWNER,
        task_id=TASK,
        run_id=RUN,
        work_unit_id=BRANCH,
        branch_id=BRANCH,
        attempt=1,
        worker_run_id="worker-aaaaaaaaaaaa",
        run_source_revision="run-rev-1",
        catalog_source_revision="catalog-rev-1",
        approved_file_refs=("forte-aaaaaaaaaaaaaaaa",),
        model_receipt=WorkerModelReceipt(called=True, output_used=True, elapsed_ms=4),
        gate_status=ContributionGateStatus.ADOPTED,
        gate_reason="source and anchor accepted",
        artifact_version=1,
        summary="bounded result",
    )


def test_work_unit_reuses_branch_key_and_has_explicit_state_machine() -> None:
    record = work_unit()
    reserved = record.transition(WorkUnitState.READY).transition(WorkUnitState.RESERVED)
    running = reserved.transition(WorkUnitState.RUNNING)
    returned = running.transition(WorkUnitState.RETURNED)
    assert returned.transition(WorkUnitState.ADOPTED).state == WorkUnitState.ADOPTED
    with pytest.raises(WorkUnitLedgerConflict):
        record.transition(WorkUnitState.ADOPTED)
    with pytest.raises(ValueError, match="work_unit_id"):
        WorkUnitRecord(**{**record.model_dump(), "branch_id": "branch-bbbbbbbbbbbb"})


def test_contribution_is_frozen_and_public_projection_removes_private_revisions() -> None:
    record = contribution()
    with pytest.raises((TypeError, ValidationError)):
        record.gate_reason = "tampered"
    projected = public_contribution(record)
    assert "run_source_revision" not in projected
    assert "catalog_source_revision" not in projected
    assert "raw" not in str(projected).lower()
    assert "reservation_id" not in public_work_unit(work_unit())
    assert "owner_id" not in public_work_unit(work_unit())
    assert "owner_id" not in projected


@pytest.mark.asyncio
async def test_memory_snapshot_rejects_contribution_mutation_and_deletion() -> None:
    store = InMemoryHarnessStateStore()
    now = datetime.now(timezone.utc).isoformat()
    first = contribution().model_dump(mode="json")
    unit = work_unit().model_dump(mode="json")
    run = StoredHarnessRun(
        owner_id=OWNER,
        run_id=RUN,
        snapshot={
            "run_id": RUN,
            "owner_id": OWNER,
            "task_id": TASK,
            "contributions": [first],
            "work_units": [unit],
            "updated_at": now,
        },
    )
    await store.commit(run)
    with pytest.raises(RuntimeError, match="immutable Contribution"):
        await store.commit(
            StoredHarnessRun(
                owner_id=OWNER,
                run_id=RUN,
                snapshot={**run.snapshot, "contributions": [{**first, "summary": "changed"}]},
            )
        )
    with pytest.raises(RuntimeError, match="delete"):
        await store.commit(
            StoredHarnessRun(owner_id=OWNER, run_id=RUN, snapshot={**run.snapshot, "contributions": []})
        )

    duplicate = contribution().model_copy(update={"contribution_id": "contribution-bbbbbbbbbbbbbbbb"})
    with pytest.raises(RuntimeError, match="duplicate"):
        await store.commit(
            StoredHarnessRun(
                owner_id=OWNER,
                run_id=RUN,
                snapshot={**run.snapshot, "contributions": [first, duplicate.model_dump(mode="json")]},
            )
        )
