from packages.contracts import ProposedActionSpec
from packages.risk_core import assess_risk


def make_action(**overrides: object) -> ProposedActionSpec:
    values = {
        "trace_id": "tr_1",
        "action_id": "act_1",
        "actor_id": "user_1",
        "action_type": "send_email",
        "capability": "email.send",
        "target_scope": "external_customer",
        "recipients": ["client@example.com"],
        "resources": ["quote.pdf"],
        "data_classes": ["pricing"],
        "state_change_type": "external_effect",
        "reversibility": "low",
        "source_refs": [],
        "missing_slots": [],
        "payload_digest": "sha256:candidate",
        "idempotency_key": "send_1",
    }
    values.update(overrides)
    return ProposedActionSpec.model_validate(values)


def test_external_pricing_email_is_high_risk() -> None:
    result = assess_risk(make_action())

    assert result.risk_level == "L4"
    assert {"EXTERNAL_RECIPIENT", "PRICING_DATA", "LOW_REVERSIBILITY"} <= set(
        result.reason_codes
    )


def test_incomplete_external_pricing_email_stays_reviewable() -> None:
    result = assess_risk(make_action(missing_slots=["recipient_email"]))

    assert result.risk_level == "L4"
    assert "ACTION_INFORMATION_MISSING" in result.reason_codes


def test_restricted_operation_is_the_only_critical_path() -> None:
    action = make_action(
        action_type="read_credential",
        capability="credential.read",
        target_scope="self",
        recipients=[],
        data_classes=["credentials"],
        state_change_type="restricted_execution",
        missing_slots=[],
    )

    assert assess_risk(action).risk_level == "L5"


def test_internal_reversible_action_is_not_high_risk() -> None:
    action = make_action(
        target_scope="internal_member",
        recipients=[],
        data_classes=[],
        reversibility="high",
    )

    assert assess_risk(action).risk_level == "L0"
