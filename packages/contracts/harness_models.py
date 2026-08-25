"""Contracts for the pinned FORTE public office workspace.

The public manifest is the server-owned allowlist. The foreground only receives
stable references and business-facing folder/file metadata; raw paths, hashes,
benchmark prompts, rubrics and solutions stay behind the catalog boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from .models import StrictModel


BenchmarkFileRole = Literal["input", "task_instruction"]
BenchmarkAvailability = Literal[
    "local_input_bundle",
    "task_only_requires_external_system",
]
BenchmarkPreviewKind = Literal["table", "document", "pdf", "text", "unavailable"]
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
AgentControlLoopCommand = Literal["pause", "resume", "steer", "stop"]


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

    max_rounds: int = Field(default=3, ge=1, le=3)
    max_files_per_round: int = Field(default=4, ge=1, le=8)
    max_model_calls: int = Field(default=6, ge=2, le=6)
    deadline_seconds: int = Field(default=120, ge=20, le=300)


class AgentControlLoopContract(StrictModel):
    contract_version: Literal["agent-control-loop.v1"] = "agent-control-loop.v1"
    goal: str = Field(min_length=3, max_length=2_000)
    allowed_file_refs: list[str] = Field(default_factory=list, max_length=20)
    completion_criteria: list[str] = Field(min_length=1, max_length=6)
    max_rounds: int = Field(ge=1, le=3)
    max_files_per_round: int = Field(ge=1, le=8)
    max_model_calls: int = Field(ge=2, le=6)
    deadline_seconds: int = Field(ge=20, le=300)
    external_action: Literal["none"] = "none"


class AgentControlLoopBudget(StrictModel):
    max_rounds: int = Field(ge=1, le=3)
    max_files_per_round: int = Field(ge=1, le=8)
    max_model_calls: int = Field(ge=2, le=6)
    deadline_seconds: int = Field(ge=20, le=300)
    rounds_used: int = Field(default=0, ge=0, le=3)
    files_verified: int = Field(default=0, ge=0, le=20)
    model_calls_used: int = Field(default=0, ge=0, le=6)
    elapsed_ms: int = Field(default=0, ge=0)
    stop_reason: str | None = Field(default=None, max_length=240)


class AgentControlLoopEvidenceGap(StrictModel):
    gap_id: str = Field(pattern=r"^gap-[0-9a-f]{12}$")
    label: str = Field(min_length=1, max_length=240)
    detail: str = Field(min_length=1, max_length=1_000)
    candidate_file_refs: list[str] = Field(default_factory=list, max_length=20)


class AgentControlLoopNextStep(StrictModel):
    decision: AgentControlLoopGateDecision
    reason: str = Field(min_length=1, max_length=1_000)
    next_question: str | None = Field(default=None, max_length=2_000)
    candidate_file_refs: list[str] = Field(default_factory=list, max_length=20)


class AgentControlLoopRound(StrictModel):
    round_number: int = Field(ge=1, le=3)
    status: Literal["running", "completed", "stopped", "failed"]
    phase: AgentControlLoopPhase
    question: str = Field(min_length=3, max_length=2_000)
    steer_instruction: str | None = Field(default=None, max_length=2_000)
    input_file_refs: list[str] = Field(default_factory=list, max_length=8)
    plan: dict[str, Any] | None = None
    model_receipt: dict[str, Any] | None = None
    result: dict[str, Any] | None = None
    analysis_receipt: dict[str, Any] | None = None
    verified_file_refs: list[str] = Field(default_factory=list, max_length=20)
    evidence_gaps: list[AgentControlLoopEvidenceGap] = Field(
        default_factory=list, max_length=20
    )
    next_step: AgentControlLoopNextStep | None = None
    started_at: datetime
    completed_at: datetime | None = None


class AgentControlLoopControlEvent(StrictModel):
    control_id: str = Field(pattern=r"^control-[0-9a-f]{12}$")
    command: AgentControlLoopCommand
    instruction: str | None = Field(default=None, max_length=2_000)
    accepted_at: datetime
    accepted_task_version: int = Field(ge=1)
    applied_task_version: int | None = Field(default=None, ge=1)
    status: Literal["accepted", "applied", "rejected"]


class AgentControlLoopBrief(StrictModel):
    outcome: Literal["completed", "bounded", "user_stopped"]
    summary: str = Field(min_length=1, max_length=3_000)
    verified_file_refs: list[str] = Field(default_factory=list, max_length=20)
    unresolved_gaps: list[AgentControlLoopEvidenceGap] = Field(
        default_factory=list, max_length=20
    )
    rounds_completed: int = Field(ge=0, le=3)
    external_action: Literal["none"] = "none"


class AgentControlLoopControlRequest(StrictModel):
    command: AgentControlLoopCommand
    idempotency_key: str = Field(min_length=8, max_length=160)
    expected_version: int = Field(ge=1)
    instruction: str | None = Field(default=None, max_length=2_000)

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


# Compatibility aliases for modules that import the former scenario contracts.
# They do not reintroduce the retired scenario API.
BenchmarkContentNature = Literal["public_benchmark_demo_inputs"]
BenchmarkTaskEntry = BenchmarkPublicSuiteTask
BenchmarkWorkProfile = dict
BenchmarkPublicScenario = BenchmarkPublicWorkspace
BenchmarkTaskTopology = Literal["single_task", "multi_task"]
BenchmarkOrchestrationMode = Literal["bounded_loop", "adaptive_swarm"]
BenchmarkControlRequirement = Literal["evidence_gate", "human_gate", "risk_gate"]
