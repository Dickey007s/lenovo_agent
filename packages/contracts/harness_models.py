"""Contracts for the pinned FORTE public office workspace.

The public manifest is the server-owned allowlist. The foreground only receives
stable references and business-facing folder/file metadata; raw paths, hashes,
benchmark prompts, rubrics and solutions stay behind the catalog boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, ValidationInfo, field_validator, model_validator

from .models import StrictModel


BenchmarkFileRole = Literal["input", "task_instruction"]
BenchmarkAvailability = Literal[
    "local_input_bundle",
    "task_only_requires_external_system",
]
BenchmarkPreviewKind = Literal["table", "document", "pdf", "text", "unavailable"]
AgentControlLoopEvidenceRole = Literal[
    "expected",
    "observed",
    "support",
    "contradiction",
    "context",
]
AgentControlLoopEvidenceLocatorKind = Literal["text_lines", "table_rows"]
AgentControlLoopEvidenceResolutionStatus = Literal[
    "exact",
    "ambiguous",
    "unavailable",
    "stale",
    "rejected",
]
AgentControlLoopDecisionOptionId = Literal["A", "B", "C"]
AgentControlLoopDecisionAction = Literal["accept", "decline", "defer", "cancel"]
AgentControlLoopRecoveryKind = Literal["source_location", "analysis_output"]
AgentControlLoopPhase = Literal[
    "observe",
    "plan",
    "act",
    "verify",
    "evidence_gate",
    "commit",
]
AgentControlLoopGateDecision = Literal[
    "pending",
    "next_round",
    "completed",
    "budget_exhausted",
    "waiting_input",
    "user_stopped",
    "failed",
]
AgentControlLoopControlState = Literal[
    "running",
    "pause_requested",
    "paused",
    "stop_requested",
    "stopped",
]
AgentControlLoopCommand = Literal[
    "pause",
    "resume",
    "steer",
    "stop",
    "rollback",
    "decision",
]
AgentControlLoopBranchStatus = Literal[
    "running",
    "completed",
    "waiting_input",
    "stopped",
    "failed",
]


def _validate_relative_path(value: str, label: str) -> str:
    normalized = value.replace("\\", "/")
    if normalized != value or normalized.startswith("/"):
        raise ValueError(f"{label} must use a relative POSIX path")
    if "\x00" in value or ":" in value or ".." in normalized.split("/"):
        raise ValueError(f"{label} is unsafe")
    if any(not part for part in normalized.split("/")):
        raise ValueError(f"{label} contains an empty segment")
    return value


class BenchmarkFileEntry(StrictModel):
    path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size: int = Field(gt=0, le=10 * 1024 * 1024)
    mime: str = Field(min_length=1, max_length=160)
    role: BenchmarkFileRole

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        return _validate_relative_path(value, "benchmark file path")


class BenchmarkPublicSuiteScope(StrictModel):
    full_benchmark_task_count_reported_by_upstream: int = Field(ge=1)
    public_demo_task_count: int = Field(ge=1)
    local_input_bundle_task_count: int = Field(ge=1)
    task_only_external_dependency_count: int = Field(ge=0)
    task_instruction_file_count: int = Field(ge=1)
    input_file_count: int = Field(ge=1)
    task_instruction_bytes: int = Field(ge=1)
    input_bytes: int = Field(ge=1)
    imported_bytes: int = Field(ge=1)


class BenchmarkPublicSuiteTask(StrictModel):
    task_id: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=120)
    availability: BenchmarkAvailability
    external_dependency: str | None = Field(default=None, max_length=160)
    task_file: BenchmarkFileEntry
    input_dir: str | None = Field(default=None, max_length=300)
    input_file_count: int = Field(ge=0, le=100)
    input_bytes: int = Field(ge=0)
    file_extensions: list[str] = Field(default_factory=list, max_length=40)
    input_files: list[BenchmarkFileEntry] = Field(default_factory=list, max_length=100)

    @field_validator("input_dir")
    @classmethod
    def validate_input_dir(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_relative_path(value, "benchmark input_dir")


class BenchmarkManifest(StrictModel):
    schema_version: Literal["1.0"]
    dataset: str = Field(min_length=1, max_length=200)
    source_url: str = Field(min_length=1, max_length=1_000)
    source_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    license: str = Field(min_length=1, max_length=120)
    content_nature: Literal["public_benchmark_demo_inputs"]
    scope: BenchmarkPublicSuiteScope
    excluded_upstream_material: list[str] = Field(min_length=1, max_length=20)
    tasks: list[BenchmarkPublicSuiteTask] = Field(min_length=1, max_length=100)


class BenchmarkDisplayFile(StrictModel):
    file_ref: str = Field(pattern=r"^forte-[0-9a-f]{16}$")
    folder_id: str = Field(pattern=r"^forte-folder-[0-9a-f]{12}$")
    display_label: str = Field(min_length=1, max_length=200)
    display_group: str = Field(min_length=1, max_length=120)
    display_path: str = Field(min_length=1, max_length=500)
    display_summary: str = Field(min_length=1, max_length=500)
    extension: str = Field(min_length=1, max_length=20)
    mime: str = Field(min_length=1, max_length=160)
    size: int = Field(gt=0, le=10 * 1024 * 1024)
    preview_kind: BenchmarkPreviewKind
    preview_available: bool


class BenchmarkWorkspaceFolder(StrictModel):
    folder_id: str = Field(pattern=r"^forte-folder-[0-9a-f]{12}$")
    display_label: str = Field(min_length=1, max_length=120)
    display_summary: str = Field(min_length=1, max_length=300)
    availability: BenchmarkAvailability
    external_dependency_label: str | None = Field(default=None, max_length=240)
    file_count: int = Field(ge=0, le=100)
    total_bytes: int = Field(ge=0)
    files: list[BenchmarkDisplayFile] = Field(default_factory=list, max_length=100)


class BenchmarkPublicWorkspace(StrictModel):
    workspace_id: Literal["forte-public-office"] = "forte-public-office"
    title: str = Field(min_length=1, max_length=200)
    dataset_label: str = Field(min_length=1, max_length=200)
    dataset_version: str = Field(min_length=1, max_length=120)
    source_label: str = Field(min_length=1, max_length=240)
    license: str = Field(min_length=1, max_length=120)
    data_boundary: str = Field(min_length=1, max_length=500)
    file_count: int = Field(ge=1)
    folder_count: int = Field(ge=1)
    previewable_file_count: int = Field(ge=0)
    folders: list[BenchmarkWorkspaceFolder] = Field(min_length=1, max_length=100)


class BenchmarkPreviewRow(StrictModel):
    row_number: int = Field(ge=1)
    values: list[str] = Field(max_length=30)


class BenchmarkPreviewSecurity(StrictModel):
    integrity_verified: Literal[True] = True
    read_only: Literal[True] = True
    active_content_executed: Literal[False] = False
    external_resources_loaded: Literal[False] = False
    notes: list[str] = Field(default_factory=list, max_length=8)


class BenchmarkFilePreview(StrictModel):
    workspace_id: Literal["forte-public-office"] = "forte-public-office"
    file_ref: str = Field(pattern=r"^forte-[0-9a-f]{16}$")
    folder_id: str = Field(pattern=r"^forte-folder-[0-9a-f]{12}$")
    display_label: str = Field(min_length=1, max_length=200)
    display_group: str = Field(min_length=1, max_length=120)
    display_path: str = Field(min_length=1, max_length=500)
    display_summary: str = Field(min_length=1, max_length=500)
    mime: str = Field(min_length=1, max_length=160)
    size: int = Field(gt=0, le=10 * 1024 * 1024)
    kind: BenchmarkPreviewKind
    sheet_name: str | None = Field(default=None, max_length=120)
    columns: list[str] = Field(default_factory=list, max_length=30)
    rows: list[BenchmarkPreviewRow] = Field(default_factory=list, max_length=120)
    total_rows: int | None = Field(default=None, ge=0)
    text: str | None = Field(default=None, max_length=30_000)
    page_count: int | None = Field(default=None, ge=0, le=1_000)
    truncated: bool = False
    security: BenchmarkPreviewSecurity


class AgentControlLoopOptions(StrictModel):
    """User-adjustable bounds; the server expands these into a frozen contract."""

    max_rounds: int = Field(default=12, ge=1, le=24)
    max_files_per_round: int = Field(default=16, ge=1, le=24)
    max_model_calls: int = Field(default=30, ge=2, le=60)
    deadline_seconds: int = Field(default=7_200, ge=20, le=14_400)


class AgentControlLoopContract(StrictModel):
    contract_version: Literal["agent-control-loop.v1"] = "agent-control-loop.v1"
    goal: str = Field(min_length=3, max_length=2_000)
    scope_mode: Literal["whole_workspace"] = "whole_workspace"
    allowed_file_refs: list[str] = Field(default_factory=list, max_length=100)
    completion_criteria: list[str] = Field(min_length=1, max_length=6)
    max_rounds: int = Field(ge=1, le=24)
    max_files_per_round: int = Field(ge=1, le=24)
    max_model_calls: int = Field(ge=2, le=60)
    deadline_seconds: int = Field(ge=20, le=14_400)
    external_action: Literal["none"] = "none"


class AgentControlLoopBudget(StrictModel):
    max_rounds: int = Field(ge=1, le=24)
    max_files_per_round: int = Field(ge=1, le=24)
    max_model_calls: int = Field(ge=2, le=60)
    deadline_seconds: int = Field(ge=20, le=14_400)
    rounds_used: int = Field(default=0, ge=0, le=24)
    files_verified: int = Field(default=0, ge=0, le=100)
    model_calls_used: int = Field(default=0, ge=0, le=60)
    elapsed_ms: int = Field(default=0, ge=0)
    stop_reason: str | None = Field(default=None, max_length=240)


class AgentControlLoopEvidenceGap(StrictModel):
    gap_id: str = Field(pattern=r"^gap-[0-9a-f]{12}$")
    branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    label: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=1_000)
    candidate_file_refs: list[str] = Field(default_factory=list, max_length=20)


class AgentControlLoopEvidenceCandidate(StrictModel):
    """One server-located candidate; it is not adopted until uniquely resolved."""

    candidate_id: str = Field(pattern=r"^candidate-[0-9a-f]{12}$")
    file_ref: str = Field(pattern=r"^forte-[0-9a-f]{16}$")
    locator_kind: AgentControlLoopEvidenceLocatorKind
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    excerpt: str = Field(min_length=1, max_length=1_200)
    source_revision: str = Field(default="", max_length=128)
    candidate_digest: str = Field(default="", max_length=128)

    @field_validator("end")
    @classmethod
    def validate_end(cls, value: int, info) -> int:
        start = info.data.get("start")
        if isinstance(start, int) and value < start:
            raise ValueError("evidence candidate end must not precede start")
        return value


class AgentControlLoopEvidenceResolution(StrictModel):
    """Server fact describing whether one model quote can locate source evidence."""

    resolution_id: str = Field(pattern=r"^resolution-[0-9a-f]{12}$")
    finding_id: str = Field(pattern=r"^finding-[0-9a-f]{12}$")
    plan_unit_id: str | None = Field(default=None, min_length=1, max_length=120)
    finding_title: str = Field(min_length=1, max_length=240)
    fact_summary: str | None = Field(default=None, max_length=500)
    impact: str | None = Field(default=None, max_length=500)
    branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    file_ref: str = Field(pattern=r"^forte-[0-9a-f]{16}$")
    role: AgentControlLoopEvidenceRole
    label: str = Field(min_length=1, max_length=120)
    query_excerpt: str = Field(min_length=4, max_length=600)
    status: AgentControlLoopEvidenceResolutionStatus
    reason: str = Field(min_length=1, max_length=500)
    candidates: list[AgentControlLoopEvidenceCandidate] = Field(default_factory=list, max_length=6)
    selected_candidate_id: str | None = Field(default=None, pattern=r"^candidate-[0-9a-f]{12}$")
    source_revision: str = Field(default="", max_length=128)
    decision_status: Literal["pending", "accepted", "declined", "deferred", "cancelled"] = "pending"


class AgentControlLoopNextStep(StrictModel):
    decision: AgentControlLoopGateDecision
    reason: str = Field(min_length=1, max_length=1_000)
    next_question: str | None = Field(default=None, max_length=2_000)
    candidate_file_refs: list[str] = Field(default_factory=list, max_length=20)
    candidate_branch_ids: list[str] = Field(default_factory=list, max_length=36)
    recovery_kind: AgentControlLoopRecoveryKind | None = None
    evidence_resolutions: list[AgentControlLoopEvidenceResolution] = Field(
        default_factory=list, max_length=20
    )


class AgentControlLoopBranch(StrictModel):
    """Server-owned task branch compiled from one validated plan unit."""

    branch_id: str = Field(pattern=r"^branch-[0-9a-f]{12}$")
    unit_id: str = Field(min_length=1, max_length=120)
    round_number: int = Field(ge=1, le=24)
    parent_branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    title: str = Field(min_length=1, max_length=240)
    objective: str = Field(min_length=1, max_length=1_000)
    depends_on: list[str] = Field(default_factory=list, max_length=12)
    input_file_refs: list[str] = Field(min_length=1, max_length=24)
    verified_file_refs: list[str] = Field(default_factory=list, max_length=24)
    missing_file_refs: list[str] = Field(default_factory=list, max_length=24)
    status: AgentControlLoopBranchStatus
    requires_human_gate: bool = False
    created_at: datetime
    updated_at: datetime


class AgentControlLoopRound(StrictModel):
    round_number: int = Field(ge=1, le=24)
    status: Literal["running", "completed", "stopped", "failed"]
    phase: AgentControlLoopPhase
    question: str = Field(min_length=3, max_length=2_000)
    steer_instruction: str | None = Field(default=None, max_length=2_000)
    input_file_refs: list[str] = Field(default_factory=list, max_length=24)
    branch_ids: list[str] = Field(default_factory=list, max_length=12)
    plan: dict[str, Any] | None = None
    model_receipt: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    analysis_receipt: dict[str, Any] | None = None
    verified_file_refs: list[str] = Field(default_factory=list, max_length=20)
    evidence_gaps: list[AgentControlLoopEvidenceGap] = Field(default_factory=list, max_length=20)
    next_step: AgentControlLoopNextStep | None = None
    started_at: datetime
    completed_at: datetime | None = None


class AgentControlLoopControlEvent(StrictModel):
    control_id: str = Field(pattern=r"^control-[0-9a-f]{12}$")
    command: AgentControlLoopCommand
    branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    artifact_version: int | None = Field(default=None, ge=1, le=24)
    instruction: str | None = Field(default=None, max_length=2_000)
    accepted_at: datetime
    accepted_task_version: int = Field(ge=1)
    applied_task_version: int | None = Field(default=None, ge=1)
    status: Literal["accepted", "applied", "rejected"]


class AgentControlLoopDecisionRecord(StrictModel):
    """Versioned, idempotent human receipt bound to a Finding or Resolution."""

    decision_id: str = Field(pattern=r"^decision-[0-9a-f]{12}$")
    decision_request_id: str | None = Field(
        default=None, pattern=r"^decision-request-[0-9a-f]{12}$"
    )
    action: AgentControlLoopDecisionAction
    finding_id: str = Field(pattern=r"^finding-[0-9a-f]{12}$")
    resolution_id: str | None = Field(default=None, pattern=r"^resolution-[0-9a-f]{12}$")
    branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    selected_option_id: AgentControlLoopDecisionOptionId | None = None
    selected_candidate_id: str | None = Field(default=None, pattern=r"^candidate-[0-9a-f]{12}$")
    feedback: str | None = Field(default=None, max_length=2_000)
    recorded_at: datetime
    source_revision: str = Field(default="", max_length=128)
    candidate_digest: str | None = Field(default=None, max_length=128)
    expected_version: int = Field(default=1, ge=1)
    # The raw key is retained only in the private state store; public snapshots
    # project it to this stable opaque reference.
    idempotency_key: str | None = Field(default=None, max_length=160)
    idempotency_ref: str = Field(default="", max_length=40)
    accepted_task_version: int = Field(ge=1)
    applied_task_version: int | None = Field(default=None, ge=1)
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    required_file_refs: list[str] = Field(default_factory=list, max_length=20)
    effect: Literal["branch_resumed", "preserved", "deferred", "cancelled", "none"] = "none"
    external_action: Literal["none"] = "none"


class AgentControlLoopDecisionRequest(StrictModel):
    """Server-owned pending decision packet exposed by a run Snapshot."""

    decision_request_id: str = Field(pattern=r"^decision-request-[0-9a-f]{12}$")
    run_id: str = Field(min_length=1, max_length=120)
    finding_id: str = Field(pattern=r"^finding-[0-9a-f]{12}$")
    resolution_id: str | None = Field(default=None, pattern=r"^resolution-[0-9a-f]{12}$")
    plan_unit_id: str | None = Field(default=None, min_length=1, max_length=120)
    branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    state: Literal["open", "accepted", "declined", "deferred", "cancelled", "stale", "rejected"] = (
        "open"
    )
    reason: str = Field(min_length=1, max_length=1_000)
    allowed_actions: list[AgentControlLoopDecisionAction] = Field(
        default_factory=lambda: ["accept", "decline", "defer", "cancel"], max_length=4
    )
    options: list[dict[str, Any]] = Field(default_factory=list, max_length=3)
    selected_option_id: AgentControlLoopDecisionOptionId | None = None
    selected_candidate_id: str | None = Field(default=None, pattern=r"^candidate-[0-9a-f]{12}$")
    candidates: list[AgentControlLoopEvidenceCandidate] = Field(default_factory=list, max_length=6)
    source_revision: str = Field(default="", max_length=128)
    expected_version: int = Field(ge=1)
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    required_file_refs: list[str] = Field(default_factory=list, max_length=20)
    estimated_additional_rounds: int = Field(default=0, ge=0, le=24)
    consequence: str = Field(min_length=1, max_length=1_000)
    requested_at: datetime
    external_action: Literal["none"] = "none"


class AgentControlLoopBrief(StrictModel):
    outcome: Literal["completed", "bounded", "user_stopped"]
    summary: str = Field(min_length=1, max_length=3_000)
    verified_file_refs: list[str] = Field(default_factory=list, max_length=20)
    unresolved_gaps: list[AgentControlLoopEvidenceGap] = Field(default_factory=list, max_length=20)
    rounds_completed: int = Field(ge=0, le=24)
    external_action: Literal["none"] = "none"


class AgentControlLoopEvidenceAnchor(StrictModel):
    """A server-resolved location inside the exact bounded preview seen by the Analyst."""

    file_ref: str = Field(pattern=r"^forte-[0-9a-f]{16}$")
    role: AgentControlLoopEvidenceRole
    label: str = Field(min_length=1, max_length=120)
    locator_kind: AgentControlLoopEvidenceLocatorKind
    start: int = Field(ge=1)
    end: int = Field(ge=1)
    excerpt: str = Field(min_length=1, max_length=1_200)

    @field_validator("end")
    @classmethod
    def validate_end(cls, value: int, info) -> int:
        start = info.data.get("start")
        if isinstance(start, int) and value < start:
            raise ValueError("evidence anchor end must not precede start")
        return value


class AgentControlLoopFindingDecisionOption(StrictModel):
    option_id: AgentControlLoopDecisionOptionId
    label: str = Field(min_length=1, max_length=80)
    meaning: str = Field(min_length=1, max_length=400)
    agent_next_step: str = Field(min_length=1, max_length=500)
    next_instruction: str = Field(min_length=3, max_length=1_200)
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    required_file_refs: list[str] = Field(default_factory=list, max_length=20)
    estimated_additional_rounds: int = Field(default=1, ge=0, le=24)
    external_action: Literal["none"] = "none"


class AgentControlLoopFindingReview(StrictModel):
    """Model-proposed handling choices; choosing one remains an explicit user act."""

    requires_human_decision: bool
    question: str = Field(min_length=1, max_length=500)
    why_human: str = Field(min_length=1, max_length=500)
    options: list[AgentControlLoopFindingDecisionOption] = Field(default_factory=list, max_length=3)
    recommended_option_id: AgentControlLoopDecisionOptionId | None = None
    recommendation_reason: str = Field(min_length=1, max_length=500)
    after_confirmation: str = Field(min_length=1, max_length=500)


class AgentControlLoopArtifactFinding(StrictModel):
    finding_id: str | None = Field(default=None, pattern=r"^finding-[0-9a-f]{12}$")
    plan_unit_id: str | None = Field(default=None, min_length=1, max_length=120)
    affected_branch_ids: list[str] = Field(default_factory=list, max_length=12)
    title: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=2_000)
    fact_summary: str | None = Field(default=None, max_length=500)
    impact: str | None = Field(default=None, max_length=500)
    file_refs: list[str] = Field(min_length=1, max_length=20)
    evidence_anchors: list[AgentControlLoopEvidenceAnchor] = Field(
        default_factory=list, max_length=6
    )
    evidence_resolutions: list[AgentControlLoopEvidenceResolution] = Field(
        default_factory=list, max_length=6
    )
    review: AgentControlLoopFindingReview | None = None


class AgentControlLoopArtifactVersion(StrictModel):
    """A user-visible, read-only result version created by one completed loop round."""

    artifact_id: str = Field(pattern=r"^artifact-[0-9a-f]{12}$")
    version: int = Field(ge=1, le=24)
    title: str = Field(min_length=1, max_length=240)
    kind: Literal["evidence_brief"] = "evidence_brief"
    status: Literal["draft", "verified", "committed"]
    round_number: int = Field(default=1, ge=1, le=24)
    summary: str = Field(min_length=1, max_length=3_000)
    findings: list[AgentControlLoopArtifactFinding] = Field(default_factory=list, max_length=10)
    follow_ups: list[str] = Field(default_factory=list, max_length=4)
    evidence_gaps: list[AgentControlLoopEvidenceGap] = Field(default_factory=list, max_length=20)
    source_file_refs: list[str] = Field(default_factory=list, max_length=20)
    finding_count: int = Field(ge=0, le=10)
    parent_version: int | None = Field(default=None, ge=1, le=23)
    created_at: datetime
    review_required: Literal[True] = True
    external_action: Literal["none"] = "none"


class AgentControlLoopArtifactCheck(StrictModel):
    """One deterministic verifier assertion for a run-workspace file."""

    check_id: str = Field(pattern=r"^check-[a-z0-9-]{3,80}$")
    label: str = Field(min_length=1, max_length=240)
    passed: bool
    detail: str = Field(min_length=1, max_length=1_000)


class AgentControlLoopArtifactTestSuite(StrictModel):
    """One public suite from the manifest and actual collected test set."""

    suite_id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{2,79}$")
    label: str = Field(min_length=1, max_length=120)
    test_files: list[str] = Field(min_length=1, max_length=8)
    test_count: int = Field(ge=1, le=500)
    test_ids: list[str] = Field(min_length=1, max_length=500)


class AgentControlLoopArtifactSelfTest(StrictModel):
    """User-visible instructions for independently checking one artifact."""

    instruction: str = Field(min_length=3, max_length=2_000)
    expected_files: list[str] = Field(min_length=1, max_length=20)
    commands: list[str] = Field(min_length=1, max_length=10)
    expected_checks: list[str] = Field(min_length=1, max_length=30)
    failure_signals: list[str] = Field(min_length=1, max_length=12)
    test_manifest_file: str | None = Field(default=None, min_length=1, max_length=180)
    test_manifest_matches_collected: bool | None = None
    test_suites: list[AgentControlLoopArtifactTestSuite] = Field(
        default_factory=list, max_length=10
    )


class AgentControlLoopBusinessGate(StrictModel):
    """One server-derived business condition, separate from file verification."""

    gate_id: str = Field(pattern=r"^business-gate-[a-z0-9-]{3,80}$")
    label: str = Field(min_length=1, max_length=160)
    passed: bool
    numerator: float
    denominator: float = Field(gt=0)
    operator: Literal[">=", "==", "<="]
    threshold: float
    actual: float
    unit: Literal["percent", "count"]
    formula: str = Field(min_length=1, max_length=300)
    source_rule: str = Field(min_length=1, max_length=500)
    result: str = Field(min_length=1, max_length=500)


class AgentControlLoopBusinessMetric(StrictModel):
    """An informative metric that must not be projected as a business Gate."""

    metric_id: str = Field(pattern=r"^business-metric-[a-z0-9-]{3,80}$")
    label: str = Field(min_length=1, max_length=160)
    numerator: float
    denominator: float = Field(gt=0)
    value: float
    unit: Literal["percent", "count"]
    formula: str = Field(min_length=1, max_length=300)
    source_note: str = Field(min_length=1, max_length=500)


class AgentControlLoopBusinessRecord(StrictModel):
    """One auditable row in a server-derived business decision ledger."""

    record_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{1,39}$")
    title: str = Field(min_length=1, max_length=180)
    module: str = Field(min_length=1, max_length=180)
    priority: str = Field(min_length=1, max_length=40)
    owner: str = Field(min_length=1, max_length=120)
    configuration_status: str = Field(min_length=1, max_length=120)
    test_status: str = Field(min_length=1, max_length=120)
    test_reason: str = Field(min_length=1, max_length=160)
    total_cases: int = Field(ge=0, le=1_000_000)
    passed_cases: int = Field(ge=0, le=1_000_000)
    compatibility_issue_count: int = Field(ge=0, le=100)
    compatibility_issue_environments: list[str] = Field(default_factory=list, max_length=24)
    rules_hit: list[str] = Field(default_factory=list, max_length=12)
    base_risk_level: Literal["none", "minor", "major", "severe"]
    compatibility_risk_level: Literal["none", "minor", "severe"]
    final_risk_level: Literal["none", "minor", "major", "severe"]
    affected_gate_ids: list[str] = Field(default_factory=list, max_length=12)
    source_locations: list[str] = Field(min_length=1, max_length=8)
    remediation_action: str = Field(min_length=1, max_length=500)
    exit_condition: str = Field(min_length=1, max_length=500)


class AgentControlLoopLegalRuleAssessment(StrictModel):
    """One source-derived rule result for one fixed Legal-020 document."""

    assessment_id: str = Field(pattern=r"^legal-assessment-doc-[0-9]{2}-[rml][0-9]{2}$")
    rule_id: str = Field(pattern=r"^[RML][0-9]{2}$")
    rule_name: str = Field(min_length=1, max_length=180)
    rule_level: Literal["high", "medium", "low"]
    status: Literal["triggered", "not_triggered", "unverifiable"]
    source_locator: str = Field(min_length=1, max_length=180)
    excerpt: str = Field(min_length=1, max_length=1_000)
    fact: str = Field(min_length=1, max_length=800)
    judgment: str = Field(min_length=1, max_length=800)
    reason: str = Field(min_length=1, max_length=800)
    owner: str = Field(min_length=1, max_length=160)
    remediation_action: str = Field(min_length=1, max_length=800)
    exit_condition: str = Field(min_length=1, max_length=800)


class AgentControlLoopLegalDocumentReview(StrictModel):
    """All 21 rule assessments for one source document."""

    document_id: str = Field(pattern=r"^DOC-[0-9]{2}$")
    document_name: str = Field(min_length=1, max_length=180)
    source_file_ref: str = Field(min_length=1, max_length=120)
    highest_triggered_level: Literal["none", "low", "medium", "high"]
    triggered_count: int = Field(ge=0, le=21)
    unverifiable_count: int = Field(ge=0, le=21)
    signing_evidence_status: Literal["present", "absent", "unverifiable"]
    summary: str = Field(min_length=1, max_length=800)
    assessments: list[AgentControlLoopLegalRuleAssessment] = Field(min_length=21, max_length=21)


class AgentControlLoopLegalReviewOutcome(StrictModel):
    """Legal review projection kept separate from file-verifier status."""

    outcome_id: str = Field(pattern=r"^legal-review-outcome-[a-z0-9-]{3,80}$")
    status: Literal["cleared", "review_required", "invalid"]
    decision: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1_000)
    document_count: int = Field(ge=0, le=6)
    rule_count: int = Field(ge=0, le=21)
    assessment_count: int = Field(ge=0, le=126)
    high_risk_document_count: int = Field(ge=0, le=6)
    medium_risk_document_count: int = Field(ge=0, le=6)
    low_risk_document_count: int = Field(ge=0, le=6)
    no_trigger_document_count: int = Field(ge=0, le=6)
    critical_unverifiable_count: int = Field(ge=0, le=126)
    signing_evidence_count: int = Field(ge=0, le=6)
    human_review_required: bool
    signing_status: Literal["evidence_present", "evidence_incomplete", "invalid"]
    documents: list[AgentControlLoopLegalDocumentReview] = Field(default_factory=list, max_length=6)
    external_action: Literal["none"] = "none"


class AgentControlLoopCandidateConditionAssessment(StrictModel):
    """One source-derived JD condition result for one candidate and role."""

    assessment_id: str = Field(pattern=r"^candidate-assessment-[a-z0-9-]{6,100}$")
    role_id: Literal["merchant_bd", "text_evaluation"]
    candidate_id: str = Field(pattern=r"^CAND-[0-9]{2}$")
    candidate_name: str = Field(min_length=1, max_length=80)
    condition_id: str = Field(pattern=r"^[A-Z][A-Z0-9-]{2,79}$")
    condition_type: Literal[
        "responsibility",
        "default_threshold",
        "required",
        "preferred",
        "bonus",
    ]
    condition_label: str = Field(min_length=1, max_length=180)
    jd_source_file_ref: str = Field(min_length=1, max_length=120)
    jd_locator: str = Field(min_length=1, max_length=180)
    jd_excerpt: str = Field(min_length=1, max_length=1_000)
    resume_source_file_ref: str = Field(min_length=1, max_length=120)
    resume_locator: str = Field(min_length=1, max_length=180)
    resume_excerpt: str = Field(min_length=1, max_length=1_000)
    resume_evidence_present: bool
    status: Literal["met", "not_met", "unverifiable", "human_exception_required"]
    fact: str = Field(min_length=1, max_length=800)
    judgment: str = Field(min_length=1, max_length=800)
    reason: str = Field(min_length=1, max_length=800)
    owner: str = Field(min_length=1, max_length=160)
    review_action: str = Field(min_length=1, max_length=800)
    exit_condition: str = Field(min_length=1, max_length=800)


class AgentControlLoopCandidateRoleReview(StrictModel):
    """All parsed JD conditions for one candidate in one role."""

    review_id: str = Field(pattern=r"^candidate-review-[a-z0-9-]{6,80}$")
    role_id: Literal["merchant_bd", "text_evaluation"]
    role_name: str = Field(min_length=1, max_length=120)
    jd_source_file_ref: str = Field(min_length=1, max_length=120)
    candidate_id: str = Field(pattern=r"^CAND-[0-9]{2}$")
    candidate_name: str = Field(min_length=1, max_length=80)
    resume_source_file_ref: str = Field(min_length=1, max_length=120)
    recommendation: Literal[
        "recommended_for_human_review",
        "explicit_hard_gap",
        "insufficient_evidence",
        "exception_review_required",
    ]
    condition_count: int = Field(ge=1, le=40)
    met_count: int = Field(ge=0, le=40)
    not_met_count: int = Field(ge=0, le=40)
    unverifiable_count: int = Field(ge=0, le=40)
    human_exception_count: int = Field(ge=0, le=40)
    summary: str = Field(min_length=1, max_length=800)
    assessments: list[AgentControlLoopCandidateConditionAssessment] = Field(
        min_length=1, max_length=40
    )


class AgentControlLoopCandidateReviewOutcome(StrictModel):
    """Candidate-review projection kept separate from file-verifier status."""

    outcome_id: str = Field(pattern=r"^candidate-review-outcome-[a-z0-9-]{3,80}$")
    status: Literal["review_required", "invalid"]
    decision: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1_000)
    role_count: int = Field(ge=0, le=2)
    candidate_count: int = Field(ge=0, le=5)
    review_count: int = Field(ge=0, le=10)
    assessment_count: int = Field(ge=0, le=200)
    met_count: int = Field(ge=0, le=200)
    not_met_count: int = Field(ge=0, le=200)
    unverifiable_count: int = Field(ge=0, le=200)
    human_exception_count: int = Field(ge=0, le=200)
    recommended_for_human_review_count: int = Field(ge=0, le=10)
    explicit_hard_gap_count: int = Field(ge=0, le=10)
    insufficient_evidence_count: int = Field(ge=0, le=10)
    exception_review_required_count: int = Field(ge=0, le=10)
    human_review_required: Literal[True] = True
    fairness_evaluated: Literal[False] = False
    reviews: list[AgentControlLoopCandidateRoleReview] = Field(default_factory=list, max_length=10)
    external_action: Literal["none"] = "none"


class AgentControlLoopCustomerSegmentationRule(StrictModel):
    """One source-derived Sales-020 cleaning, classification, or report rule."""

    rule_id: str = Field(pattern=r"^SEG-[A-Z0-9-]{3,80}$")
    category: Literal["cleaning", "classification", "priority", "exclusion", "report"]
    source_file_ref: str = Field(min_length=1, max_length=120)
    locator: str = Field(min_length=1, max_length=180)
    excerpt: str = Field(min_length=1, max_length=1_000)
    parameters: list[str] = Field(default_factory=list, max_length=16)


class AgentControlLoopCustomerSampleDecision(StrictModel):
    """One raw survey row, its cleaning trace, and its source-derived label decision."""

    sample_id: str = Field(min_length=1, max_length=80)
    source_file_ref: str = Field(min_length=1, max_length=120)
    source_row: int = Field(ge=2, le=1_000_000)
    source_locator: str = Field(min_length=1, max_length=180)
    industry: str = Field(min_length=1, max_length=180)
    company_size: str = Field(min_length=1, max_length=120)
    respondent_role: str = Field(min_length=1, max_length=180)
    raw_scores: dict[str, str] = Field(min_length=4, max_length=4)
    cleaned_scores: dict[str, int] = Field(min_length=4, max_length=4)
    transformations: list[str] = Field(default_factory=list, max_length=12)
    matched_profiles: list[str] = Field(default_factory=list, max_length=8)
    priority_applied: bool
    final_label: str | None = Field(default=None, min_length=1, max_length=80)
    exclusion_reason: Literal["exact_duplicate", "unclassified"] | None = None
    duplicate_of: str | None = Field(default=None, min_length=1, max_length=80)
    rule_refs: list[str] = Field(min_length=1, max_length=24)


class AgentControlLoopCustomerSegmentationParameters(StrictModel):
    """Public parameters parsed from the approved Sales-020 Markdown."""

    parsing_encoding: Literal["utf-8-sig", "utf-8", "gb18030"]
    missing_score_default: int = Field(ge=0, le=10)
    chinese_number_domain: str = Field(min_length=1, max_length=120)
    profile_thresholds: dict[str, int] = Field(min_length=3, max_length=3)
    profile_priority: list[str] = Field(min_length=3, max_length=3)
    duplicate_policy: Literal["exact_non_id_payload"] = "exact_non_id_payload"


class AgentControlLoopCustomerSegmentationOutcome(StrictModel):
    """Customer-segmentation facts kept separate from sales approval and CRM actions."""

    outcome_id: str = Field(pattern=r"^customer-segmentation-outcome-[a-z0-9-]{3,80}$")
    status: Literal["sales_review_required", "invalid"]
    decision: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=1_000)
    source_row_count: int = Field(ge=0, le=20_000)
    unique_payload_count: int = Field(ge=0, le=20_000)
    duplicate_count: int = Field(ge=0, le=20_000)
    classified_count: int = Field(ge=0, le=20_000)
    unclassified_count: int = Field(ge=0, le=20_000)
    excluded_count: int = Field(ge=0, le=20_000)
    profile_counts: dict[str, int] = Field(default_factory=dict, max_length=8)
    parameters: AgentControlLoopCustomerSegmentationParameters
    rules: list[AgentControlLoopCustomerSegmentationRule] = Field(min_length=1, max_length=40)
    samples: list[AgentControlLoopCustomerSampleDecision] = Field(
        min_length=1, max_length=20_000
    )
    duplicate_policy_assumption: Literal["exact_non_id_payload"] = "exact_non_id_payload"
    policy_assumption_review_required: Literal[True] = True
    priority_witness_count: int = Field(ge=0, le=20_000)
    strategy_evidence_status: Literal["no_approved_strategy_source"] = (
        "no_approved_strategy_source"
    )
    human_review_required: Literal[True] = True
    original_inputs_modified: Literal[False] = False
    external_action: Literal["none"] = "none"

    @model_validator(mode="after")
    def validate_customer_counts(self) -> "AgentControlLoopCustomerSegmentationOutcome":
        if self.unique_payload_count + self.duplicate_count != self.source_row_count:
            raise ValueError("unique payloads plus duplicates must equal source rows")
        if self.classified_count + self.unclassified_count != self.unique_payload_count:
            raise ValueError("classified plus unclassified must equal unique payloads")
        if self.unclassified_count + self.duplicate_count != self.excluded_count:
            raise ValueError("unclassified plus duplicates must equal excluded rows")
        if sum(self.profile_counts.values()) != self.classified_count:
            raise ValueError("profile counts must equal classified_count")
        if len(self.samples) != self.source_row_count:
            raise ValueError("sample decisions must cover every source row")
        if sum(bool(item.duplicate_of) for item in self.samples) != self.duplicate_count:
            raise ValueError("duplicate sample projection must equal duplicate_count")
        if sum(item.priority_applied for item in self.samples) != self.priority_witness_count:
            raise ValueError("priority witness projection must equal priority_witness_count")
        return self


class AgentControlLoopSREObservation(StrictModel):
    """One source-bound fact extracted from the approved SRE-010 log."""

    observation_id: str = Field(pattern=r"^sre-observation-[a-z0-9-]{3,100}$")
    category: Literal[
        "metadata",
        "cluster",
        "node",
        "metric",
        "gc",
        "slow_query",
        "queue",
        "health",
        "thread_pool",
        "shard",
        "query",
        "recovery",
        "side_event",
        "allocation",
        "unclassified",
    ]
    statement: str = Field(min_length=1, max_length=1_000)
    source_file_ref: str = Field(min_length=1, max_length=120)
    locator: str = Field(min_length=1, max_length=180)
    excerpt: str = Field(min_length=1, max_length=2_000)
    fields: dict[str, str] = Field(default_factory=dict, max_length=30)
    status: Literal["observed", "unclassified"] = "observed"


class AgentControlLoopSRESourceConflict(StrictModel):
    """Two or more incompatible source observations that need SRE review."""

    conflict_id: str = Field(pattern=r"^sre-conflict-[a-z0-9-]{3,100}$")
    title: str = Field(min_length=1, max_length=240)
    statement: str = Field(min_length=1, max_length=1_000)
    side_a_observation_ids: list[str] = Field(min_length=1, max_length=100)
    side_b_observation_ids: list[str] = Field(min_length=1, max_length=100)
    locators: list[str] = Field(min_length=2, max_length=30)
    impact: str = Field(min_length=1, max_length=800)
    status: Literal["open", "resolved"]


class AgentControlLoopSREHypothesis(StrictModel):
    """A bounded diagnosis hypothesis, kept separate from observed facts."""

    hypothesis_id: str = Field(pattern=r"^sre-hypothesis-[a-z0-9-]{3,100}$")
    statement: str = Field(min_length=1, max_length=1_200)
    confidence: Literal["low", "medium", "high"]
    supporting_observation_ids: list[str] = Field(default_factory=list, max_length=100)
    supporting_locators: list[str] = Field(default_factory=list, max_length=100)
    counter_evidence_ids: list[str] = Field(default_factory=list, max_length=100)
    counter_evidence_locators: list[str] = Field(default_factory=list, max_length=100)
    limitations: list[str] = Field(min_length=1, max_length=20)


class AgentControlLoopSREActionProposal(StrictModel):
    """A review-only SRE proposal. It is never an execution receipt."""

    proposal_id: str = Field(pattern=r"^sre-proposal-[a-z0-9-]{3,100}$")
    kind: Literal["read_only_preflight", "write_change", "business_mitigation"]
    title: str = Field(min_length=1, max_length=240)
    risk_level: Literal["low", "medium", "high"]
    command_template: str | None = Field(default=None, min_length=1, max_length=2_000)
    action_text: str | None = Field(default=None, min_length=1, max_length=1_000)
    target_status: Literal["unresolved", "not_applicable"]
    target_rationale: str = Field(min_length=1, max_length=800)
    preconditions: list[str] = Field(min_length=1, max_length=20)
    rollback: str = Field(min_length=1, max_length=1_000)
    verify_after: list[str] = Field(min_length=1, max_length=20)
    official_reference: str | None = Field(default=None, min_length=1, max_length=500)
    approval_required: Literal[True] = True
    executed: Literal[False] = False
    source_observation_ids: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_proposal_body(self) -> "AgentControlLoopSREActionProposal":
        if bool(self.command_template) == bool(self.action_text):
            raise ValueError("SRE proposal must contain exactly one command_template or action_text")
        if self.kind == "business_mitigation" and self.target_status != "not_applicable":
            raise ValueError("business mitigation does not use an Elasticsearch endpoint")
        if self.kind != "business_mitigation" and self.target_status != "unresolved":
            raise ValueError("Elasticsearch proposal target must remain unresolved")
        return self


class AgentControlLoopSREDiagnosisOutcome(StrictModel):
    """Source-derived SRE facts kept separate from diagnosis approval and execution."""

    outcome_id: str = Field(pattern=r"^sre-diagnosis-outcome-[a-z0-9-]{3,80}$")
    status: Literal["incident_review_required", "invalid"]
    decision: str = Field(min_length=1, max_length=700)
    summary: str = Field(min_length=1, max_length=1_500)
    source_line_count: int = Field(ge=1, le=100_000)
    cluster_facts: dict[str, Any] = Field(default_factory=dict, max_length=30)
    node_facts: dict[str, Any] = Field(default_factory=dict, max_length=30)
    metric_facts: dict[str, Any] = Field(default_factory=dict, max_length=60)
    timeline: list[str] = Field(default_factory=list, max_length=200)
    observation_count: int = Field(ge=1, le=1_000)
    conflict_count: int = Field(ge=0, le=100)
    hypothesis_count: int = Field(ge=0, le=50)
    proposal_count: int = Field(ge=0, le=100)
    business_mitigation_count: int = Field(ge=0, le=50)
    unclassified_count: int = Field(ge=0, le=1_000)
    observations: list[AgentControlLoopSREObservation] = Field(min_length=1, max_length=1_000)
    source_conflicts: list[AgentControlLoopSRESourceConflict] = Field(
        default_factory=list, max_length=100
    )
    hypotheses: list[AgentControlLoopSREHypothesis] = Field(default_factory=list, max_length=50)
    action_proposals: list[AgentControlLoopSREActionProposal] = Field(
        default_factory=list, max_length=100
    )
    business_mitigations: list[AgentControlLoopSREActionProposal] = Field(
        default_factory=list, max_length=50
    )
    resolved_target_count: Literal[0] = 0
    human_review_required: Literal[True] = True
    original_inputs_modified: Literal[False] = False
    external_action: Literal["none"] = "none"

    @model_validator(mode="after")
    def validate_sre_projection(self) -> "AgentControlLoopSREDiagnosisOutcome":
        if self.observation_count != len(self.observations):
            raise ValueError("SRE observation_count must equal observations length")
        if self.conflict_count != len(self.source_conflicts):
            raise ValueError("SRE conflict_count must equal source_conflicts length")
        if self.hypothesis_count != len(self.hypotheses):
            raise ValueError("SRE hypothesis_count must equal hypotheses length")
        if self.proposal_count != len(self.action_proposals):
            raise ValueError("SRE proposal_count must equal action_proposals length")
        if self.business_mitigation_count != len(self.business_mitigations):
            raise ValueError("SRE business_mitigation_count must equal business_mitigations length")
        if self.unclassified_count != sum(
            item.status == "unclassified" for item in self.observations
        ):
            raise ValueError("SRE unclassified_count must equal unclassified observations")
        observation_ids = [item.observation_id for item in self.observations]
        if len(observation_ids) != len(set(observation_ids)):
            raise ValueError("SRE observation ids must be unique")
        known = set(observation_ids)
        for hypothesis in self.hypotheses:
            if not set(hypothesis.supporting_observation_ids).issubset(known):
                raise ValueError("SRE hypothesis support must reference known observations")
            if not set(hypothesis.counter_evidence_ids).issubset(known):
                raise ValueError("SRE hypothesis counter evidence must reference known observations")
        for proposal in (*self.action_proposals, *self.business_mitigations):
            if not set(proposal.source_observation_ids).issubset(known):
                raise ValueError("SRE proposal must reference known observations")
        return self


class AgentControlLoopFinanceCandidateSource(StrictModel):
    """One period-specific source row for a cross-period finance candidate."""

    period_id: Literal["2025_h1", "2025_h2", "2026"]
    period_label: str = Field(min_length=1, max_length=80)
    source_file_ref: str = Field(min_length=1, max_length=120)
    file_name: str = Field(min_length=1, max_length=180)
    sheet_name: str = Field(min_length=1, max_length=120)
    row_number: int = Field(ge=2, le=1_000_000)
    locator: str = Field(min_length=1, max_length=180)
    direction: Literal["借"] = "借"
    ending_balance: str = Field(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")


class AgentControlLoopFinanceCandidate(StrictModel):
    """A source-derived cross-period risk candidate, not an accounting decision."""

    candidate_id: str = Field(pattern=r"^finance-candidate-[0-9a-f]{12}$")
    key: str = Field(min_length=1, max_length=360)
    subject: str = Field(min_length=1, max_length=180)
    customer: str = Field(min_length=1, max_length=180)
    sources: list[AgentControlLoopFinanceCandidateSource] = Field(min_length=3, max_length=3)
    review_action: str = Field(min_length=1, max_length=800)
    exit_condition: str = Field(min_length=1, max_length=800)


class AgentControlLoopFinanceReviewOutcome(StrictModel):
    """Finance review projection kept separate from deterministic file verification."""

    outcome_id: str = Field(pattern=r"^finance-review-outcome-[a-z0-9-]{3,80}$")
    status: Literal["review_required", "invalid"]
    decision: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=1_000)
    period_ids: list[Literal["2025_h1", "2025_h2", "2026"]] = Field(
        min_length=3, max_length=3
    )
    unpaid_count: int = Field(ge=0, le=1_000_000)
    unpaid_total: str = Field(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")
    unreceived_count: int = Field(ge=0, le=1_000_000)
    unreceived_total: str = Field(pattern=r"^(0|[1-9][0-9]*)(\.[0-9]+)?$")
    candidate_count: int = Field(ge=0, le=1_000)
    candidates: list[AgentControlLoopFinanceCandidate] = Field(
        default_factory=list, max_length=1_000
    )
    method: str = Field(min_length=1, max_length=1_000)
    limitations: list[str] = Field(min_length=1, max_length=12)
    human_review_required: Literal[True] = True
    original_inputs_modified: Literal[False] = False
    external_action: Literal["none"] = "none"

    @field_validator("period_ids")
    @classmethod
    def validate_period_order(cls, value: list[str]) -> list[str]:
        if value != ["2025_h1", "2025_h2", "2026"]:
            raise ValueError("finance review periods must contain the three fixed periods in order")
        return value

    @field_validator("candidates")
    @classmethod
    def validate_candidate_projection(
        cls,
        value: list[AgentControlLoopFinanceCandidate],
        info: ValidationInfo,
    ) -> list[AgentControlLoopFinanceCandidate]:
        if len(value) != info.data.get("candidate_count"):
            raise ValueError("finance candidate_count must equal the candidate list length")
        candidate_ids = [item.candidate_id for item in value]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("finance candidate ids must be unique")
        expected_periods = ["2025_h1", "2025_h2", "2026"]
        for candidate in value:
            if [source.period_id for source in candidate.sources] != expected_periods:
                raise ValueError("each finance candidate must bind the three fixed periods in order")
        return value


class AgentControlLoopOutboundRuleParameter(StrictModel):
    """One public, source-derived parameter used by the outbound-flow design."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    value: str = Field(min_length=1, max_length=180)
    unit: str | None = Field(default=None, min_length=1, max_length=40)


class AgentControlLoopOutboundRule(StrictModel):
    """One normative requirement extracted from the approved Operations-008 Markdown."""

    rule_id: str = Field(pattern=r"^OUT-[A-Z][A-Z0-9_]*-[0-9]{2}$")
    group: Literal[
        "TIME",
        "FREQ",
        "RECORD",
        "IDENTITY",
        "THIRD_PARTY",
        "PROHIBIT",
        "CONNECT",
        "PTP",
        "SOFT",
        "HARD",
        "DISPUTE",
        "INVALID",
        "TERMINAL",
        "PAYMENT",
        "REDIAL",
    ]
    source_file_ref: str = Field(min_length=1, max_length=120)
    locator: str = Field(min_length=1, max_length=180)
    excerpt: str = Field(min_length=1, max_length=1_000)
    parameters: list[AgentControlLoopOutboundRuleParameter] = Field(
        default_factory=list, max_length=12
    )
    expected_relation: str = Field(min_length=1, max_length=300)
    expected_action: str = Field(min_length=1, max_length=500)
    coverage_state: Literal["covered", "unsupported", "conflict"]
    mapped_node_ids: list[str] = Field(default_factory=list, max_length=20)
    mapped_edge_ids: list[str] = Field(default_factory=list, max_length=20)
    mapped_guard_ids: list[str] = Field(default_factory=list, max_length=20)
    mapped_terminal_ids: list[str] = Field(default_factory=list, max_length=12)


class AgentControlLoopOutboundNode(StrictModel):
    node_id: str = Field(pattern=r"^out-node-[a-z0-9-]{2,100}$")
    label: str = Field(min_length=1, max_length=240)
    kind: Literal["start", "gate", "decision", "action", "terminal"]
    source_rule_ids: list[str] = Field(default_factory=list, max_length=30)
    future_action: bool = False


class AgentControlLoopOutboundEdge(StrictModel):
    edge_id: str = Field(pattern=r"^out-edge-[a-z0-9-]{2,100}$")
    from_node_id: str = Field(pattern=r"^out-node-[a-z0-9-]{2,100}$")
    to_node_id: str = Field(pattern=r"^out-node-[a-z0-9-]{2,100}$")
    label: str = Field(min_length=1, max_length=240)
    guard_ids: list[str] = Field(default_factory=list, max_length=12)
    source_rule_ids: list[str] = Field(default_factory=list, max_length=30)
    future_action: bool = False


class AgentControlLoopOutboundGuard(StrictModel):
    guard_id: str = Field(pattern=r"^out-guard-[a-z0-9-]{2,100}$")
    label: str = Field(min_length=1, max_length=300)
    parameters: list[AgentControlLoopOutboundRuleParameter] = Field(
        default_factory=list, max_length=12
    )
    source_rule_ids: list[str] = Field(min_length=1, max_length=30)


class AgentControlLoopOutboundTerminal(StrictModel):
    terminal_id: str = Field(pattern=r"^out-terminal-[a-z0-9-]{2,100}$")
    node_id: str = Field(pattern=r"^out-node-[a-z0-9-]{2,100}$")
    label: str = Field(min_length=1, max_length=180)
    source_rule_ids: list[str] = Field(min_length=1, max_length=20)
    source_listed: bool


class AgentControlLoopOutboundGraphIntegrity(StrictModel):
    unique_start: bool
    unique_ids: bool
    no_dangling_edges: bool
    all_nodes_reachable: bool
    all_terminals_reachable: bool
    every_nonterminal_has_outgoing: bool
    every_node_can_reach_terminal: bool
    critical_order_valid: bool
    third_party_boundary_valid: bool
    all_rules_mapped: bool


class AgentControlLoopOutboundFlowOutcome(StrictModel):
    """Source-derived flow coverage, kept separate from approval and execution."""

    outcome_id: str = Field(pattern=r"^outbound-flow-outcome-[a-z0-9-]{3,80}$")
    status: Literal["approval_required", "invalid"]
    decision: str = Field(min_length=1, max_length=500)
    summary: str = Field(min_length=1, max_length=1_000)
    source_rule_group_count: int = Field(ge=0, le=30)
    atomic_requirement_count: int = Field(ge=0, le=100)
    covered_count: int = Field(ge=0, le=100)
    unsupported_count: int = Field(ge=0, le=100)
    conflict_count: int = Field(ge=0, le=100)
    node_count: int = Field(ge=0, le=100)
    edge_count: int = Field(ge=0, le=150)
    guard_count: int = Field(ge=0, le=50)
    terminal_count: int = Field(ge=0, le=20)
    reachable_terminal_count: int = Field(ge=0, le=20)
    parameters: list[AgentControlLoopOutboundRuleParameter] = Field(
        default_factory=list, max_length=30
    )
    rules: list[AgentControlLoopOutboundRule] = Field(default_factory=list, max_length=100)
    nodes: list[AgentControlLoopOutboundNode] = Field(default_factory=list, max_length=100)
    edges: list[AgentControlLoopOutboundEdge] = Field(default_factory=list, max_length=150)
    guards: list[AgentControlLoopOutboundGuard] = Field(default_factory=list, max_length=50)
    terminals: list[AgentControlLoopOutboundTerminal] = Field(default_factory=list, max_length=20)
    graph_integrity: AgentControlLoopOutboundGraphIntegrity
    human_approval_required: Literal[True] = True
    legal_opinion: Literal[False] = False
    original_inputs_modified: Literal[False] = False
    external_action: Literal["none"] = "none"

    @model_validator(mode="after")
    def validate_projection_counts(self) -> "AgentControlLoopOutboundFlowOutcome":
        if self.atomic_requirement_count != len(self.rules):
            raise ValueError("outbound atomic_requirement_count must equal rules length")
        if self.source_rule_group_count != len({rule.group for rule in self.rules}):
            raise ValueError("outbound source_rule_group_count must equal unique groups")
        if self.covered_count + self.unsupported_count + self.conflict_count != len(self.rules):
            raise ValueError("outbound coverage counts must equal rules length")
        if self.node_count != len(self.nodes) or self.edge_count != len(self.edges):
            raise ValueError("outbound graph counts must equal node and edge list lengths")
        if self.guard_count != len(self.guards) or self.terminal_count != len(self.terminals):
            raise ValueError("outbound graph counts must equal guard and terminal list lengths")
        if self.reachable_terminal_count > self.terminal_count:
            raise ValueError("outbound reachable terminals cannot exceed terminal count")
        return self


class AgentControlLoopBusinessGateOutcome(StrictModel):
    """A business decision projected independently from deterministic checks."""

    outcome_id: str = Field(pattern=r"^business-outcome-[a-z0-9-]{3,80}$")
    outcome_kind: Literal["release_readiness", "legal_delegation_review"] = "release_readiness"
    status: Literal["passed", "failed", "invalid"]
    decision: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=800)
    total_gate_count: int = Field(ge=0, le=30)
    failed_gate_count: int = Field(ge=0, le=30)
    gates: list[AgentControlLoopBusinessGate] = Field(default_factory=list, max_length=30)
    auxiliary_metrics: list[AgentControlLoopBusinessMetric] = Field(
        default_factory=list, max_length=30
    )
    records: list[AgentControlLoopBusinessRecord] = Field(default_factory=list, max_length=100)
    external_action: Literal["none"] = "none"


class AgentControlLoopWorkspaceArtifact(StrictModel):
    """A real file written only inside an isolated run workspace."""

    artifact_id: str = Field(pattern=r"^workspace-artifact-[0-9a-f]{12}$")
    capability_id: str = Field(pattern=r"^office-[a-z0-9-]{3,80}$")
    scenario_id: str = Field(pattern=r"^TC-[0-9]{2}$")
    title: str = Field(min_length=1, max_length=240)
    file_name: str = Field(min_length=1, max_length=180)
    media_type: Literal[
        "text/csv",
        "text/markdown",
        "application/zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    size: int = Field(gt=0, le=10 * 1024 * 1024)
    version: int = Field(default=1, ge=1, le=24)
    round_number: int = Field(ge=1, le=24)
    source_file_refs: list[str] = Field(min_length=1, max_length=96)
    validator_id: str = Field(pattern=r"^validator-[a-z0-9-]{3,100}$")
    verifier_status: Literal["passed", "failed"]
    checks: list[AgentControlLoopArtifactCheck] = Field(min_length=1, max_length=30)
    summary: str = Field(min_length=1, max_length=1_000)
    covered_period: str | None = Field(default=None, min_length=1, max_length=300)
    statistic_basis: str | None = Field(default=None, min_length=1, max_length=800)
    purpose: str | None = Field(default=None, min_length=1, max_length=500)
    record_count: int | None = Field(default=None, ge=0, le=1_000_000)
    deliverable_type: str | None = Field(default=None, min_length=1, max_length=120)
    key_outputs: list[str] = Field(default_factory=list, max_length=12)
    key_outputs_label: str | None = Field(default=None, min_length=1, max_length=80)
    review_guidance: str | None = Field(default=None, min_length=1, max_length=500)
    execution_summary: str | None = Field(default=None, min_length=1, max_length=500)
    self_test: AgentControlLoopArtifactSelfTest | None = None
    business_gate_outcome: AgentControlLoopBusinessGateOutcome | None = None
    legal_review_outcome: AgentControlLoopLegalReviewOutcome | None = None
    candidate_review_outcome: AgentControlLoopCandidateReviewOutcome | None = None
    finance_review_outcome: AgentControlLoopFinanceReviewOutcome | None = None
    outbound_flow_outcome: AgentControlLoopOutboundFlowOutcome | None = None
    customer_segmentation_outcome: AgentControlLoopCustomerSegmentationOutcome | None = None
    sre_diagnosis_outcome: AgentControlLoopSREDiagnosisOutcome | None = None
    download_path: str = Field(min_length=1, max_length=300)
    created_at: datetime
    original_inputs_modified: Literal[False] = False
    review_required: Literal[True] = True
    external_action: Literal["none"] = "none"


class AgentControlLoopEffectReceipt(StrictModel):
    """Auditable state-action-observation-cost-result receipt for one office tool."""

    receipt_id: str = Field(pattern=r"^effect-receipt-[0-9a-f]{12}$")
    capability_id: str = Field(pattern=r"^office-[a-z0-9-]{3,80}$")
    scenario_id: str = Field(pattern=r"^TC-[0-9]{2}$")
    status: Literal[
        "passed",
        "failed",
        "blocked_external_boundary",
        "unsupported_local_capability",
    ]
    state: str = Field(min_length=1, max_length=500)
    action: str = Field(min_length=1, max_length=500)
    observation: str = Field(min_length=1, max_length=1_000)
    cost: str = Field(min_length=1, max_length=500)
    result: str = Field(min_length=1, max_length=1_000)
    source_file_refs: list[str] = Field(default_factory=list, max_length=96)
    artifact_ids: list[str] = Field(default_factory=list, max_length=8)
    prohibited_side_effects: list[str] = Field(default_factory=list, max_length=12)
    business_gate_outcome: AgentControlLoopBusinessGateOutcome | None = None
    legal_review_outcome: AgentControlLoopLegalReviewOutcome | None = None
    candidate_review_outcome: AgentControlLoopCandidateReviewOutcome | None = None
    finance_review_outcome: AgentControlLoopFinanceReviewOutcome | None = None
    outbound_flow_outcome: AgentControlLoopOutboundFlowOutcome | None = None
    customer_segmentation_outcome: AgentControlLoopCustomerSegmentationOutcome | None = None
    sre_diagnosis_outcome: AgentControlLoopSREDiagnosisOutcome | None = None
    created_at: datetime
    external_action: Literal["none"] = "none"


class AgentControlLoopCommit(StrictModel):
    """Logical commit of the final verified brief; it is not an external action."""

    commit_id: str = Field(pattern=r"^commit-[0-9a-f]{12}$")
    artifact_id: str = Field(pattern=r"^artifact-[0-9a-f]{12}$")
    artifact_version: int = Field(ge=1, le=24)
    operation: Literal["commit", "rollback"] = "commit"
    parent_commit_id: str | None = Field(default=None, pattern=r"^commit-[0-9a-f]{12}$")
    summary: str = Field(min_length=1, max_length=1_000)
    committed_at: datetime
    external_action: Literal["none"] = "none"


class AgentControlLoopControlRequest(StrictModel):
    command: AgentControlLoopCommand
    idempotency_key: str = Field(min_length=8, max_length=160)
    expected_version: int = Field(ge=1)
    instruction: str | None = Field(default=None, max_length=2_000)
    branch_id: str | None = Field(default=None, pattern=r"^branch-[0-9a-f]{12}$")
    artifact_version: int | None = Field(default=None, ge=1, le=24)
    decision_action: AgentControlLoopDecisionAction | None = None
    decision_request_id: str | None = Field(
        default=None, pattern=r"^decision-request-[0-9a-f]{12}$"
    )
    finding_id: str | None = Field(default=None, pattern=r"^finding-[0-9a-f]{12}$")
    resolution_id: str | None = Field(default=None, pattern=r"^resolution-[0-9a-f]{12}$")
    selected_option_id: AgentControlLoopDecisionOptionId | None = None
    selected_candidate_id: str | None = Field(default=None, pattern=r"^candidate-[0-9a-f]{12}$")
    candidate_digest: str | None = Field(default=None, max_length=128)
    source_revision: str | None = Field(default=None, max_length=128)
    feedback: str | None = Field(default=None, max_length=2_000)

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("steer instruction is too short")
        return normalized

    @field_validator("idempotency_key")
    @classmethod
    def validate_control_key(cls, value: str) -> str:
        if any(ord(character) < 32 for character in value):
            raise ValueError("idempotency_key contains invalid content")
        return value

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        if any(ord(character) < 32 and character not in "\n\t" for character in normalized):
            raise ValueError("decision feedback contains invalid content")
        return normalized


# Compatibility aliases for modules that import the former scenario contracts.
# They do not reintroduce the retired scenario API.
BenchmarkContentNature = Literal["public_benchmark_demo_inputs"]
BenchmarkTaskEntry = BenchmarkPublicSuiteTask
BenchmarkWorkProfile = dict
BenchmarkPublicScenario = BenchmarkPublicWorkspace
BenchmarkTaskTopology = Literal["single_task", "multi_task"]
BenchmarkOrchestrationMode = Literal["bounded_loop", "adaptive_swarm"]
BenchmarkControlRequirement = Literal["evidence_gate", "human_gate", "risk_gate"]
