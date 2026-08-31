"""Server-owned task identity DTOs.

Task persistence deliberately lives in ``HarnessStateStore``. Keeping one
aggregate boundary prevents a task CAS, child Run and command receipt from
being committed by separate best-effort stores.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class TaskLedgerConflict(RuntimeError):
    """The task version or idempotency command no longer matches."""


class TaskRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(pattern=r"^task-[0-9a-f]{12}$")
    owner_id: str = Field(min_length=1, max_length=120)
    task_version: int = Field(default=1, ge=1)
    workspace_id: str = Field(min_length=1, max_length=120)
    workspace_revision: str = Field(min_length=1, max_length=120)
    current_run_id: str = Field(pattern=r"^harness:[0-9a-f]{32}$")
    run_sequence: int = Field(default=1, ge=1)
    parent_run_id: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskLedgerReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(default_factory=lambda: f"task-receipt-{uuid4().hex}")
    task_id: str
    owner_id: str
    idempotency_key: str = Field(min_length=8, max_length=160)
    from_task_version: int = Field(ge=1)
    to_task_version: int = Field(ge=1)
    child_run_id: str = Field(pattern=r"^harness:[0-9a-f]{32}$")
    parent_run_id: str = Field(pattern=r"^harness:[0-9a-f]{32}$")
    recheck_file_refs: list[str] = Field(default_factory=list, max_length=24)
    created_at: datetime


def command_digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
