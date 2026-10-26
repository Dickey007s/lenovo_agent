"""The browser's demonstration inputs must exercise real fixed-policy states."""
import json
from pathlib import Path

import pytest

from packages.contracts.office_actions import ActionInput
from services.api.app.application.office_action_policy import prepare_action

EXAMPLES = json.loads((Path(__file__).resolve().parents[2] /
    "apps/web/app/office-action-examples.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda item: item["id"])
def test_example_has_real_policy_boundary(example):
    data = ActionInput.model_validate(example["input"])
    result = prepare_action(data)
    assert result.status == example["expected_status"]
    assert result.model_called is False
    assert result.external_action == "none"
    assert data.source_ref is None
    assert result.decision is None
    if result.status in {"needs_input", "awaiting_decision", "awaiting_confirmation", "denied"}:
        assert result.receipt is None
    if data.operation == "send_message" and result.status != "denied":
        assert result.required_checks == ["target", "content", "impact"]


def test_example_catalog_identity_and_coverage():
    assert len(EXAMPLES) == len({item["id"] for item in EXAMPLES}) == 12
    assert len({item["input"]["title"] for item in EXAMPLES}) == 12
    assert {item["expected_status"] for item in EXAMPLES} == {
        "executed", "draft_ready", "needs_input", "awaiting_confirmation", "denied", "awaiting_decision",
    }
