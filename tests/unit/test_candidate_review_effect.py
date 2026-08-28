from __future__ import annotations

import io
import zipfile
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from services.api.app.application import candidate_review_effect as candidate_effect
from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.candidate_review_effect import (
    CandidateReviewValidationError,
    CandidateSourceInput,
    SourceLine,
    analyze_candidate_review_sources,
    build_candidate_review,
    verify_candidate_review_artifacts,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"


@pytest.fixture(scope="module")
def catalog() -> BenchmarkWorkspaceCatalog:
    return BenchmarkWorkspaceCatalog(FORTE_ROOT)


@pytest.fixture(scope="module")
def sources(catalog: BenchmarkWorkspaceCatalog) -> tuple[CandidateSourceInput, ...]:
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-06")
    return ScenarioEffectEngine._candidate_source_inputs(catalog, spec)


def _source_by_id(
    sources: tuple[CandidateSourceInput, ...], logical_id: str
) -> CandidateSourceInput:
    return next(item for item in sources if item.logical_id == logical_id)


def _replace_source(
    sources: tuple[CandidateSourceInput, ...], replacement: CandidateSourceInput
) -> tuple[CandidateSourceInput, ...]:
    return tuple(
        replacement if item.logical_id == replacement.logical_id else item for item in sources
    )


def _replace_docx_text(content: bytes, old: str, new: str) -> bytes:
    source = io.BytesIO(content)
    output = io.BytesIO()
    with (
        zipfile.ZipFile(source) as archive,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        replaced = False
        for info in archive.infolist():
            data = archive.read(info.filename)
            if info.filename == "word/document.xml":
                root = ET.fromstring(data)
                for paragraph in root.iter(f"{candidate_effect.W}p"):
                    text_nodes = list(paragraph.iter(f"{candidate_effect.W}t"))
                    paragraph_text = "".join(node.text or "" for node in text_nodes)
                    if old not in paragraph_text:
                        continue
                    replacement = paragraph_text.replace(old, new, 1)
                    text_nodes[0].text = replacement
                    for node in text_nodes[1:]:
                        node.text = ""
                    data = ET.tostring(
                        root, encoding="utf-8", xml_declaration=True
                    )
                    replaced = True
                    break
            target.writestr(info, data)
    assert replaced
    return output.getvalue()


def _append_ascii_pdf_page(content: bytes, line: str) -> bytes:
    writer = PdfWriter(clone_from=io.BytesIO(content))
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    font_ref = writer._add_object(font)
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
    )
    stream = DecodedStreamObject()
    escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream.set_data(f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii"))
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    assert line in (PdfReader(io.BytesIO(output.getvalue())).pages[-1].extract_text() or "")
    return output.getvalue()


def _mutated_source(source: CandidateSourceInput, content: bytes) -> CandidateSourceInput:
    return replace(source, content=content, declared_size=len(content))


def _review(outcome, role_id: str, candidate_name: str):
    return next(
        item
        for item in outcome.reviews
        if item.role_id == role_id and item.candidate_name == candidate_name
    )


def _assessment(outcome, role_id: str, candidate_name: str, condition_id: str):
    review = _review(outcome, role_id, candidate_name)
    return next(item for item in review.assessments if item.condition_id == condition_id)


def test_canonical_sources_build_three_recomputed_private_artifacts(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    build = build_candidate_review(sources)
    outcome = build.analysis.outcome

    assert outcome.assessment_count == 110
    assert (
        outcome.met_count,
        outcome.not_met_count,
        outcome.unverifiable_count,
        outcome.human_exception_count,
    ) == (32, 6, 71, 1)
    assert all(item.passed for item in build.checks)
    assert len(build.ledger_csv.decode("utf-8-sig").splitlines()) == 111
    assert build.report_table_counts == (8, 8)
    assert (
        _assessment(outcome, "merchant_bd", "王琳达", "BD-EDUCATION").status
        == "human_exception_required"
    )
    assert (
        _review(outcome, "text_evaluation", "周伦").recommendation == "recommended_for_human_review"
    )
    assert (
        _assessment(outcome, "text_evaluation", "孙博文", "TEXT-REQ-AI-EXPERIENCE").status
        == "not_met"
    )
    assert (
        _assessment(outcome, "text_evaluation", "李雨桐", "TEXT-REQ-PYTHON").status
        == "unverifiable"
    )
    assert _assessment(outcome, "text_evaluation", "赵晨曦", "TEXT-REQ-PYTHON").status == "not_met"
    rendered = "\n".join(
        (
            build.ledger_csv.decode("utf-8-sig"),
            candidate_effect._parse_generated_docx(build.bd_report_docx)[1],
            candidate_effect._parse_generated_docx(build.text_report_docx)[1],
        )
    )
    assert "@" not in rendered
    assert "手机号" not in rendered
    assert "不是录用或淘汰决定" in rendered
    assert "不能声称无偏" in rendered


@pytest.mark.parametrize(
    ("mutator", "error_code"),
    [
        (lambda items: items[:-1], "source-count"),
        (
            lambda items: (*items, replace(items[-1], logical_id="CAND-99")),
            "source-count",
        ),
        (
            lambda items: (items[0], replace(items[1], logical_id=items[0].logical_id), *items[2:]),
            "duplicate-logical-id",
        ),
        (
            lambda items: (
                items[0],
                items[1],
                replace(items[2], content=items[3].content, declared_size=len(items[3].content)),
                items[3],
                *items[4:],
            ),
            "duplicate-source-content",
        ),
    ],
)
def test_source_set_failures_are_closed(
    sources: tuple[CandidateSourceInput, ...], mutator, error_code: str
) -> None:
    with pytest.raises(CandidateReviewValidationError) as captured:
        analyze_candidate_review_sources(tuple(mutator(sources)))
    assert captured.value.code == error_code


def test_swapped_resume_bytes_cannot_borrow_another_candidate_identity(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    first = _source_by_id(sources, "CAND-01")
    second = _source_by_id(sources, "CAND-02")
    swapped = _replace_source(
        _replace_source(
            sources,
            _mutated_source(first, second.content),
        ),
        _mutated_source(second, first.content),
    )
    with pytest.raises(CandidateReviewValidationError) as captured:
        analyze_candidate_review_sources(swapped)
    assert captured.value.code == "candidate-name-mismatch"


@pytest.mark.parametrize(
    ("logical_id", "content", "error_code"),
    [
        ("JD-BD", b"not-a-docx", "jd-docx-container"),
        ("CAND-03", b"not-a-pdf", "resume-pdf-parse"),
        ("CAND-04", b"", "source-size"),
    ],
)
def test_empty_or_corrupt_office_sources_fail_closed(
    sources: tuple[CandidateSourceInput, ...],
    logical_id: str,
    content: bytes,
    error_code: str,
) -> None:
    source = _source_by_id(sources, logical_id)
    mutated = _replace_source(sources, _mutated_source(source, content))
    with pytest.raises(CandidateReviewValidationError) as captured:
        analyze_candidate_review_sources(mutated)
    assert captured.value.code == error_code


def test_sun_ai_experience_raw_pdf_mutation_changes_only_target_text_review(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    baseline = analyze_candidate_review_sources(sources).outcome
    source = _source_by_id(sources, "CAND-02")
    content = _append_ascii_pdf_page(
        source.content,
        "2024.01 - 2024.08 AI evaluation engineer (8 months)",
    )
    mutated = analyze_candidate_review_sources(
        _replace_source(sources, _mutated_source(source, content))
    ).outcome

    assert (
        _assessment(baseline, "text_evaluation", "孙博文", "TEXT-REQ-AI-EXPERIENCE").status
        == "not_met"
    )
    changed = _assessment(mutated, "text_evaluation", "孙博文", "TEXT-REQ-AI-EXPERIENCE")
    assert changed.status == "met"
    assert "16 个月" in changed.fact
    assert (
        _review(mutated, "text_evaluation", "孙博文").recommendation
        == "recommended_for_human_review"
    )
    baseline_other = [
        item.model_dump()
        for item in baseline.reviews
        if not (item.role_id == "text_evaluation" and item.candidate_name == "孙博文")
    ]
    mutated_other = [
        item.model_dump()
        for item in mutated.reviews
        if not (item.role_id == "text_evaluation" and item.candidate_name == "孙博文")
    ]
    assert baseline_other == mutated_other


@pytest.mark.parametrize(
    ("threshold", "sun_status", "zhou_status"),
    [("6 个月以上", "met", "met"), ("2 年以上", "not_met", "not_met")],
)
def test_jd_threshold_mutation_dynamically_changes_matching_results(
    sources: tuple[CandidateSourceInput, ...],
    threshold: str,
    sun_status: str,
    zhou_status: str,
) -> None:
    source = _source_by_id(sources, "JD-TEXT")
    content = _replace_docx_text(source.content, "1 年以上", threshold)
    outcome = analyze_candidate_review_sources(
        _replace_source(sources, _mutated_source(source, content))
    ).outcome

    assert (
        _assessment(outcome, "text_evaluation", "孙博文", "TEXT-REQ-AI-EXPERIENCE").status
        == sun_status
    )
    assert (
        _assessment(outcome, "text_evaluation", "周伦", "TEXT-REQ-AI-EXPERIENCE").status
        == zhou_status
    )
    assert [item.model_dump() for item in outcome.reviews if item.role_id == "merchant_bd"] == [
        item.model_dump()
        for item in analyze_candidate_review_sources(sources).outcome.reviews
        if item.role_id == "merchant_bd"
    ]


def test_removing_bd_exception_changes_wang_from_exception_to_explicit_gap(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    source = _source_by_id(sources, "JD-BD")
    content = _replace_docx_text(source.content, "（优秀者可放宽）", "")
    outcome = analyze_candidate_review_sources(
        _replace_source(sources, _mutated_source(source, content))
    ).outcome

    assert _assessment(outcome, "merchant_bd", "王琳达", "BD-EDUCATION").status == "not_met"
    assert _review(outcome, "merchant_bd", "王琳达").recommendation == "explicit_hard_gap"


def test_conflicting_ai_none_and_dated_experience_fails_closed(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    source = _source_by_id(sources, "CAND-01")
    content = _append_ascii_pdf_page(source.content, "AI experience: none")
    with pytest.raises(CandidateReviewValidationError) as captured:
        analyze_candidate_review_sources(_replace_source(sources, _mutated_source(source, content)))
    assert captured.value.code == "candidate-ai-experience-conflict"


@pytest.mark.parametrize(
    ("line", "error_code"),
    [
        ("2024.12 - 2024.01 AI evaluation engineer (2 months)", "candidate-date-order"),
        (
            "2024.01 - 2024.08 AI evaluation engineer (12 months)",
            "candidate-duration-conflict",
        ),
    ],
)
def test_illegal_or_conflicting_resume_dates_fail_closed(
    sources: tuple[CandidateSourceInput, ...], line: str, error_code: str
) -> None:
    source = _source_by_id(sources, "CAND-03")
    content = _append_ascii_pdf_page(source.content, line)
    with pytest.raises(CandidateReviewValidationError) as captured:
        analyze_candidate_review_sources(_replace_source(sources, _mutated_source(source, content)))
    assert captured.value.code == error_code


def test_safe_extracted_source_mutation_removing_li_bd_facts_is_isolated(
    sources: tuple[CandidateSourceInput, ...], monkeypatch: pytest.MonkeyPatch
) -> None:
    baseline = analyze_candidate_review_sources(sources).outcome
    original_extract = candidate_effect._extract_pdf_lines
    bd_terms = {
        term
        for key, patterns in candidate_effect.POSITIVE_PATTERNS.items()
        if key
        not in {
            "python_data",
            "ai_experience",
            "frontend",
            "llm_evaluation",
            "english_reading",
            "dataset_work",
            "tool_development",
            "rubric_evaluation",
        }
        for pattern in patterns
        for term in pattern
    }

    def without_li_bd_facts(source: CandidateSourceInput) -> tuple[SourceLine, ...]:
        lines = original_extract(source)
        if source.logical_id != "CAND-03":
            return lines
        return tuple(
            line
            for line in lines
            if not any(term.lower() in line.text.lower() for term in bd_terms)
        )

    monkeypatch.setattr(candidate_effect, "_extract_pdf_lines", without_li_bd_facts)
    mutated = analyze_candidate_review_sources(sources).outcome
    assert (
        _review(mutated, "merchant_bd", "李雨桐").met_count
        < _review(baseline, "merchant_bd", "李雨桐").met_count
    )
    assert (
        _review(mutated, "text_evaluation", "李雨桐").model_dump()
        == _review(baseline, "text_evaluation", "李雨桐").model_dump()
    )
    baseline_other = [
        item.model_dump() for item in baseline.reviews if item.candidate_name != "李雨桐"
    ]
    mutated_other = [
        item.model_dump() for item in mutated.reviews if item.candidate_name != "李雨桐"
    ]
    assert baseline_other == mutated_other


def test_verifier_rejects_tampered_missing_duplicate_and_private_ledger_rows(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    build = build_candidate_review(sources)
    text = build.ledger_csv.decode("utf-8-sig")
    header, first, *rest = text.splitlines()
    variants = {
        "tampered": "\ufeff" + text.replace("资料不足", "明确不满足", 1),
        "missing": "\ufeff" + "\n".join([header, *rest]) + "\n",
        "duplicate": "\ufeff" + "\n".join([header, first, first, *rest]) + "\n",
        "private": "\ufeff" + text + "招聘邮箱,hr@example.com\n",
    }
    for name, value in variants.items():
        checks = verify_candidate_review_artifacts(
            sources,
            bd_report_docx=build.bd_report_docx,
            text_report_docx=build.text_report_docx,
            ledger_csv=value.encode("utf-8"),
        )
        assert not all(item.passed for item in checks), name
    privacy_checks = verify_candidate_review_artifacts(
        sources,
        bd_report_docx=build.bd_report_docx,
        text_report_docx=build.text_report_docx,
        ledger_csv=variants["private"].encode("utf-8"),
    )
    assert not next(
        item for item in privacy_checks if item.check_id == "check-candidate-privacy-boundary"
    ).passed


@pytest.mark.parametrize(
    "private_value",
    (
        "hr@example.com",
        "13800138000",
        "家庭住址：北京市朝阳区",
        "性别：女",
        "年龄：29",
        "民族：汉族",
        "婚姻状况：已婚",
        "候选人照片",
    ),
)
def test_verifier_rejects_nonessential_private_or_population_attributes(
    sources: tuple[CandidateSourceInput, ...], private_value: str
) -> None:
    build = build_candidate_review(sources)
    polluted = build.ledger_csv + f"\n{private_value}".encode("utf-8")
    checks = verify_candidate_review_artifacts(
        sources,
        bd_report_docx=build.bd_report_docx,
        text_report_docx=build.text_report_docx,
        ledger_csv=polluted,
    )
    assert not next(
        item for item in checks if item.check_id == "check-candidate-privacy-boundary"
    ).passed


def test_verifier_rejects_a_report_replaced_by_old_fixed_summary(
    sources: tuple[CandidateSourceInput, ...],
) -> None:
    build = build_candidate_review(sources)
    old_report = candidate_effect._docx_bytes(
        [
            ("title", "外卖商户BD岗位辅助筛选报告"),
            ("body", "通过 1 人，不通过 4 人。"),
            ("body", "这是旧的固定名单，不包含逐条件来源。"),
        ]
    )
    checks = verify_candidate_review_artifacts(
        sources,
        bd_report_docx=old_report,
        text_report_docx=build.text_report_docx,
        ledger_csv=build.ledger_csv,
    )
    assert not next(item for item in checks if item.check_id == "check-candidate-reports").passed
