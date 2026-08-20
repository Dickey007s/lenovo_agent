from __future__ import annotations

from typing import Literal

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
ExecutionStatus = Literal["not_started"]
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
    selection_receipt: RouteSelectionReceipt | None = None
    selection_receipts: list[RouteSelectionReceipt] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    last_event_sequence: int = Field(default=1, ge=1)
    last_event_type: Literal["ADMISSION_EVALUATED", "ROUTE_SELECTED"] = "ADMISSION_EVALUATED"

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
