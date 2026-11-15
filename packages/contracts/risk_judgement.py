"""Five-factor risk judgement record (manual v1.1, section 4.2-4.5 and 4.8).

The record is what a reviewer needs to re-check a level: each factor's value,
the level floor it implies, which merge rules fired, the autonomy cap and the
action form, and the intervention that comes first.  It is produced by
``services.api.app.application.risk_judgement`` and never by a model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["L0", "L1", "L2", "L3", "L4", "L5"]
AutonomyLevel = Literal["AL0", "AL1", "AL2", "AL3", "AL4", "AL5"]

FactorKey = Literal["state_change", "scope", "recoverability", "sensitivity", "authority"]

StateChange = Literal["read_only", "own_content", "draft", "internal_record", "external_commit"]
Scope = Literal["none", "self", "internal_small", "internal_batch", "external", "major_batch"]
Recoverability = Literal["full", "partial", "irreversible"]
Sensitivity = Literal["routine", "controlled", "high"]
Authority = Literal["own", "approval_needed", "forbidden"]
ActionForm = Literal["status_only", "suggest", "content", "implement", "maintenance"]

Intervention = Literal[
    "user_takeover", "restricted", "missing_info", "business_judgment",
    "execution_authorization", "execution_exception",
]

MergeRule = Literal[
    "restricted_first", "take_highest", "unknown_as_high",
    "reason_no_downgrade", "per_action", "recheck_on_change",
]


class FactorFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: FactorKey
    label: str
    value: str
    value_label: str
    floor: RiskLevel
    # True when the value is an assumption taken at the high end because the
    # fact is not known yet (merge rule 3).  Clarification replaces it.
    assumed: bool = False
    basis: str = Field(default="", max_length=300)
    # True when this factor's floor equals the final level.
    drives_level: bool = False


class RiskJudgement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    judgement_version: Literal["five-factor.v1"] = "five-factor.v1"
    threshold_version: Literal["thresholds.default.v1"] = "thresholds.default.v1"
    factors: list[FactorFinding] = Field(min_length=5, max_length=5)
    rules_applied: list[MergeRule] = Field(default_factory=list, max_length=6)
    rule_notes: list[str] = Field(default_factory=list, max_length=8)
    risk_level: RiskLevel
    autonomy_cap: AutonomyLevel
    action_form: ActionForm
    action_form_label: str
    autonomy_level: AutonomyLevel
    # First intervention to raise now (manual 4.5); later ones are listed as "后续还需".
    intervention: Intervention | None = None
    intervention_label: str | None = None
    follow_ups: list[str] = Field(default_factory=list, max_length=5)
