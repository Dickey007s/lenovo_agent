"""The browser's demonstration inputs must exercise real fixed-policy states."""
import json
from pathlib import Path

import pytest

from packages.contracts.office_actions import ActionInput
from services.api.app.application.office_action_policy import prepare_action
from services.api.app.application.benchmark_workspace_catalog import BenchmarkWorkspaceCatalog

APP = Path(__file__).resolve().parents[2] / "apps/web/app"
# Five headline cases, one per risk level L1-L5.
LEVELS = json.loads((APP / "office-action-examples.json").read_text(encoding="utf-8"))
# The earlier twelve boundary cases, folded away from the main path in the UI.
EXAMPLES = json.loads((APP / "office-action-examples-legacy.json").read_text(encoding="utf-8"))


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


def _library_index():
    """display_path -> file_ref for the real shared library the demo serves (same dicts the API returns)."""
    catalog = BenchmarkWorkspaceCatalog()
    index = {}
    for folder in catalog.public_workspace()["folders"]:
        for file in folder["files"]:
            index[file["display_path"]] = file["file_ref"]
    return catalog, index


def test_level_cases_cover_l1_to_l5_exactly_once():
    assert [item["level"] for item in LEVELS] == ["L1", "L2", "L3", "L4", "L5"]
    assert len({item["id"] for item in LEVELS}) == 5
    assert len({item["input"]["title"] for item in LEVELS}) == 5


@pytest.mark.parametrize("example", LEVELS, ids=lambda item: item["id"])
def test_level_case_lands_on_its_declared_level(example):
    """Labels shown in the UI must never drift from what the policy really decides."""
    catalog, index = _library_index()
    payload = dict(example["input"])
    source = None
    if example.get("sourcePath"):
        # The UI resolves the real file at runtime; do the same here.
        assert example["sourcePath"] in index, f"案例引用的文件不在资料库中：{example['sourcePath']}"
        payload["source_ref"] = index[example["sourcePath"]]
        source = catalog.public_file(payload["source_ref"])
    data = ActionInput.model_validate(payload)
    result = prepare_action(data, source)
    assert result.risk_level == example["level"]
    assert result.autonomy_level == example["autonomy"]
    assert result.status == example["expected_status"]
    assert result.missing_fields == []
    assert result.model_called is False
    assert result.external_action == "none"
    if example["level"] == "L4":
        assert result.required_checks == ["target", "content", "impact"]
    if example["level"] == "L5":
        assert result.receipt is None


def test_level_cases_reference_only_real_library_files():
    _, index = _library_index()
    for example in LEVELS:
        for path in example["sources"]:
            assert path in index, f"{example['id']} 引用了资料库中不存在的文件：{path}"
