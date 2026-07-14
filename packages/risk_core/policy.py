from typing import Any

from packages.contracts import CapabilityDecision, PolicyEffect, ProposedActionSpec, RiskAssessment


POLICY_VERSION = "2026-07-v1"

_RESTRICTED_CAPABILITIES = {
    "expense.approve",
    "finance.pay",
    "contract.sign",
    "iam.permission.change",
    "credential.read",
    "data.bulk_delete",
}

_INTERNAL_WRITES = {
    "task.create",
    "calendar.invite",
    "crm.opportunity.update",
    "expense.request_evidence",
}


def evaluate_policies(
    action: ProposedActionSpec,
    risk: RiskAssessment,
    trusted_context: dict[str, Any],
) -> list[PolicyEffect]:
    effects = [
        PolicyEffect(
            policy_id="baseline_v1",
            capability_effects={
                action.capability: CapabilityDecision(verdict="allow"),
            },
        )
    ]

    if action.capability == "email.send" and action.target_scope.startswith("external"):
        effects.append(
            PolicyEffect(
                policy_id="external_email_v1",
                capability_effects={
                    "email.draft": CapabilityDecision(verdict="allow"),
                    "email.preview": CapabilityDecision(verdict="allow"),
                    "email.send": CapabilityDecision(verdict="blocked"),
                },
                required_evidence=["recipient_identity", "attachment_hash", "dlp_result"],
                required_approvals=["current_user"],
                reason_codes=["EXTERNAL_SEND_RESTRICTED"],
            )
        )

    if action.capability in _INTERNAL_WRITES:
        evidence_requirement = {
            "task.create": "project_write_access",
            "calendar.invite": "calendar_availability",
            "crm.opportunity.update": "crm_write_access",
            "expense.request_evidence": "expense_case_access",
        }[action.capability]
        effects.append(
            PolicyEffect(
                policy_id=f"{action.capability.replace('.', '_')}_v1",
                capability_effects={
                    action.capability: CapabilityDecision(verdict="blocked")
                },
                required_evidence=[evidence_requirement],
                required_approvals=["current_user"],
                reason_codes=["INTERNAL_SYSTEM_WRITE"],
            )
        )

    if action.capability == "calendar.invite" and action.target_scope.startswith("external"):
        effects.append(
            PolicyEffect(
                policy_id="external_calendar_invite_v1",
                capability_effects={
                    action.capability: CapabilityDecision(verdict="blocked")
                },
                required_evidence=["recipient_identity"],
                required_approvals=["current_user"],
                reason_codes=["EXTERNAL_INVITE"],
            )
        )

    if "pricing" in action.data_classes:
        effects.append(
            PolicyEffect(
                policy_id="pricing_data_v1",
                capability_effects={
                    action.capability: CapabilityDecision(
                        verdict="blocked",
                        constraints=["price_must_match_approved_quote"],
                    )
                },
                required_evidence=["pricing_source"],
                required_approvals=["sales_manager"],
                constraints=["price_must_match_approved_quote"],
                reason_codes=["PRICING_EXTERNAL_SEND"],
            )
        )

    if not trusted_context.get("device", {}).get("managed", False) and action.state_change_type in {
        "internal_effect",
        "internal_system_write",
        "external_effect",
        "restricted_execution",
    }:
        effects.append(
            PolicyEffect(
                policy_id="unmanaged_device_v1",
                capability_effects={
                    "email.draft": CapabilityDecision(verdict="allow"),
                    action.capability: CapabilityDecision(verdict="deny"),
                },
                reason_codes=["UNMANAGED_DEVICE"],
            )
        )

    if action.capability in _RESTRICTED_CAPABILITIES:
        effects.append(
            PolicyEffect(
                policy_id="restricted_office_actions_v1",
                capability_effects={
                    action.capability: CapabilityDecision(verdict="deny")
                },
                reason_codes=["MANUAL_PROCESS_REQUIRED"],
            )
        )

    if risk.risk_level == "L5":
        effects.append(
            PolicyEffect(
                policy_id="critical_risk_v1",
                capability_effects={
                    action.capability: CapabilityDecision(verdict="deny")
                },
                reason_codes=["CRITICAL_RISK_DENIED"],
            )
        )
    return effects
