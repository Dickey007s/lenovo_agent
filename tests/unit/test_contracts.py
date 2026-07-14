import pytest
from pydantic import ValidationError

from packages.contracts import ActionCandidate


def test_action_candidate_forbids_trusted_fields_and_unknown_properties() -> None:
    with pytest.raises(ValidationError):
        ActionCandidate.model_validate(
            {
                "action_type": "send_email",
                "capability": "email.send",
                "target_scope": "external_customer",
                "state_change_type": "external_effect",
                "reversibility": "low",
                "actor_id": "model_must_not_set_this",
            }
        )
