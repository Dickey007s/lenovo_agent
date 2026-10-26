from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pytest
from pydantic import ValidationError

from services.api.app.application.harness_storage import (
    InMemoryHarnessStateStore,
    StoredHarnessRun,
    _validate_ledger_append,
)
from services.api.app.application.workunit_ledger import (
    ContributionGateStatus,
    ContributionRecord,
    WorkUnitLedgerConflict,
    WorkUnitRecord,
    WorkUnitState,
    WorkUnitStatusReason,
    WorkerModelReceipt,
    contribution_digest,
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
    failed = running.transition(WorkUnitState.FAILED, error="worker stopped")
    with pytest.raises(WorkUnitLedgerConflict, match="checkpoint-recovered"):
        failed.transition(WorkUnitState.READY)
    recovered = failed.model_copy(
        update={"status_reason": WorkUnitStatusReason.CHECKPOINT_RECOVERED_IN_FLIGHT}
    )
    assert recovered.transition(WorkUnitState.READY).state == WorkUnitState.READY
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


def test_legacy_handoff_defaults_preserve_payloads_digests_and_cas() -> None:
    for model in (WorkUnitRecord, ContributionRecord):
        schema = model.model_json_schema(mode="serialization")
        assert "input_contribution_ids" in schema["properties"]
        assert "branch_id" in schema["properties"]
    old_unit = work_unit().model_dump(mode="json", exclude={"input_contribution_ids"})
    old_row = contribution().model_dump(mode="json", exclude={"input_contribution_ids"})
    restored_unit = WorkUnitRecord.model_validate(old_unit)
    restored_row = ContributionRecord.model_validate(old_row)
    assert restored_unit.model_dump(mode="json") == old_unit
    assert restored_row.model_dump(mode="json") == old_row
    old_digest = hashlib.sha256(json.dumps(old_row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    assert contribution_digest(restored_row) == old_digest
    base = {
        "owner_id": OWNER, "task_id": TASK, "run_id": RUN,
        "branches": [{"branch_id": BRANCH, "unit_id": "u1", "depends_on": [],
                      "input_file_refs": ["forte-aaaaaaaaaaaaaaaa"]}],
        "work_units": [old_unit], "contributions": [old_row],
    }
    restored = {**base, "work_units": [restored_unit.model_dump(mode="json")],
                "contributions": [restored_row.model_dump(mode="json")]}
    _validate_ledger_append(base, restored)
    changed = restored_row.model_copy(update={"input_contribution_ids": ("contribution-parent",)})
    assert contribution_digest(changed) != old_digest
    with pytest.raises(RuntimeError, match="immutable Contribution"):
        _validate_ledger_append(base, {**restored, "contributions": [changed.model_dump(mode="json")]})
    changed_unit = restored_unit.model_copy(update={"input_contribution_ids": ("contribution-parent",)})
    with pytest.raises(RuntimeError, match="WorkUnit version CAS"):
        _validate_ledger_append(base, {**restored, "work_units": [changed_unit.model_dump(mode="json")]})


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
            "branches": [
                {
                    "branch_id": BRANCH,
                    "unit_id": "u1",
                    "depends_on": [],
                    "input_file_refs": ["forte-aaaaaaaaaaaaaaaa"],
                }
            ],
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


def test_ledger_binds_sources_to_branch_and_work_unit() -> None:
    unit = work_unit().model_dump(mode="json")
    row = contribution().model_dump(mode="json")
    base = {
        "owner_id": OWNER,
        "task_id": TASK,
        "run_id": RUN,
        "workspace_revision": "run-rev-1",
        "branches": [
            {
                "branch_id": BRANCH,
                "unit_id": "u1",
                "depends_on": [],
                "input_file_refs": ["forte-aaaaaaaaaaaaaaaa"],
            }
        ],
        "work_units": [unit],
        "contributions": [row],
    }
    _validate_ledger_append(None, base)
    with pytest.raises(RuntimeError, match="WorkUnit projection"):
        _validate_ledger_append(
            None,
            {**base, "work_units": [{**unit, "approved_file_refs": ["forte-bbbbbbbbbbbbbbbb"]}]},
        )
    with pytest.raises(RuntimeError, match="Contribution approved sources"):
        _validate_ledger_append(
            None,
            {**base, "contributions": [{**row, "approved_file_refs": ["forte-bbbbbbbbbbbbbbbb"]}]},
        )
    with pytest.raises(RuntimeError, match="source revision"):
        _validate_ledger_append(
            None,
            {**base, "contributions": [{**row, "run_source_revision": "run-rev-2"}]},
        )
