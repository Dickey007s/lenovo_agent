from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.contracts import (
    BranchSnapshot,
    DeliverableSpec,
    TaskContract,
    TaskContractDraft,
    TaskControlCommand,
    TaskSnapshot,
)


NOW = datetime(2026, 8, 10, 4, 0, tzinfo=UTC)


def contract_draft() -> TaskContractDraft:
    return TaskContractDraft(
        title="Customer A operating review",
        objective="Produce an analysis, a risk brief, and a reply draft.",
        source_scope=["fixture:mail/customer-a", "fixture:crm/customer-a"],
        allowed_capabilities=["document.draft", "email.draft"],
        deliverables=[
            DeliverableSpec(
                deliverable_id="operating-analysis",
                title="Operating analysis",
                kind="analysis",
                completion_criteria=["Every material claim has a source reference."],
            )
        ],
        completion_criteria=["Every required deliverable is verified."],
    )


def task_snapshot() -> TaskSnapshot:
    draft = contract_draft()
    contract = TaskContract(
        **draft.model_dump(),
        task_id="task_customer_a",
        owner_id="user_1",
        created_at=NOW,
    )
    branch = BranchSnapshot(
        branch_id="branch_analysis",
        task_id=contract.task_id,
        title="Operating analysis",
        objective="Reconcile the operating facts.",
        deliverable_ids=["operating-analysis"],
        created_at=NOW,
        updated_at=NOW,
    )
    return TaskSnapshot(
        task_id=contract.task_id,
        trace_id="trace_customer_a",
        owner_id=contract.owner_id,
        contract=contract,
        branches=[branch],
        created_at=NOW,
        updated_at=NOW,
    )


def test_task_contract_rejects_server_owned_and_unknown_fields() -> None:
    payload = contract_draft().model_dump(mode="json") | {
        "task_id": "model_must_not_choose_this",
        "status": "committed",
    }

    with pytest.raises(ValidationError):
        TaskContractDraft.model_validate(payload)


def test_task_contract_requires_unique_deliverables_and_sources() -> None:
    payload = contract_draft().model_dump()
    payload["deliverables"] = [payload["deliverables"][0], payload["deliverables"][0]]
    with pytest.raises(ValidationError, match="deliverable_id values must be unique"):
        TaskContractDraft.model_validate(payload)

    payload = contract_draft().model_dump()
    payload["source_scope"] = [payload["source_scope"][0], payload["source_scope"][0]]
    with pytest.raises(ValidationError, match="source_scope values must be unique"):
        TaskContractDraft.model_validate(payload)


def test_snapshot_rejects_identity_and_deliverable_reference_drift() -> None:
    snapshot = task_snapshot()

    with pytest.raises(ValidationError, match="task contract identity"):
        TaskSnapshot.model_validate(snapshot.model_dump() | {"owner_id": "other_user"})

    branch = snapshot.branches[0].model_copy(
        update={"deliverable_ids": ["unknown-deliverable"]}
    )
    with pytest.raises(ValidationError, match="unknown deliverable"):
        TaskSnapshot.model_validate(snapshot.model_dump() | {"branches": [branch]})


def test_control_commands_require_versions_and_command_specific_fields() -> None:
    steer = TaskControlCommand(
        kind="steer",
        instruction="Use the approved revenue baseline.",
        expected_task_version=3,
        idempotency_key="control-steer-001",
    )
    assert steer.expected_task_version == 3

    with pytest.raises(ValidationError, match="steer requires instruction"):
        TaskControlCommand(
            kind="steer",
            expected_task_version=3,
            idempotency_key="control-steer-002",
        )

    with pytest.raises(ValidationError, match="pause_branch requires branch_id"):
        TaskControlCommand(
            kind="pause_branch",
            expected_task_version=3,
            idempotency_key="control-pause-001",
        )

    with pytest.raises(ValidationError, match="resolve_evidence requires selected_source_ref"):
        TaskControlCommand(
            kind="resolve_evidence",
            branch_id="branch_analysis",
            expected_task_version=3,
            idempotency_key="control-resolve-001",
        )


def test_task_snapshot_round_trip_is_strict_and_stable() -> None:
    snapshot = task_snapshot()
    restored = TaskSnapshot.model_validate_json(snapshot.model_dump_json())

    assert restored == snapshot
    assert restored.status == "ready"
    assert restored.phase == "contract"
    assert restored.version == 1
