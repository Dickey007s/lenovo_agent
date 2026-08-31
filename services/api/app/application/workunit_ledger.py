"""Server-owned WorkUnit execution ledger for the bounded worker wave.

Branches remain the plan, dependency and evidence-gate authority.  A record in
this module only records execution attempts against an existing Branch; it
never copies or replaces Branch state.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from packages.contracts.harness_models import AgentControlLoopEvidenceAnchor


class WorkUnitLedgerConflict(RuntimeError):
    """A stale WorkUnit version, duplicate attempt, or command conflict."""


class WorkUnitState(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RESERVED = "reserved"
    RUNNING = "running"
    RETURNED = "returned"
    ADOPTED = "adopted"
    WAITING = "waiting"
    REJECTED = "rejected"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkUnitStatusReason(StrEnum):
    """Finite, server-owned explanations safe for the public projection."""

    CHECKPOINT_RECOVERED_IN_FLIGHT = "checkpoint_recovered_in_flight_worker"


class ContributionGateStatus(StrEnum):
    PENDING = "pending"
    ADOPTED = "adopted"
    WAITING = "waiting"
    REJECTED = "rejected"
    FAILED = "failed"


class WorkUnitRecord(BaseModel):
    """Mutable execution pointer, keyed one-to-one with a server Branch."""

    model_config = ConfigDict(extra="forbid")

    owner_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(pattern=r"^task-[0-9a-f]{12}$")
    run_id: str = Field(pattern=r"^harness:[0-9a-f]{32}$")
    work_unit_id: str = Field(pattern=r"^branch-[0-9a-f]{12}$")
    branch_id: str = Field(pattern=r"^branch-[0-9a-f]{12}$")
    unit_id: str = Field(min_length=1, max_length=120)
    depends_on: list[str] = Field(default_factory=list, max_length=12)
    approved_file_refs: list[str] = Field(min_length=1, max_length=24)
    state: WorkUnitState = WorkUnitState.PENDING
    attempt: int = Field(default=0, ge=0, le=24)
    version: int = Field(default=1, ge=1)
    reservation_id: str | None = Field(default=None, max_length=160)
    latest_contribution_id: str | None = Field(default=None, max_length=160)
    reserved_at: datetime | None = None
    started_at: datetime | None = None
    returned_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = Field(default=None, max_length=500)
    status_reason: WorkUnitStatusReason | None = None

    @model_validator(mode="after")
    def branch_is_authority_key(self) -> "WorkUnitRecord":
        if self.work_unit_id != self.branch_id:
            raise ValueError("work_unit_id must directly equal branch_id")
        return self

    def transition(
        self,
        target: WorkUnitState,
        *,
        error: str | None = None,
        status_reason: WorkUnitStatusReason | None = None,
    ) -> "WorkUnitRecord":
        allowed: dict[WorkUnitState, set[WorkUnitState]] = {
            WorkUnitState.PENDING: {WorkUnitState.READY, WorkUnitState.BLOCKED},
            WorkUnitState.READY: {WorkUnitState.RESERVED, WorkUnitState.BLOCKED},
            WorkUnitState.RESERVED: {WorkUnitState.RUNNING, WorkUnitState.FAILED},
            WorkUnitState.RUNNING: {WorkUnitState.RETURNED, WorkUnitState.FAILED},
            WorkUnitState.RETURNED: {
                WorkUnitState.ADOPTED,
                WorkUnitState.WAITING,
                WorkUnitState.REJECTED,
                WorkUnitState.FAILED,
            },
            WorkUnitState.ADOPTED: set(),
            WorkUnitState.WAITING: {WorkUnitState.RESERVED, WorkUnitState.BLOCKED},
            WorkUnitState.REJECTED: set(),
            # Only an in-flight attempt made uncertain by checkpoint recovery
            # may be explicitly retried. Ordinary execution failures remain
            # terminal.
            WorkUnitState.FAILED: {WorkUnitState.READY},
            WorkUnitState.BLOCKED: set(),
        }
        if target not in allowed[self.state]:
            raise WorkUnitLedgerConflict(f"illegal WorkUnit transition {self.state}->{target}")
        if (
            self.state == WorkUnitState.FAILED
            and target == WorkUnitState.READY
            and self.status_reason != WorkUnitStatusReason.CHECKPOINT_RECOVERED_IN_FLIGHT
        ):
            raise WorkUnitLedgerConflict("only checkpoint-recovered WorkUnit can be retried")
        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {"state": target, "version": self.version + 1, "updated_at": now}
        if target == WorkUnitState.RESERVED:
            values["reserved_at"] = now
        elif target == WorkUnitState.RUNNING:
            values["started_at"] = now
        elif target in {
            WorkUnitState.RETURNED,
            WorkUnitState.ADOPTED,
            WorkUnitState.WAITING,
            WorkUnitState.REJECTED,
            WorkUnitState.FAILED,
        }:
            values["returned_at"] = now
        if error is not None:
            values["error"] = error[:500]
        if status_reason is not None:
            values["status_reason"] = status_reason
        return self.model_copy(update=values)


class WorkerModelReceipt(BaseModel):
    """Sanitized receipt; raw provider output is deliberately absent."""

    model_config = ConfigDict(extra="forbid")

    called: bool = False
    output_used: bool = False
    elapsed_ms: int = Field(default=0, ge=0)
    model: str | None = Field(default=None, max_length=120)


class ContributionRecord(BaseModel):
    """Immutable server receipt for one worker attempt."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contribution_id: str = Field(default_factory=lambda: f"contribution-{uuid4().hex[:16]}")
    owner_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(pattern=r"^task-[0-9a-f]{12}$")
    run_id: str = Field(pattern=r"^harness:[0-9a-f]{32}$")
    work_unit_id: str = Field(pattern=r"^branch-[0-9a-f]{12}$")
    branch_id: str = Field(pattern=r"^branch-[0-9a-f]{12}$")
    attempt: int = Field(ge=1, le=24)
    worker_run_id: str = Field(min_length=1, max_length=160)
    run_source_revision: str = Field(min_length=1, max_length=120)
    catalog_source_revision: str = Field(min_length=1, max_length=120)
    approved_file_refs: tuple[str, ...] = Field(min_length=1, max_length=24)
    evidence_anchors: tuple[AgentControlLoopEvidenceAnchor, ...] = Field(default_factory=tuple, max_length=96)
    model_receipt: WorkerModelReceipt
    gate_status: ContributionGateStatus
    gate_reason: str = Field(min_length=1, max_length=500)
    artifact_version: int | None = Field(default=None, ge=1, le=24)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # A safe, bounded candidate summary is useful for audit projections.  It
    # is not a second Artifact store and never contains provider raw output.
    summary: str = Field(min_length=1, max_length=2_000)

    @model_validator(mode="after")
    def validate_branch_key(self) -> "ContributionRecord":
        if self.work_unit_id != self.branch_id:
            raise ValueError("contribution work_unit_id must equal branch_id")
        return self


def contribution_digest(record: ContributionRecord) -> str:
    """Stable comparison digest for idempotent append-only writes."""

    payload = record.model_dump(mode="json")
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def public_work_unit(record: WorkUnitRecord) -> dict[str, Any]:
    return record.model_dump(mode="json", exclude={"owner_id", "reservation_id", "error"})


def public_contribution(record: ContributionRecord) -> dict[str, Any]:
    payload = record.model_dump(mode="json")
    payload.pop("run_source_revision", None)
    payload.pop("catalog_source_revision", None)
    payload.pop("owner_id", None)
    return payload
