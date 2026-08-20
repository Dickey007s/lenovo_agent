from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TaskArtifactBinding(StrictModel):
    """Immutable Task artifact facts bound to a governed action."""

    task_id: str = Field(min_length=1, max_length=120)
    task_version: int = Field(ge=1)
    commit_id: str = Field(min_length=1, max_length=120)
    commit_state_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    artifact_id: str = Field(min_length=1, max_length=120)
    artifact_version_id: str = Field(min_length=1, max_length=160)
    artifact_version: int = Field(ge=1)
    artifact_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    deliverable_id: str = Field(min_length=1, max_length=100)
    verification_report_id: str = Field(min_length=1, max_length=120)


ImpactChangeKind = Literal[
    "will_change",
    "will_recheck",
    "unchanged",
    "no_external_action",
]

_IMPACT_KINDS = {
    "will_change",
    "will_recheck",
    "unchanged",
    "no_external_action",
}
_IMPACT_ITEM_KINDS = {
    "target-change": "will_change",
    "binding-recheck": "will_recheck",
    "task-preserved": "unchanged",
    "real-connector-not-called": "no_external_action",
}


class ImpactItem(StrictModel):
    """Server-owned business fact used by action previews and receipts."""

    item_id: Literal[
        "target-change",
        "binding-recheck",
        "task-preserved",
        "real-connector-not-called",
    ]
    change_kind: ImpactChangeKind
    label: str = Field(min_length=1, max_length=200)
    before: str | None = None
    after: str | None = None

    @model_validator(mode="after")
    def validate_kind(self) -> "ImpactItem":
        if self.change_kind not in _IMPACT_KINDS:
            raise ValueError("unsupported impact change kind")
        if _IMPACT_ITEM_KINDS[self.item_id] != self.change_kind:
            raise ValueError("impact item id does not match its change kind")
        return self


class ActionImpactPreview(StrictModel):
    """Deterministic expectation shown before a governed action is confirmed."""

    schema_version: Literal["1.0"] = "1.0"
    preview_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)
    action_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    policy_version: str = Field(min_length=1, max_length=120)
    items: list[ImpactItem] = Field(min_length=4, max_length=4)
    executor: str | None = Field(default=None, max_length=120)
    external_side_effect: Literal["none", "simulator_only", "external"] = "none"
    generated_at: datetime
    task_artifact_binding: TaskArtifactBinding | None = None

    @model_validator(mode="after")
    def validate_four_impact_kinds(self) -> "ActionImpactPreview":
        kinds = [item.change_kind for item in self.items]
        if set(kinds) != _IMPACT_KINDS or len(kinds) != len(_IMPACT_KINDS):
            raise ValueError("action impact preview must contain each impact kind once")
        return self


class ActionExecutionReceipt(StrictModel):
    """Server receipt for the terminal decision or tool execution outcome."""

    schema_version: Literal["1.0"] = "1.0"
    receipt_id: str = Field(min_length=1, max_length=160)
    action_id: str = Field(min_length=1, max_length=160)
    action_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    status: Literal["succeeded", "denied", "failed", "unknown"]
    items: list[ImpactItem] = Field(min_length=4, max_length=4)
    execution_id: str | None = Field(default=None, max_length=160)
    permit_id: str | None = Field(default=None, max_length=160)
    simulator: str | None = Field(default=None, max_length=120)
    external_side_effect: Literal["none", "simulator_only", "external", "unknown"]
    error_code: str | None = Field(default=None, max_length=160)
    failure_stage: Literal["binding", "policy", "authorization", "gateway", "simulator"] | None = None
    retryable: bool = False
    observed_at: datetime

    @model_validator(mode="after")
    def validate_four_impact_kinds(self) -> "ActionExecutionReceipt":
        kinds = [item.change_kind for item in self.items]
        if set(kinds) != _IMPACT_KINDS or len(kinds) != len(_IMPACT_KINDS):
            raise ValueError("action execution receipt must contain each impact kind once")
        return self


class ActionCandidate(StrictModel):
    """Only business facts may come from the language model."""

    action_type: Literal[
        "mail_search",
        "draft_email",
        "send_email",
        "document_search",
        "generate_summary",
        "draft_document",
        "insert_document",
        "quote_lookup",
        "quote_compare",
        "quote_calculate",
        "quote_draft",
        "rank_tasks",
        "create_internal_task",
        "find_calendar_slots",
        "create_calendar_invite",
        "expense_inspect",
        "expense_request_evidence",
        "crm_customer_read",
        "update_crm_stage",
        "approve_expense",
        "make_payment",
        "sign_contract",
        "change_permission",
        "read_credential",
        "bulk_delete",
    ]
    capability: Literal[
        "mail.search",
        "email.draft",
        "email.send",
        "document.search",
        "document.summarize",
        "document.draft",
        "document.insert",
        "quote.read",
        "quote.compare",
        "quote.calculate",
        "quote.draft",
        "task.rank",
        "task.create",
        "calendar.read",
        "calendar.invite",
        "expense.read",
        "expense.request_evidence",
        "crm.customer.read",
        "crm.opportunity.update",
        "expense.approve",
        "finance.pay",
        "contract.sign",
        "iam.permission.change",
        "credential.read",
        "data.bulk_delete",
    ]
    target_scope: Literal[
        "self",
        "internal_member",
        "internal_team",
        "cross_department",
        "external_customer",
        "external_supplier",
        "public",
        "batch_external",
    ]
    recipients: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    data_classes: list[
        Literal[
            "public",
            "internal",
            "customer_data",
            "supplier_data",
            "pricing",
            "financial",
            "project_risk",
            "contract",
            "hr",
            "permission",
            "security_log",
            "personal_sensitive",
            "credentials",
        ]
    ] = Field(default_factory=list)
    state_change_type: Literal[
        "no_state_change",
        "read_only",
        "draft_only",
        "local_state_change",
        "internal_effect",
        "internal_system_write",
        "external_effect",
        "restricted_execution",
    ]
    reversibility: Literal["high", "medium", "low"]
    source_refs: list[str] = Field(default_factory=list)
    missing_slots: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class ProposedActionSpec(ActionCandidate):
    schema_version: Literal["1.0"] = "1.0"
    trace_id: str
    action_id: str
    actor_id: str
    payload_digest: str
    idempotency_key: str
    task_artifact_binding: TaskArtifactBinding | None = None


class RiskDimensions(StrictModel):
    impact: Literal["low", "medium", "high"]
    data_sensitivity: Literal["low", "medium", "high"]
    blast_radius: Literal["self", "internal", "external_customer", "public"]
    reversibility: Literal["high", "medium", "low"]
    uncertainty: Literal["low", "medium", "high"]


class RiskAssessment(StrictModel):
    action_id: str
    risk_level: Literal["L0", "L1", "L2", "L3", "L4", "L5"]
    dimensions: RiskDimensions
    reason_codes: list[str] = Field(default_factory=list)


class CapabilityDecision(StrictModel):
    verdict: Literal["allow", "blocked", "deny"]
    constraints: list[str] = Field(default_factory=list)


class PolicyEffect(StrictModel):
    policy_id: str
    matched: bool = True
    capability_effects: dict[str, CapabilityDecision] = Field(default_factory=dict)
    required_evidence: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


EvidenceStatus = Literal["satisfied", "missing", "stale", "conflict", "unavailable"]


class EvidenceRecord(StrictModel):
    requirement: str
    status: EvidenceStatus
    source: str
    reference: str | None = None
    digest: str | None = None
    checked_at: datetime
    expires_at: datetime | None = None


class ApprovalRecord(StrictModel):
    approval_id: str
    action_id: str
    approver_role: str
    approver_id: str
    decision: Literal["approved", "rejected"]
    created_at: datetime


class PanelSpec(StrictModel):
    type: Literal["denied", "clarification", "approval", "preview", "result", "error"]
    message: str


class ControlPlan(StrictModel):
    action_id: str
    action_hash: str
    risk_level: Literal["L0", "L1", "L2", "L3", "L4", "L5"]
    status: Literal[
        "DENIED",
        "WAITING_EVIDENCE",
        "WAITING_APPROVAL",
        "READY_TO_AUTHORIZE",
        "AUTHORIZED",
        "EXECUTED",
        "FAILED",
    ]
    capabilities: dict[str, CapabilityDecision]
    missing_requirements: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)
    panel: PanelSpec
    schema_version: Literal["1.0"] = "1.0"
    policy_version: str


class PermitMetadata(StrictModel):
    permit_id: str
    subject: str
    capability: str
    action_hash: str
    policy_version: str
    max_uses: int
    expires_at: datetime
    idempotency_key: str


class ToolExecutionResult(StrictModel):
    execution_id: str
    capability: str
    status: Literal["succeeded", "failed"]
    simulator: str
    idempotency_key: str
    output: dict
    executed_at: datetime


class AuditEvent(StrictModel):
    sequence: int
    event_id: str
    run_id: str
    trace_id: str
    action_id: str | None = None
    actor_id: str
    event_type: str
    payload: dict = Field(default_factory=dict)
    occurred_at: datetime
