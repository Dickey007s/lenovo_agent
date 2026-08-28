from __future__ import annotations

import csv
import io
import zipfile
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.legal_delegation_effect import (
    LegalDelegationValidationError,
    LegalSourceInput,
    analyze_legal_delegation_sources,
    build_legal_delegation_review,
    verify_legal_delegation_artifacts,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"


@pytest.fixture(scope="module")
def legal_sources() -> tuple[LegalSourceInput, ...]:
    catalog = BenchmarkWorkspaceCatalog(FORTE_ROOT)
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-07")
    return ScenarioEffectEngine._legal_source_inputs(catalog, spec)


def _replace_source(
    sources: tuple[LegalSourceInput, ...],
    logical_id: str,
    replacement: LegalSourceInput,
) -> tuple[LegalSourceInput, ...]:
    return tuple(replacement if item.logical_id == logical_id else item for item in sources)


def _rewrite_docx_bytes(
    content: bytes,
    *,
    replacements: dict[str, str] | None = None,
    append_paragraphs: tuple[str, ...] = (),
    clear_text: bool = False,
) -> bytes:
    replacements = replacements or {}
    with zipfile.ZipFile(io.BytesIO(content)) as source_package:
        members = {name: source_package.read(name) for name in source_package.namelist()}
    root = ET.fromstring(members["word/document.xml"])
    for paragraph in root.iter(f"{W}p"):
        text_nodes = list(paragraph.iter(f"{W}t"))
        visible = "".join(node.text or "" for node in text_nodes)
        if clear_text:
            for node in text_nodes:
                node.text = ""
        elif visible in replacements and text_nodes:
            text_nodes[0].text = replacements[visible]
            for node in text_nodes[1:]:
                node.text = ""
    body = root.find(f"{W}body")
    assert body is not None
    for value in append_paragraphs:
        paragraph = ET.Element(f"{W}p")
        run = ET.SubElement(paragraph, f"{W}r")
        text = ET.SubElement(run, f"{W}t")
        text.text = value
        section = body.find(f"{W}sectPr")
        if section is None:
            body.append(paragraph)
        else:
            body.insert(list(body).index(section), paragraph)
    members["word/document.xml"] = ET.tostring(
        root, encoding="utf-8", xml_declaration=True
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target_package:
        for name, payload in members.items():
            target_package.writestr(name, payload)
    return output.getvalue()


def _mutate_docx(
    source: LegalSourceInput,
    *,
    replacements: dict[str, str] | None = None,
    append_paragraphs: tuple[str, ...] = (),
    clear_text: bool = False,
) -> LegalSourceInput:
    content = _rewrite_docx_bytes(
        source.content,
        replacements=replacements,
        append_paragraphs=append_paragraphs,
        clear_text=clear_text,
    )
    return replace(source, content=content, declared_size=len(content))


def _mutate_rules(
    source: LegalSourceInput, old: str, new: str
) -> LegalSourceInput:
    text = source.content.decode("utf-8")
    assert old in text
    content = text.replace(old, new, 1).encode("utf-8")
    return replace(source, content=content, declared_size=len(content))


def _review(analysis, document_id: str):
    return next(item for item in analysis.reviews if item.document_id == document_id)


def _assessment(review, rule_id: str):
    return next(item for item in review.assessments if item.rule_id == rule_id)


def test_public_legal_sources_produce_126_source_derived_assessments(
    legal_sources: tuple[LegalSourceInput, ...],
) -> None:
    build = build_legal_delegation_review(legal_sources)
    outcome = build.analysis.legal_outcome

    assert outcome.document_count == 6
    assert outcome.rule_count == 21
    assert outcome.assessment_count == 126
    assert outcome.high_risk_document_count == 6
    assert outcome.critical_unverifiable_count == 11
    assert outcome.signing_evidence_count == 0
    assert outcome.human_review_required is True
    assert build.analysis.business_outcome.failed_gate_count == 3
    assert all(check.passed for check in build.checks)
    assert len(build.ledger_csv.decode("utf-8-sig").splitlines()) == 127
    assert build.docx_table_count >= 8

    for review in build.analysis.reviews:
        assert len(review.assessments) == 21
        assert _assessment(review, "R05").status == "triggered"
    document_four = _review(build.analysis, "DOC-04")
    assert _assessment(document_four, "R01").status == "triggered"
    assert _assessment(document_four, "R02").status == "triggered"
    assert _assessment(document_four, "M03").status == "triggered"
    for document_id in ("DOC-02", "DOC-06"):
        lawyer_review = _review(build.analysis, document_id)
        assert _assessment(lawyer_review, "M03").status == "unverifiable"
        assert "字段存在不等于资质已核验" in _assessment(lawyer_review, "M03").reason
    assert all(
        _assessment(review, "M02").status == "unverifiable"
        for review in build.analysis.reviews
    )


def test_repairing_one_source_only_changes_that_document_and_reduces_risk(
    legal_sources: tuple[LegalSourceInput, ...],
) -> None:
    baseline = analyze_legal_delegation_sources(legal_sources)
    document_four = next(item for item in legal_sources if item.logical_id == "DOC-04")
    repaired = _mutate_docx(
        document_four,
        replacements={
            "委托人：周丽华": "委托人：周丽华，身份证号：110101198812120028",
            "受托人：孙志强律师": "受托人：孙志强律师，执业证号：11101202010067890",
            "授权范围：一般授权，包括代为立案、参加庭审、提交证据。": (
                "授权范围：一般授权，包括代为立案、参加庭审、提交证据。"
                "禁止转委托。受托人因故意或重大过失造成委托人损失的，应承担赔偿责任。"
            ),
            "委托人签名：": "委托人签名：周丽华（测试签署对象）",
        },
    )
    mutated_sources = _replace_source(legal_sources, "DOC-04", repaired)
    mutated = build_legal_delegation_review(mutated_sources)

    before = _review(baseline, "DOC-04")
    after = _review(mutated.analysis, "DOC-04")
    assert after.triggered_count < before.triggered_count
    assert after.highest_triggered_level == "none"
    assert after.signing_evidence_status == "present"
    for rule_id in ("R01", "R02", "M07", "M08", "R05"):
        assert _assessment(after, rule_id).status == "not_triggered"
    assert _assessment(after, "M03").status == "unverifiable"
    assert mutated.analysis.legal_outcome.high_risk_document_count == 5
    assert mutated.analysis.legal_outcome.signing_evidence_count == 1
    assert all(
        _review(mutated.analysis, review.document_id).model_dump()
        == review.model_dump()
        for review in baseline.reviews
        if review.document_id != "DOC-04"
    )
    assert all(check.passed for check in mutated.checks)


def test_principal_and_agent_identity_fields_never_cross_contaminate(
    legal_sources: tuple[LegalSourceInput, ...],
) -> None:
    document_one = next(item for item in legal_sources if item.logical_id == "DOC-01")
    missing_principal_id = _mutate_docx(
        document_one,
        replacements={
            "委托人：张伟，身份证号：110101199003150012": "委托人：张伟",
        },
    )
    principal_analysis = analyze_legal_delegation_sources(
        _replace_source(legal_sources, "DOC-01", missing_principal_id)
    )
    principal_review = _review(principal_analysis, "DOC-01")
    principal_document = next(
        item for item in principal_analysis.documents if item.source.logical_id == "DOC-01"
    )
    assert principal_document.principal_identity == ""
    assert principal_document.agent_identity == "310115198506220045"
    assert principal_document.is_enterprise is False
    assert _assessment(principal_review, "R01").status == "triggered"
    assert _assessment(principal_review, "R02").status == "not_triggered"

    unrelated_credit_code = _mutate_docx(
        document_one,
        replacements={
            "委托人：张伟，身份证号：110101199003150012": "委托人：张伟",
            "受托人：李芳，身份证号：310115198506220045": (
                "受托人：李芳，身份证号：310115198506220045，"
                "关联机构统一社会信用代码：91310115MA1K4XY26Q"
            ),
        },
    )
    credit_analysis = analyze_legal_delegation_sources(
        _replace_source(legal_sources, "DOC-01", unrelated_credit_code)
    )
    credit_document = next(
        item for item in credit_analysis.documents if item.source.logical_id == "DOC-01"
    )
    assert credit_document.principal_identity == ""
    assert credit_document.is_enterprise is False
    assert _assessment(_review(credit_analysis, "DOC-01"), "R01").status == "triggered"

    missing_agent_id = _mutate_docx(
        document_one,
        replacements={
            "受托人：李芳，身份证号：310115198506220045": "受托人：李芳",
        },
    )
    agent_analysis = analyze_legal_delegation_sources(
        _replace_source(legal_sources, "DOC-01", missing_agent_id)
    )
    agent_review = _review(agent_analysis, "DOC-01")
    agent_document = next(
        item for item in agent_analysis.documents if item.source.logical_id == "DOC-01"
    )
    assert agent_document.principal_identity == "110101199003150012"
    assert agent_document.agent_identity == ""
    assert _assessment(agent_review, "R01").status == "not_triggered"
    assert _assessment(agent_review, "R02").status == "triggered"


@pytest.mark.parametrize(
    ("mutator", "expected_code"),
    [
        (lambda items: items[:-1], "source-count"),
        (
            lambda items: items
            + (replace(items[-1], logical_id="DOC-07", file_name="委托书7.docx"),),
            "source-count",
        ),
        (
            lambda items: _replace_source(
                items, "DOC-02", replace(items[1], logical_id="DOC-01")
            ),
            "duplicate-logical-id",
        ),
        (
            lambda items: _replace_source(
                items,
                "DOC-02",
                replace(
                    items[2],
                    content=items[1].content,
                    declared_size=len(items[1].content),
                ),
            ),
            "duplicate-document-content",
        ),
    ],
)
def test_source_contract_fails_closed_for_missing_extra_duplicate_or_alias_content(
    legal_sources: tuple[LegalSourceInput, ...], mutator, expected_code: str
) -> None:
    with pytest.raises(LegalDelegationValidationError) as exc_info:
        build_legal_delegation_review(mutator(legal_sources))
    assert exc_info.value.code == expected_code


def test_empty_document_fails_before_any_artifact_can_pass(
    legal_sources: tuple[LegalSourceInput, ...],
) -> None:
    document_one = next(item for item in legal_sources if item.logical_id == "DOC-01")
    empty = _mutate_docx(document_one, clear_text=True)
    with pytest.raises(LegalDelegationValidationError) as exc_info:
        build_legal_delegation_review(
            _replace_source(legal_sources, "DOC-01", empty)
        )
    assert exc_info.value.code == "docx-empty"


def test_rule_name_and_level_mutation_changes_ledger_and_summary_dynamically(
    legal_sources: tuple[LegalSourceInput, ...],
) -> None:
    rules = next(item for item in legal_sources if item.logical_id == "RULES")
    mutated_rules = _mutate_rules(
        rules,
        "| R05 | 签字/盖章完全缺失 | 🔴 高 |",
        "| R05 | 签署证据缺失 | 🟡 中 |",
    )
    build = build_legal_delegation_review(
        _replace_source(legal_sources, "RULES", mutated_rules)
    )

    assert build.analysis.legal_outcome.high_risk_document_count == 2
    assert build.analysis.legal_outcome.medium_risk_document_count == 4
    assert all(
        _assessment(review, "R05").rule_name == "签署证据缺失"
        and _assessment(review, "R05").rule_level == "medium"
        for review in build.analysis.reviews
    )
    rendered = build.ledger_csv.decode("utf-8-sig")
    assert "签署证据缺失" in rendered
    assert "签字/盖章完全缺失" not in rendered
    assert all(check.passed for check in build.checks)


@pytest.mark.parametrize(
    ("old", "new", "expected_code"),
    [
        (
            "| R05 | 签字/盖章完全缺失 | 🔴 高 |",
            "| R05 | 签字/盖章完全缺失 | 高中 |",
            "rule-level",
        ),
        (
            "| R05 | 签字/盖章完全缺失 | 🔴 高 |",
            "| X99 | 签字/盖章完全缺失 | 🔴 高 |",
            "rule-set",
        ),
        (
            "| R05 | 签字/盖章完全缺失 | 🔴 高 |",
            "| R01 | 签字/盖章完全缺失 | 🔴 高 |",
            "duplicate-rule",
        ),
    ],
)
def test_damaged_or_ambiguous_rule_contract_fails_closed(
    legal_sources: tuple[LegalSourceInput, ...],
    old: str,
    new: str,
    expected_code: str,
) -> None:
    rules = next(item for item in legal_sources if item.logical_id == "RULES")
    with pytest.raises(LegalDelegationValidationError) as exc_info:
        build_legal_delegation_review(
            _replace_source(legal_sources, "RULES", _mutate_rules(rules, old, new))
        )
    assert exc_info.value.code == expected_code


@pytest.mark.parametrize(
    ("replacements", "append_paragraphs", "expected_code"),
    [
        (
            {
                "授权期限：自2026年4月30日起至2027年4月30日止。": (
                    "授权期限：自2027年4月30日起至2026年4月30日止。"
                )
            },
            (),
            "date-order",
        ),
        (
            {
                "授权期限：自2026年4月30日起至2027年4月30日止。": (
                    "授权期限：自2026年2月30日起至2027年4月30日止。"
                )
            },
            (),
            "date-value",
        ),
        ({}, ("委托人：另一主体，身份证号：110101198001010011",), "field-conflict"),
    ],
)
def test_invalid_dates_or_conflicting_fields_fail_closed(
    legal_sources: tuple[LegalSourceInput, ...],
    replacements: dict[str, str],
    append_paragraphs: tuple[str, ...],
    expected_code: str,
) -> None:
    document_one = next(item for item in legal_sources if item.logical_id == "DOC-01")
    mutated = _mutate_docx(
        document_one,
        replacements=replacements,
        append_paragraphs=append_paragraphs,
    )
    with pytest.raises(LegalDelegationValidationError) as exc_info:
        build_legal_delegation_review(
            _replace_source(legal_sources, "DOC-01", mutated)
        )
    assert exc_info.value.code == expected_code


def test_verifier_rejects_tampered_missing_duplicate_and_stale_fixed_outputs(
    legal_sources: tuple[LegalSourceInput, ...],
) -> None:
    build = build_legal_delegation_review(legal_sources)
    rows = list(csv.reader(io.StringIO(build.ledger_csv.decode("utf-8-sig"))))

    missing_output = io.StringIO()
    csv.writer(missing_output, lineterminator="\n").writerows(rows[:-1])
    missing_checks = verify_legal_delegation_artifacts(
        legal_sources,
        report_docx=build.report_docx,
        ledger_csv=("\ufeff" + missing_output.getvalue()).encode("utf-8"),
    )
    assert not all(check.passed for check in missing_checks)

    duplicate_output = io.StringIO()
    csv.writer(duplicate_output, lineterminator="\n").writerows([*rows, rows[-1]])
    duplicate_checks = verify_legal_delegation_artifacts(
        legal_sources,
        report_docx=build.report_docx,
        ledger_csv=("\ufeff" + duplicate_output.getvalue()).encode("utf-8"),
    )
    assert not all(check.passed for check in duplicate_checks)

    rows[1][10] = "篡改后的来源事实"
    tampered_output = io.StringIO()
    csv.writer(tampered_output, lineterminator="\n").writerows(rows)
    tampered_checks = verify_legal_delegation_artifacts(
        legal_sources,
        report_docx=build.report_docx,
        ledger_csv=("\ufeff" + tampered_output.getvalue()).encode("utf-8"),
    )
    assert not all(check.passed for check in tampered_checks)

    stale_report = _rewrite_docx_bytes(
        build.report_docx,
        replacements={
            "共 6 份文件：高风险 6 份、中风险 0 份、低风险 0 份、无已触发项 0 份；关键资料不足 11 项；可审查签署证据 0/6 份。": (
                "共 6 份文件：高风险 2 份、中风险 4 份、低风险 0 份、无已触发项 0 份；关键资料不足 11 项；可审查签署证据 0/6 份。"
            )
        },
    )
    stale_checks = verify_legal_delegation_artifacts(
        legal_sources,
        report_docx=stale_report,
        ledger_csv=build.ledger_csv,
    )
    assert not all(check.passed for check in stale_checks)
