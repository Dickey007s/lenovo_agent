from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, model_validator

from .models import StrictModel


ExecutionMode = Literal[
    "tool_call",
    "single_agent",
    "fixed_workflow",
    "adaptive_swarm",
]
AdmissionStatus = Literal["recommended", "route_selected"]
RouteSelectionSource = Literal["admission", "user_override"]
OverrideScope = Literal["this_run"]
ExecutionStatus = Literal[
    "not_started",
    "queued",
    "running",
    "verifying",
    "completed",
    "failed",
    "cancelled",
]
RouteImpactKind = Literal["change", "preserve", "no_external_action"]
RouteImpactAspect = Literal[
    "route_decision",
    "work_allocation",
    "coordination",
    "human_control",
    "policy_forecast",
    "execution_boundary",
    "external_action",
]


class WorkItemFacts(StrictModel):
    value_band: Literal["low", "medium", "high"]
    breadth: int = Field(ge=1, le=20)
    parallelism: int = Field(ge=1, le=20)
    deadline_pressure: Literal["low", "medium", "high"]
    risk_band: Literal["low", "medium", "high"]
    budget_band: Literal["tight", "approved", "ample"]
    source_labels: list[str] = Field(min_length=1)


class AdmissionReason(StrictModel):
    factor: Literal[
        "value",
        "breadth",
        "parallelism",
        "deadline",
        "risk",
        "budget",
    ]
    label: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=500)


class AdmissionForecast(StrictModel):
    source_type: Literal["fixture_policy_forecast"] = "fixture_policy_forecast"
    estimated_tool_calls: int = Field(ge=0, le=1_000)
    estimated_runtime_seconds: int = Field(ge=1, le=86_400)
    max_workers: int = Field(ge=1, le=20)


class RouteImpactChange(StrictModel):
    change_kind: RouteImpactKind
    aspect: RouteImpactAspect
    label: str = Field(min_length=1, max_length=80)
    before: str | None = Field(default=None, max_length=300)
    after: str = Field(min_length=1, max_length=500)
    detail: str | None = Field(default=None, max_length=500)


class RouteImpactPreview(StrictModel):
    summary: str = Field(min_length=1, max_length=500)
    changes: list[RouteImpactChange] = Field(min_length=4)
    execution_status_before: ExecutionStatus = "not_started"
    execution_status_after: ExecutionStatus = "not_started"
    external_side_effect: Literal["none"] = "none"

    @model_validator(mode="after")
    def validate_required_boundaries(self) -> RouteImpactPreview:
        aspects = {change.aspect for change in self.changes}
        required = {"execution_boundary", "external_action"}
        if not required.issubset(aspects):
            raise ValueError("route impact preview must include execution and external action boundaries")
        return self


class RouteSelectionProcessing(StrictModel):
    """Server-observed route-selection path; absent on legacy receipts."""

    path: Literal["policy_engine"] = "policy_engine"
    model_called: Literal[False] = False
    elapsed_ms: int = Field(ge=0)


class RouteSelectionReceipt(StrictModel):
    receipt_id: str = Field(min_length=1, max_length=160)
    from_cockpit_version: int = Field(ge=1)
    to_cockpit_version: int = Field(ge=1)
    from_item_version: int = Field(ge=1)
    to_item_version: int = Field(ge=1)
    selected_mode: ExecutionMode
    selection_source: RouteSelectionSource
    override_scope: OverrideScope | None = None
    forecast: AdmissionForecast
    changes: list[RouteImpactChange] = Field(min_length=4)
    execution_status_before: ExecutionStatus = "not_started"
    execution_status_after: ExecutionStatus = "not_started"
    external_side_effect: Literal["none"] = "none"
    processing: RouteSelectionProcessing | None = None
    summary: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_receipt_transition(self) -> RouteSelectionReceipt:
        if self.to_cockpit_version <= self.from_cockpit_version:
            raise ValueError("cockpit version must advance")
        if self.to_item_version <= self.from_item_version:
            raise ValueError("work item version must advance")
        aspects = {change.aspect for change in self.changes}
        required = {"route_decision", "execution_boundary", "external_action"}
        if not required.issubset(aspects):
            raise ValueError("route selection receipt is missing required impact boundaries")
        return self


class AdmissionRecommendation(StrictModel):
    mode: ExecutionMode
    summary: str = Field(min_length=1, max_length=300)
    reasons: list[AdmissionReason] = Field(min_length=1)
    forecast: AdmissionForecast
    policy_version: str = Field(min_length=1, max_length=80)


class RouteProfile(StrictModel):
    mode: ExecutionMode
    label: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=300)
    forecast: AdmissionForecast
    tradeoff: str = Field(min_length=1, max_length=500)
    candidate_only: bool = False
    impact_preview: RouteImpactPreview | None = None


class WorkItemSnapshot(StrictModel):
    work_item_id: str = Field(min_length=1, max_length=120)
    owner_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=200)
    objective: str = Field(min_length=1, max_length=1_000)
    business_status: Literal["attention", "ready", "waiting"]
    priority: int = Field(ge=1, le=100)
    facts: WorkItemFacts
    allowed_modes: list[ExecutionMode] = Field(min_length=1)
    route_profiles: list[RouteProfile] = Field(min_length=1)
    admission_status: AdmissionStatus = "recommended"
    recommendation: AdmissionRecommendation
    selected_mode: ExecutionMode | None = None
    selection_source: RouteSelectionSource | None = None
    override_scope: OverrideScope | None = None
    execution_status: ExecutionStatus = "not_started"
    execution_id: str | None = None
    selection_receipt: RouteSelectionReceipt | None = None
    selection_receipts: list[RouteSelectionReceipt] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    last_event_sequence: int = Field(default=1, ge=1)
    last_event_type: Literal[
        "ADMISSION_EVALUATED",
        "ROUTE_SELECTED",
        "EXECUTION_QUEUED",
        "EXECUTION_STARTED",
        "WORKER_STARTED",
        "WORKER_COMPLETED",
        "WORKER_FAILED",
        "WORKER_CANCELLED",
        "DYNAMIC_REPLAN",
        "WORKER_ADDED",
        "EXECUTION_VERIFYING",
        "ARTIFACT_VERIFIED",
        "EXECUTION_COMPLETED",
        "EXECUTION_FAILED",
        "EXECUTION_CANCELLED",
    ] = "ADMISSION_EVALUATED"

    @model_validator(mode="after")
    def normalize_and_validate_receipt_history(self) -> WorkItemSnapshot:
        if self.selection_receipt is not None and not self.selection_receipts:
            self.selection_receipts = [self.selection_receipt]
        elif self.selection_receipt is None and self.selection_receipts:
            self.selection_receipt = self.selection_receipts[-1]
        if not self.selection_receipts:
            return self
        if self.selection_receipt is None or self.selection_receipts[-1].receipt_id != self.selection_receipt.receipt_id:
            raise ValueError("latest route receipt must match receipt history")
        for previous, current in zip(self.selection_receipts, self.selection_receipts[1:], strict=False):
            if current.from_cockpit_version != previous.to_cockpit_version:
                raise ValueError("cockpit receipt history must be contiguous")
            if current.from_item_version != previous.to_item_version:
                raise ValueError("work item receipt history must be contiguous")
        return self


class WorkCockpitSnapshot(StrictModel):
    owner_id: str = Field(min_length=1, max_length=120)
    backend: Literal["memory"] = "memory"
    version: int = Field(default=1, ge=1)
    last_event_sequence: int = Field(default=4, ge=1)
    items: list[WorkItemSnapshot] = Field(min_length=1)


class RouteSelectionResult(StrictModel):
    cockpit_version: int = Field(ge=1)
    cockpit_last_event_sequence: int = Field(ge=1)
    item: WorkItemSnapshot


class RouteSelectionRequest(StrictModel):
    mode: ExecutionMode
    scope: OverrideScope = "this_run"
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=160)


WorkerStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
WorkerRole = Literal[
    "revenue_analyst",
    "project_risk_analyst",
    "request_context_analyst",
    "reconciliation_analyst",
    "synthesis_verifier",
]
WorkerTrigger = Literal["initial_plan", "dynamic_replan", "verification"]
ArtifactStatus = Literal["draft", "validated"]
WorkerProcessingKind = Literal["language_model", "deterministic", "policy_engine"]
WorkerProcessingPath = Literal["language_model", "deterministic"]
WorkerOutputUsed = Literal["model", "deterministic", "template_fallback"]


class WorkerProcessing(StrictModel):
    path: WorkerProcessingPath
    kind: WorkerProcessingKind
    label: str = Field(min_length=1, max_length=120)
    model_called: bool = False
    model: str | None = Field(default=None, max_length=120)
    elapsed_ms: int | None = Field(default=None, ge=0)
    output_used: WorkerOutputUsed
    fallback_reason: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_processing_truth(self) -> WorkerProcessing:
        if self.path == "deterministic":
            if self.kind != "deterministic":
                raise ValueError("deterministic path must use deterministic kind")
            if self.model_called or self.model is not None or self.output_used == "model":
                raise ValueError("deterministic path cannot claim model facts")
        else:
            if self.kind != "language_model" or not self.model_called or not self.model:
                raise ValueError("language-model path requires an observed model call")
            if self.output_used == "deterministic":
                raise ValueError("language-model path cannot claim deterministic output")
        if self.output_used == "template_fallback" and not self.fallback_reason:
            raise ValueError("template fallback requires a bounded reason")
        if self.output_used != "template_fallback" and self.fallback_reason is not None:
            raise ValueError("fallback reason is only valid for template fallback")
        return self


class Demo2WorkerSpec(StrictModel):
    worker_run_id: str = Field(min_length=1, max_length=160)
    work_item_id: str = Field(min_length=1, max_length=120)
    role: WorkerRole
    label: str = Field(min_length=1, max_length=160)
    objective: str = Field(min_length=1, max_length=600)
    depends_on: list[str] = Field(default_factory=list, max_length=20)
    source_document_ids: list[str] = Field(min_length=1, max_length=20)
    trigger: WorkerTrigger = "initial_plan"
    status: WorkerStatus = "queued"
    started_at: datetime | None = None
    completed_at: datetime | None = None
    artifact_version_id: str | None = None
    error_code: str | None = None
    processing: WorkerProcessing | None = None


class SharedArtifactVersion(StrictModel):
    artifact_version_id: str = Field(min_length=1, max_length=160)
    artifact_id: str = Field(min_length=1, max_length=160)
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=240)
    kind: Literal["worker_finding", "verified_report_bundle"]
    status: ArtifactStatus
    produced_by_worker_run_id: str | None = None
    source_document_ids: list[str] = Field(min_length=1, max_length=20)
    content: dict[str, Any] = Field(min_length=1, max_length=30)
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: datetime


class SwarmEvent(StrictModel):
    execution_id: str = Field(min_length=1, max_length=160)
    sequence: int = Field(ge=1)
    event_type: Literal[
        "EXECUTION_QUEUED",
        "EXECUTION_STARTED",
        "WORKER_STARTED",
        "WORKER_COMPLETED",
        "WORKER_FAILED",
        "WORKER_CANCELLED",
        "DYNAMIC_REPLAN",
        "WORKER_ADDED",
        "EXECUTION_VERIFYING",
        "ARTIFACT_VERIFIED",
        "EXECUTION_COMPLETED",
        "EXECUTION_FAILED",
        "EXECUTION_CANCELLED",
    ]
    occurred_at: datetime
    status: ExecutionStatus
    worker_run_id: str | None = None
    artifact_version_id: str | None = None
    message: str = Field(min_length=1, max_length=600)
    details: dict[str, str] = Field(default_factory=dict, max_length=20)


class ExecutionReceipt(StrictModel):
    receipt_id: str = Field(min_length=1, max_length=160)
    execution_id: str = Field(min_length=1, max_length=160)
    work_item_id: str = Field(min_length=1, max_length=120)
    status: Literal["completed", "failed", "cancelled"]
    worker_run_ids: list[str] = Field(min_length=1, max_length=20)
    artifact_version_ids: list[str] = Field(min_length=1, max_length=20)
    final_artifact_version_id: str | None = None
    external_side_effect: Literal["none"] = "none"
    started_at: datetime
    completed_at: datetime
    summary: str = Field(min_length=1, max_length=800)


class Demo2ExecutionSnapshot(StrictModel):
    backend: Literal["memory"] = "memory"
    execution_id: str = Field(min_length=1, max_length=160)
    owner_id: str = Field(min_length=1, max_length=120)
    work_item_id: str = Field(min_length=1, max_length=120)
    mode: Literal["adaptive_swarm"] = "adaptive_swarm"
    status: ExecutionStatus
    version: int = Field(ge=1)
    last_event_sequence: int = Field(ge=0)
    source_document_ids: list[str] = Field(min_length=1, max_length=20)
    worker_runs: list[Demo2WorkerSpec] = Field(default_factory=list, max_length=20)
    artifacts: list[SharedArtifactVersion] = Field(default_factory=list, max_length=30)
    events: list[SwarmEvent] = Field(default_factory=list, max_length=200)
    receipt: ExecutionReceipt | None = None
    budget_max_workers: int = Field(default=3, ge=1, le=4)
    budget_max_worker_runs: int = Field(default=4, ge=1, le=6)


class Demo2ExecutionStartRequest(StrictModel):
    expected_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=8, max_length=160)
    max_workers: int = Field(default=3, ge=1, le=3)


class Demo2ExecutionStartResult(StrictModel):
    replayed: bool = False
    item: WorkItemSnapshot
    execution: Demo2ExecutionSnapshot
