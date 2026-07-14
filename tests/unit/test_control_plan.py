from datetime import UTC, datetime

from packages.contracts import ApprovalRecord, CapabilityDecision, EvidenceRecord, PolicyEffect
from packages.risk_core import assess_risk, build_control_plan
from tests.unit.test_risk import make_action


def effect() -> PolicyEffect:
    return PolicyEffect(
        policy_id="test",
        capability_effects={"email.send": CapabilityDecision(verdict="blocked")},
        required_evidence=["pricing_source"],
        required_approvals=["sales_manager"],
    )


def test_missing_evidence_blocks_before_approval() -> None:
    action = make_action(data_classes=[])
    plan = build_control_plan(action, assess_risk(action), [effect()], {}, [], "test-v1")

    assert plan.status == "WAITING_EVIDENCE"
    assert plan.missing_requirements == ["pricing_source"]


def test_complete_requirements_release_block() -> None:
    action = make_action(data_classes=[])
    evidence = {
        "pricing_source": EvidenceRecord(
            requirement="pricing_source",
            status="satisfied",
            source="test",
            checked_at=datetime.now(UTC),
        )
    }
    approval = ApprovalRecord(
        approval_id="approval_1",
        action_id=action.action_id,
        approver_role="sales_manager",
        approver_id="manager_1",
        decision="approved",
        created_at=datetime.now(UTC),
    )
    plan = build_control_plan(
        action, assess_risk(action), [effect()], evidence, [approval], "test-v1"
    )

    assert plan.status == "READY_TO_AUTHORIZE"
    assert plan.capabilities["email.send"].verdict == "allow"


def test_deny_has_precedence_over_allow() -> None:
    action = make_action(data_classes=[])
    effects = [
        PolicyEffect(
            policy_id="allow",
            capability_effects={"email.send": CapabilityDecision(verdict="allow")},
        ),
        PolicyEffect(
            policy_id="deny",
            capability_effects={"email.send": CapabilityDecision(verdict="deny")},
        ),
    ]

    plan = build_control_plan(action, assess_risk(action), effects, {}, [], "test-v1")
    assert plan.status == "DENIED"
