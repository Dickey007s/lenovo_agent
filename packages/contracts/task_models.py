from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel


TaskStatus = Literal[
    "ready",
    "running",
    "waiting_input",
    "paused",
    "taken_over",
    "verifying",
    "committed",
    "failed",
    "cancelled",
]

TaskPhase = Literal["contract", "observe", "plan", "act", "verify", "commit"]

TaskStage = Literal["observe", "plan", "act", "verify"]
TaskStageStatus = Literal["pending", "running", "completed", "failed"]
TaskStageSource = Literal["deterministic", "model", "template_fallback", "human", "system"]

BranchStatus = Literal[
    "queued",
    "running",
    "waiting_evidence",
    "paused",
    "taken_over",
    "verifying",
    "failed",
    "committed",
    "cancelled",
]

ArtifactStatus = Literal["candidate", "verified", "rejected", "committed", "invalidated"]
VerificationStatus = Literal["pending", "passed", "failed", "conflict"]
ConflictStatus = Literal["open", "resolved", "dismissed"]
ResolutionOptionKind = Literal["select_source"]
ImpactVerificationStatus = Literal["not_run", "passed", "partial", "failed"]
ExternalSideEffect = Literal["none", "simulator", "real"]
ImpactChangeKind = Literal["will_change", "will_recheck", "unchanged", "no_external_action"]
ControlKind = Literal[
    "steer",
    "pause_branch",
    "resume_branch",
    "take_over",
    "return_control",
    "resolve_evidence",
]
ControlStatus = Literal["accepted", "applied", "rejected"]

TaskEventType = Literal[
    "TASK_CREATED",
    "TASK_RESTORED",
    "TASK_STATUS_CHANGED",
    "TASK_PHASE_CHANGED",
    "BRANCH_STATUS_CHANGED",
    "LOOP_STEP_STARTED",
    "LOOP_STEP_COMPLETED",
    "ARTIFACT_VERSION_CREATED",
    "VERIFICATION_RECORDED",
    "CONFLICT_OPENED",
    "CONFLICT_RESOLVED",
    "CONTROL_ACCEPTED",
    "CONTROL_APPLIED",
    "CONTROL_REJECTED",
    "BUDGET_UPDATED",
    "CHECKPOINT_COMMITTED",
    "TASK_COMMITTED",
    "TASK_FAILED",
]


class DeliverableSpec(StrictModel):
    deliverable_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    kind: Literal[
        "analysis",
        "risk_brief",
        "reply_draft",
        "document",
        "mail",
        "structured_data",
    ]
    completion_criteria: list[str] = Field(min_length=1)


class TaskBudget(StrictModel):
    max_steps: int = Field(default=12, ge=1, le=100)
    max_tool_calls: int = Field(default=30, ge=0, le=1_000)
    max_runtime_seconds: int = Field(default=3_600, ge=1, le=86_400)


class TaskBudgetSnapshot(StrictModel):
    steps_used: int = Field(default=0, ge=0)
    tool_calls_used: int = Field(default=0, ge=0)
    runtime_seconds: int = Field(default=0, ge=0)
    exhausted: bool = False


class TaskContractDraft(StrictModel):
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=4_000)
    source_scope: list[str] = Field(min_length=1)
    allowed_capabilities: list[str] = Field(default_factory=list)
    deliverables: list[DeliverableSpec] = Field(min_length=1)
    completion_criteria: list[str] = Field(min_length=1)
    budget: TaskBudget = Field(default_factory=TaskBudget)
    deadline_at: datetime | None = None

    @model_validator(mode="after")
    def validate_unique_references(self) -> TaskContractDraft:
        deliverable_ids = [item.deliverable_id for item in self.deliverables]
        if len(deliverable_ids) != len(set(deliverable_ids)):
            raise ValueError("deliverable_id values must be unique")
        if len(self.source_scope) != len(set(self.source_scope)):
            raise ValueError("source_scope values must be unique")
        return self


class TaskContract(TaskContractDraft):
    schema_version: Literal["1.0"] = "1.0"
    task_id: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    contract_version: int = Field(default=1, ge=1)
    created_at: datetime


class BranchSnapshot(StrictModel):
    branch_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=2_000)
    deliverable_ids: list[str] = Field(min_length=1)
    status: BranchStatus = "queued"
    version: int = Field(default=1, ge=1)
    artifact_heads: dict[str, str] = Field(default_factory=dict)
    issue_ids: list[str] = Field(default_factory=list)
    pause_reason: str | None = None
    last_commit_id: str | None = None
    created_at: datetime
    updated_at: datetime


class ArtifactVersion(StrictModel):
    artifact_version_id: str = Field(min_length=1, max_length=160)
    artifact_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    branch_id: str = Field(min_length=1, max_length=120)
    deliverable_id: str = Field(min_length=1, max_length=100)
    version: int = Field(ge=1)
    parent_version_id: str | None = None
    title: str = Field(min_length=1, max_length=200)
    kind: str = Field(min_length=1, max_length=80)
    status: ArtifactStatus = "candidate"
    content: dict[str, Any] = Field(default_factory=dict)
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_refs: list[str] = Field(default_factory=list)
    created_by: Literal["agent", "human", "system"]
    created_at: datetime


class VerificationCheck(StrictModel):
    check_id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=200)
    status: Literal["passed", "failed", "conflict"]
    detail: str = Field(min_length=1, max_length=2_000)
    source_refs: list[str] = Field(default_factory=list)


class VerificationReport(StrictModel):
    report_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    branch_id: str = Field(min_length=1, max_length=120)
    artifact_version_id: str = Field(min_length=1, max_length=160)
    status: VerificationStatus
    checks: list[VerificationCheck] = Field(min_length=1)
    checked_at: datetime


class ImpactChange(StrictModel):
    """A business-facing before/after row for preview and receipt rendering."""

    change_kind: ImpactChangeKind
    label: str = Field(min_length=1, max_length=200)
    before: str | None = None
    after: str | None = None
    deliverable_ids: list[str] = Field(default_factory=list)
    artifact_version_ids: list[str] = Field(default_factory=list)


class ResolutionImpact(StrictModel):
    """Server-owned preview of the state change an option would cause."""

    task_status: TaskStatus | None = None
    task_phase: TaskPhase | None = None
    branch_status: BranchStatus | None = None
    changed_deliverable_ids: list[str] = Field(default_factory=list)
    creates_artifact_versions: int = Field(default=0, ge=0)
    creates_verification_reports: int = Field(default=0, ge=0)
    commit_created: bool = False
    external_side_effect: ExternalSideEffect = "none"
    changes: list[ImpactChange] = Field(default_factory=list)


class ConflictResolutionOption(StrictModel):
    """Executable, server-approved option exposed with a conflict."""

    option_id: str = Field(min_length=1, max_length=120)
    kind: ResolutionOptionKind = "select_source"
    label: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2_000)
    selected_source_ref: str = Field(min_length=1, max_length=500)
    executable: bool = True
    expected_impact: ResolutionImpact = Field(default_factory=ResolutionImpact)


class ConflictRecord(StrictModel):
    conflict_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    branch_id: str = Field(min_length=1, max_length=120)
    subject: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=2_000)
    source_refs: list[str] = Field(min_length=2)
    candidate_values: list[str] = Field(min_length=2)
    resolution_options: list[ConflictResolutionOption] = Field(default_factory=list)
    status: ConflictStatus = "open"
    resolution: str | None = None
    opened_at: datetime
    resolved_at: datetime | None = None

    @model_validator(mode="after")
    def validate_resolution_options(self) -> ConflictRecord:
        option_ids = [item.option_id for item in self.resolution_options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("resolution option_id values must be unique")
        if any(item.selected_source_ref not in self.source_refs for item in self.resolution_options):
            raise ValueError("resolution option source must be listed in conflict source_refs")
        return self


class TaskControlCommand(StrictModel):
    kind: ControlKind
    branch_id: str | None = None
    instruction: str | None = Field(default=None, max_length=4_000)
    reason: str | None = Field(default=None, max_length=1_000)
    resolution_option_id: str | None = Field(default=None, max_length=120)
    selected_source_ref: str | None = Field(default=None, max_length=500)
    expected_task_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=160)

    @model_validator(mode="after")
    def validate_command_shape(self) -> TaskControlCommand:
        if self.kind == "steer" and not self.instruction:
            raise ValueError("steer requires instruction")
        branch_kinds = {
            "pause_branch",
            "resume_branch",
            "take_over",
            "return_control",
            "resolve_evidence",
        }
        if self.kind in branch_kinds and not self.branch_id:
            raise ValueError(f"{self.kind} requires branch_id")
        if self.kind == "resolve_evidence" and not self.selected_source_ref:
            raise ValueError("resolve_evidence requires selected_source_ref")
        return self


class ImpactReceipt(StrictModel):
    """Actual server-observed impact committed with a control event."""

    from_task_version: int = Field(ge=1)
    to_task_version: int = Field(ge=1)
    impact_status: Literal["accepted", "applied", "rejected"] = "applied"
    changed_artifact_version_ids: list[str] = Field(default_factory=list)
    changed_deliverable_ids: list[str] = Field(default_factory=list)
    verification_report_ids: list[str] = Field(default_factory=list)
    verification_status: ImpactVerificationStatus = "not_run"
    commit_id: str | None = Field(default=None, max_length=120)
    commit_created: bool = False
    external_side_effect: ExternalSideEffect = "none"
    changes: list[ImpactChange] = Field(default_factory=list)
    summary: str = Field(min_length=1, max_length=2_000)


class ControlEvent(TaskControlCommand):
    control_event_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    actor_id: str = Field(min_length=1, max_length=120)
    status: ControlStatus
    applied_task_version: int | None = Field(default=None, ge=1)
    rejection_reason: str | None = None
    created_at: datetime
    applied_at: datetime | None = None
    impact_receipt: "ImpactReceipt | None" = None


class TaskCommit(StrictModel):
    commit_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    task_version: int = Field(ge=1)
    artifact_version_ids: list[str] = Field(min_length=1)
    verification_report_ids: list[str] = Field(min_length=1)
    state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    summary: str = Field(min_length=1, max_length=2_000)
    committed_at: datetime


class TaskError(StrictModel):
    code: str = Field(min_length=1, max_length=120)
    scope: Literal["task", "branch", "artifact", "control", "stream"]
    message: str = Field(min_length=1, max_length=2_000)
    recoverable: bool
    user_action: str | None = None


class TaskStageRecord(StrictModel):
    """Durable, user-facing record for one bounded runtime stage."""

    phase: TaskStage
    status: TaskStageStatus
    summary: str = Field(min_length=1, max_length=500)
    detail: dict[str, Any] = Field(default_factory=dict)
    artifact_version_ids: list[str] = Field(default_factory=list)
    generation_source: TaskStageSource
    started_at: datetime
    completed_at: datetime | None = None
    failed_at: datetime | None = None


class TaskSnapshot(StrictModel):
    task_id: str = Field(min_length=1, max_length=120)
    trace_id: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    contract: TaskContract
    status: TaskStatus = "ready"
    phase: TaskPhase = "contract"
    version: int = Field(default=1, ge=1)
    branches: list[BranchSnapshot] = Field(min_length=1)
    artifact_versions: list[ArtifactVersion] = Field(default_factory=list)
    verification_reports: list[VerificationReport] = Field(default_factory=list)
    conflicts: list[ConflictRecord] = Field(default_factory=list)
    controls: list[ControlEvent] = Field(default_factory=list)
    stage_records: list[TaskStageRecord] = Field(default_factory=list)
    budget: TaskBudgetSnapshot = Field(default_factory=TaskBudgetSnapshot)
    last_commit: TaskCommit | None = None
    last_event_sequence: int = Field(default=0, ge=0)
    last_error: TaskError | None = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_aggregate_references(self) -> TaskSnapshot:
        if self.contract.task_id != self.task_id or self.contract.owner_id != self.owner_id:
            raise ValueError("task contract identity must match snapshot identity")
        deliverable_ids = {item.deliverable_id for item in self.contract.deliverables}
        branch_ids: set[str] = set()
        for branch in self.branches:
            if branch.task_id != self.task_id:
                raise ValueError("branch task_id must match snapshot task_id")
            if branch.branch_id in branch_ids:
                raise ValueError("branch_id values must be unique")
            branch_ids.add(branch.branch_id)
            if not set(branch.deliverable_ids).issubset(deliverable_ids):
                raise ValueError("branch references an unknown deliverable")
        return self


class TaskEvent(StrictModel):
    sequence: int = Field(ge=1)
    event_id: str = Field(min_length=1, max_length=120)
    task_id: str = Field(min_length=1, max_length=120)
    trace_id: str = Field(min_length=1, max_length=120)
    task_version: int = Field(ge=1)
    branch_id: str | None = None
    artifact_version_id: str | None = None
    control_event_id: str | None = None
    actor_id: str = Field(min_length=1, max_length=120)
    event_type: TaskEventType
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime
