"""Fixed-source count checks are not a general semantic verifier."""

import copy

import pytest

from services.api.app.application.readonly_source_facts import (
    ReadonlySourceFactsError, readonly_numeric_error, readonly_source_context,
)
from tests.unit.test_release_readiness_effect import FORTE_ROOT, BenchmarkWorkspaceCatalog, _previews, _row


@pytest.fixture
def sources():
    return list(_previews(BenchmarkWorkspaceCatalog(FORTE_ROOT)).values())


def test_counts_exclude_headers_and_preserve_conditional_pass_rule(sources, monkeypatch):
    def no_render(*args, **kwargs):
        raise AssertionError("Read-only checks must not render any files")
    monkeypatch.setattr("services.api.app.application.release_readiness_effect._report_docx", no_render)
    monkeypatch.setattr("services.api.app.application.release_readiness_effect._ledger_csv", no_render)
    context = readonly_source_context(sources)
    assert context["counts"] == {"prd_features": 18, "p0_features": 7,
                                  "configured_features": 13, "submitted_features": 13}
    assert context["p0_feature_ids"] == ["F01", "F02", "F06", "F07", "F09", "F10", "F11"]
    gate = next(item for item in context["gates"] if item["gate_id"] == "business-gate-p0-accepted")
    assert (gate["numerator"], gate["denominator"]) == (4, 5)
    assert "有条件通过" in str(gate)


def test_counts_follow_source_changes_not_canonical_totals(sources):
    by_name = {item["display_label"]: item for item in sources}
    prd = by_name["PRD_v2.5.md"]
    prd["text"] = "\n".join(line.replace("| P0 |", "| P1 |") if "| F09 |" in line else line
                            for line in prd["text"].splitlines())
    _row(by_name, "上线配置清单.xlsx", "F01")["values"][-1] = "待提测"
    context = readonly_source_context(sources)
    assert context["counts"]["p0_features"] == 6
    assert context["counts"]["configured_features"] == 13
    assert context["counts"]["submitted_features"] == 12
    assert readonly_numeric_error(context, {"summary": "P0 功能共 7 项。"})
    assert readonly_numeric_error(context, {"summary": "配置清单仅 13 项已提测。"})
    assert not readonly_numeric_error(context, {"summary": "配置清单共 13 项。P0 功能共 6 项。"})


@pytest.mark.parametrize("text", [
    "P0 功能共 6 项。", "PRD 列 17 项功能。", "配置清单仅 14 项已提测。", "上线配置清单共 14 个功能。",
])
def test_wrong_explicit_counts_rejected_in_all_adoptable_fields(sources, text):
    context = readonly_source_context(sources)
    assert readonly_numeric_error(context, {"summary": text})
    assert readonly_numeric_error(context, {"follow_ups": [text]})
    assert readonly_numeric_error(context, {"findings": [{"fact_summary": text}]})
    assert readonly_numeric_error(context, {"dependency_assessments": [{"explanation": text}]})


def test_unknown_prose_and_thresholds_not_claimed_verified_or_false_rejected(sources):
    context = readonly_source_context(sources)
    for text in ["P0 功能共 7 项。配置清单仅 13 项已提测。PRD 列 18 项功能。",
                 "要求 P0 功能共 8 项。", "假设 P0 功能有 8 项。", "P0 功能风险较高。",
                 "PRD 共 7 项 P0 功能。", "PRD列出7项P0功能。", "PRD列出5项未提测功能。"]:
        assert readonly_numeric_error(context, {"summary": text}) is None
    assert readonly_numeric_error(context, {"findings": [{"evidence_quotes": [{"quote": "P0 功能共 6 项"}]}]}) is None
    assert readonly_source_context(sources[:-1]) is None
    assert readonly_source_context([{**item, "display_group": "other"} for item in sources]) is None


@pytest.mark.parametrize("fault", ["truncated", "duplicate", "invalid", "missing_rows"])
def test_present_but_invalid_bundle_never_silently_disables_check(sources, fault):
    sources = copy.deepcopy(sources)
    if fault == "truncated":
        sources[0]["truncated"] = True
    elif fault == "duplicate":
        sources.append(copy.deepcopy(sources[0]))
    elif fault == "invalid":
        next(item for item in sources if item["display_label"] == "PRD_v2.5.md")["text"] = "invalid"
    else:
        next(item for item in sources if item["kind"] == "table")["rows"].pop()
    with pytest.raises(ReadonlySourceFactsError):
        readonly_source_context(sources)
