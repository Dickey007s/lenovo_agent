from collections.abc import Iterable

from packages.contracts import (
    ApprovalRecord,
    CapabilityDecision,
    ControlPlan,
    EvidenceRecord,
    PolicyEffect,
    ProposedActionSpec,
    RiskAssessment,
)
from packages.contracts.hashing import canonical_hash
from packages.contracts.models import PanelSpec


_PRECEDENCE = {"allow": 0, "blocked": 1, "deny": 2}
_REQUIREMENT_LABELS = {
    "recipient_identity": "收件人企业身份",
    "attachment_hash": "附件完整性校验",
    "dlp_result": "数据防泄漏扫描结果",
    "pricing_source": "已批准报价来源",
    "project_write_access": "项目任务写入权限",
    "calendar_availability": "与会人时间与日历权限",
    "crm_write_access": "CRM 商机写入权限",
    "expense_case_access": "报销单访问权限",
}


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _merge_capabilities(effects: list[PolicyEffect]) -> dict[str, CapabilityDecision]:
    merged: dict[str, CapabilityDecision] = {}
    for effect in effects:
        for capability, incoming in effect.capability_effects.items():
            current = merged.get(capability)
            constraints = _unique((current.constraints if current else []) + incoming.constraints)
            if current is None or _PRECEDENCE[incoming.verdict] > _PRECEDENCE[current.verdict]:
                merged[capability] = incoming.model_copy(update={"constraints": constraints})
            else:
                merged[capability] = current.model_copy(update={"constraints": constraints})
    return merged


def build_control_plan(
    action: ProposedActionSpec,
    risk: RiskAssessment,
    effects: list[PolicyEffect],
    evidence: dict[str, EvidenceRecord],
    approvals: list[ApprovalRecord],
    policy_version: str,
) -> ControlPlan:
    capabilities = _merge_capabilities(effects)
    requirements = _unique(req for effect in effects for req in effect.required_evidence)
    approvers = _unique(role for effect in effects for role in effect.required_approvals)
    missing = [
        requirement
        for requirement in requirements
        if evidence.get(requirement) is None or evidence[requirement].status != "satisfied"
    ]
    approved_roles = {
        approval.approver_role for approval in approvals if approval.decision == "approved"
    }
    rejected_roles = {
        approval.approver_role for approval in approvals if approval.decision == "rejected"
    }
    pending = [role for role in approvers if role not in approved_roles]
    target = capabilities.get(action.capability, CapabilityDecision(verdict="deny"))

    if rejected_roles or target.verdict == "deny":
        status = "DENIED"
        panel = PanelSpec(type="denied", message="当前策略不允许执行该动作。")
    elif missing:
        status = "WAITING_EVIDENCE"
        labels = [_REQUIREMENT_LABELS.get(requirement, requirement) for requirement in missing]
        panel = PanelSpec(type="clarification", message=f"仍缺少：{', '.join(labels)}")
    elif pending:
        status = "WAITING_APPROVAL"
        panel = PanelSpec(type="approval", message=f"等待审批：{', '.join(pending)}")
    else:
        status = "READY_TO_AUTHORIZE"
        capabilities[action.capability] = target.model_copy(update={"verdict": "allow"})
        panel = PanelSpec(type="preview", message="证据和审批已满足，可以申请一次性执行许可。")

    reason_codes = _unique(
        risk.reason_codes
        + [code for effect in effects for code in effect.reason_codes]
        + (["REQUIRED_EVIDENCE_MISSING"] if missing else [])
        + (["APPROVAL_REJECTED"] if rejected_roles else [])
    )
    return ControlPlan(
        action_id=action.action_id,
        action_hash=canonical_hash(action),
        risk_level=risk.risk_level,
        status=status,
        capabilities=capabilities,
        missing_requirements=missing,
        required_approvals=pending,
        reason_codes=reason_codes,
        panel=panel,
        policy_version=policy_version,
    )
