from packages.contracts import ProposedActionSpec, RiskAssessment
from packages.contracts.models import RiskDimensions


_SENSITIVE_DATA = {
    "credentials",
    "personal_sensitive",
    "financial",
    "pricing",
    "contract",
    "hr",
    "permission",
}
_RESTRICTED_CAPABILITIES = {
    "expense.approve",
    "finance.pay",
    "contract.sign",
    "iam.permission.change",
    "credential.read",
    "data.bulk_delete",
}


def assess_risk(action: ProposedActionSpec) -> RiskAssessment:
    external = action.target_scope in {
        "external_customer",
        "external_supplier",
        "batch_external",
    }
    public = action.target_scope == "public"
    sensitive = bool(_SENSITIVE_DATA.intersection(action.data_classes))
    missing = bool(action.missing_slots)
    critical = False

    score = 0
    reasons: list[str] = []
    if external:
        score += 2
        reasons.append("EXTERNAL_RECIPIENT")
    if public:
        score += 2
        reasons.append("PUBLIC_SCOPE")
    if sensitive:
        score += 1
        reasons.append("SENSITIVE_DATA")
    if "pricing" in action.data_classes:
        reasons.append("PRICING_DATA")
    if action.reversibility == "low":
        score += 1
        reasons.append("LOW_REVERSIBILITY")
    if missing:
        score += 1
        reasons.append("ACTION_INFORMATION_MISSING")
    if public and "credentials" in action.data_classes:
        critical = True
        reasons.append("CREDENTIAL_EXPOSURE")
    if action.capability in _RESTRICTED_CAPABILITIES:
        critical = True
        reasons.append("RESTRICTED_OPERATION")
    if action.state_change_type == "restricted_execution":
        critical = True
        reasons.append("RESTRICTED_EXECUTION")

    # L5 means "must be denied by policy", so ordinary business risk factors
    # must never reach it merely by addition. External sending, pricing,
    # low reversibility and incomplete slots stay reviewable at L4; only
    # explicitly restricted or credential-exposure actions are critical L5.
    level = 5 if critical else min(4, score)
    blast_radius = (
        "public"
        if public
        else "external_customer"
        if external
        else "internal"
        if action.target_scope.startswith("internal") or action.target_scope == "cross_department"
        else "self"
    )
    return RiskAssessment(
        action_id=action.action_id,
        risk_level=f"L{level}",
        dimensions=RiskDimensions(
            impact="high" if level >= 4 else "medium" if level >= 2 else "low",
            data_sensitivity="high" if sensitive else "low",
            blast_radius=blast_radius,
            reversibility=action.reversibility,
            uncertainty="high" if missing else "low",
        ),
        reason_codes=reasons,
    )
