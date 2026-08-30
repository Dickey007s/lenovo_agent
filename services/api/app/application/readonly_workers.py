"""Bounded read-only worker execution and server-side contribution merge."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from typing import Awaitable, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from packages.contracts.harness_models import (
    AgentControlLoopArtifactFinding,
    AgentControlLoopNarrativeReconciliation,
)


class ReadonlyWorkerRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    worker_run_id: str = Field(min_length=1, max_length=160)
    branch_id: str = Field(min_length=1, max_length=120)
    goal: str = Field(min_length=3, max_length=1_000)
    source_file_refs: tuple[str, ...] = Field(min_length=1, max_length=24)
    expected_version: int = Field(ge=1)


WorkerOutcome = Literal["adopted", "failed", "ambiguous", "rejected"]


class ReadonlyWorkerContribution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker_run_id: str
    branch_id: str
    outcome: WorkerOutcome
    summary: str = Field(min_length=1, max_length=2_000)
    source_file_refs: tuple[str, ...] = Field(min_length=1, max_length=24)
    evidence_anchors: tuple[str, ...] = Field(default_factory=tuple, max_length=6)
    model_called: bool = False
    output_used: bool = False
    elapsed_ms: int = Field(default=0, ge=0)
    error: str | None = Field(default=None, max_length=500)
    # Every model receipt is reconciled, even when no deterministic effect is
    # available.  ``model_only`` is intentionally visible so it cannot be
    # mistaken for an authoritative Artifact effect.
    narrative_reconciliation: AgentControlLoopNarrativeReconciliation | None = None
    findings: tuple[AgentControlLoopArtifactFinding, ...] = Field(
        default_factory=tuple, max_length=10
    )


class SharedArtifactMerge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # This is the id of the normal logical ArtifactVersion, not a second
    # worker-only artifact namespace.
    artifact_id: str = Field(pattern=r"^artifact-[0-9a-f]{12}$")
    version: int = Field(ge=1)
    adopted_worker_run_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=3)
    adopted_contributions: tuple[ReadonlyWorkerContribution, ...] = Field(default_factory=tuple, max_length=3)
    waiting_branch_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=3)
    failed_worker_run_ids: tuple[str, ...] = Field(default_factory=tuple, max_length=3)
    created_at: datetime
    external_action: Literal["none"] = "none"


WorkerHandler = Callable[[ReadonlyWorkerRequest], Awaitable[ReadonlyWorkerContribution]]


async def execute_readonly_workers(
    requests: list[ReadonlyWorkerRequest],
    handler: WorkerHandler,
    *,
    max_workers: int = 3,
) -> list[ReadonlyWorkerContribution]:
    """Run no more than three branch-scoped handlers and preserve partial success."""

    if not 1 <= max_workers <= 3:
        raise ValueError("max_workers must be between 1 and 3")
    if len(requests) > max_workers:
        raise ValueError("worker request count exceeds the explicit hard cap")
    semaphore = asyncio.Semaphore(max_workers)

    async def run_one(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        async with semaphore:
            try:
                result = await handler(request)
            except Exception as exc:  # one failed Branch must not erase others
                return ReadonlyWorkerContribution(
                    worker_run_id=request.worker_run_id,
                    branch_id=request.branch_id,
                    outcome="failed",
                    summary="该工作分支执行失败，已保留其他分支成果。",
                    source_file_refs=request.source_file_refs,
                    error=str(exc)[:500],
                )
            if set(result.source_file_refs) - set(request.source_file_refs):
                return result.model_copy(
                    update={
                        "outcome": "rejected",
                        "output_used": False,
                        "error": "worker attempted to use a source outside its Branch",
                    }
                )
            return result

    return list(await asyncio.gather(*(run_one(request) for request in requests)))


def merge_adopted_contributions(
    contributions: list[ReadonlyWorkerContribution], *, version: int = 1
) -> SharedArtifactMerge:
    """Merge only adopted, anchored contributions; failed/ambiguous Branches wait."""

    adopted = tuple(
        item
        for item in contributions
        if (
            item.outcome == "adopted"
            and item.output_used
            and item.evidence_anchors
            and (
                item.narrative_reconciliation is None
                or item.narrative_reconciliation.model_disposition != "rejected"
            )
        )
    )
    adopted_ids = {item.worker_run_id for item in adopted}
    waiting = tuple(
        item.branch_id
        for item in contributions
        if item.worker_run_id not in adopted_ids
    )
    failed = tuple(item.worker_run_id for item in contributions if item.outcome == "failed")
    digest = hashlib.sha256(
        json.dumps([item.model_dump(mode="json") for item in adopted], sort_keys=True).encode()
    ).hexdigest()[:12]
    return SharedArtifactMerge(
        artifact_id=f"artifact-{digest}",
        version=version,
        adopted_worker_run_ids=tuple(item.worker_run_id for item in adopted),
        adopted_contributions=adopted,
        waiting_branch_ids=waiting,
        failed_worker_run_ids=failed,
        created_at=datetime.now(timezone.utc),
    )


# Names used by the application layer and tests.
ReadonlyWorkerManager = execute_readonly_workers
merge_worker_contributions = merge_adopted_contributions
