from __future__ import annotations

from typing import Literal

from pydantic import Field

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
    version: int = Field(default=1, ge=1)
    last_event_sequence: int = Field(default=1, ge=1)
    last_event_type: Literal["ADMISSION_EVALUATED", "ROUTE_SELECTED"] = "ADMISSION_EVALUATED"


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
