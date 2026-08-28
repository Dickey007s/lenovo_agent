from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.customer_segmentation_effect import (
    CustomerSegmentationValidationError,
    CustomerSourceInput,
    analyze_customer_sources,
    build_customer_segmentation,
    verify_customer_artifacts,
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
def sources(catalog: BenchmarkWorkspaceCatalog) -> tuple[CustomerSourceInput, ...]:
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-13")
    return ScenarioEffectEngine._customer_source_inputs(catalog, spec)


def _source(
    sources: tuple[CustomerSourceInput, ...], logical_id: str
) -> CustomerSourceInput:
    return next(item for item in sources if item.logical_id == logical_id)


def _replace_source(
    sources: tuple[CustomerSourceInput, ...], replacement: CustomerSourceInput
) -> tuple[CustomerSourceInput, ...]:
    return tuple(
        replacement if item.logical_id == replacement.logical_id else item for item in sources
    )


def _mutated_source(source: CustomerSourceInput, content: bytes) -> CustomerSourceInput:
    return replace(source, content=content, declared_size=len(content))


def _decode_csv(source: CustomerSourceInput) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return source.content.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise AssertionError("fixture CSV encoding is unsupported")


def _replace_csv(
    sources: tuple[CustomerSourceInput, ...], old: str, new: str, *, count: int = 1
) -> tuple[CustomerSourceInput, ...]:
    source = _source(sources, "sales-020-survey")
    text, encoding = _decode_csv(source)
    assert old in text
    content = text.replace(old, new, count).encode(encoding)
    return _replace_source(sources, _mutated_source(source, content))


def _append_csv_row(
    sources: tuple[CustomerSourceInput, ...], row: str
) -> tuple[CustomerSourceInput, ...]:
    source = _source(sources, "sales-020-survey")
    text, encoding = _decode_csv(source)
    content = (text.rstrip("\r\n") + "\n" + row + "\n").encode(encoding)
    return _replace_source(sources, _mutated_source(source, content))


def _replace_rule(
    sources: tuple[CustomerSourceInput, ...], old: str, new: str, *, count: int = 1
) -> tuple[CustomerSourceInput, ...]:
    source = _source(sources, "sales-020-rules")
    text = source.content.decode("utf-8-sig")
    assert old in text
    content = text.replace(old, new, count).encode("utf-8")
    return _replace_source(sources, _mutated_source(source, content))


def _sample(outcome, sample_id: str):
    return next(item for item in outcome.samples if item.sample_id == sample_id)


def test_canonical_sources_build_two_independently_verified_artifacts(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    build = build_customer_segmentation(sources)
    outcome = build.analysis.outcome

    assert (
        outcome.source_row_count,
        outcome.unique_payload_count,
        outcome.duplicate_count,
        outcome.classified_count,
        outcome.unclassified_count,
        outcome.excluded_count,
    ) == (11, 10, 1, 8, 2, 3)
    assert outcome.profile_counts == {"技术型": 3, "安全型": 3, "敏捷型": 2}
    assert outcome.priority_witness_count == 0
    assert outcome.parameters.missing_score_default == 0
    assert outcome.parameters.profile_thresholds == {
        "技术型": 8,
        "安全型": 8,
        "敏捷型": 8,
    }
    assert outcome.parameters.profile_priority == ["安全型", "技术型", "敏捷型"]
    assert len(outcome.rules) == 15
    assert all(item.passed for item in build.checks)
    assert len(build.checks) == 7
    assert len(build.ledger_csv.decode("utf-8-sig").splitlines()) == 12
    report = build.report_markdown.decode("utf-8")
    assert "多标签优先级 witness：0" in report
    assert "exact_non_id_payload" in report
    assert "待销售负责人基于已批准产品资料补充并确认" in report
    assert "私有化部署" not in report
    assert "模板市场" not in report
    assert "没有联系客户、写 CRM、创建商机或触发营销动作" in report


def test_threshold_mutation_recomputes_labels_without_fixed_sample_sets(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    mutated_sources = _replace_rule(
        sources,
        "1. 技术型：专业(Stech)字段数值≥8的客户",
        "1. 技术型：专业(Stech)字段数值≥9的客户",
    )
    build = build_customer_segmentation(mutated_sources)
    outcome = build.analysis.outcome

    assert outcome.parameters.profile_thresholds["技术型"] == 9
    assert outcome.profile_counts == {"技术型": 2, "安全型": 3, "敏捷型": 2}
    assert outcome.classified_count == 7
    assert outcome.unclassified_count == 3
    assert _sample(outcome, "104").final_label is None
    assert _sample(outcome, "104").exclusion_reason == "unclassified"
    assert all(item.passed for item in build.checks)


def test_priority_is_proven_by_a_real_multilabel_witness_and_can_be_reordered(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    with_witness = _append_csv_row(
        sources,
        "112,制造业,100-500人,技术负责人,9,9,9,9",
    )
    canonical_priority = analyze_customer_sources(with_witness).outcome
    assert canonical_priority.priority_witness_count == 1
    assert _sample(canonical_priority, "112").matched_profiles == [
        "安全型",
        "技术型",
        "敏捷型",
    ]
    assert _sample(canonical_priority, "112").final_label == "安全型"

    reordered = _replace_rule(
        with_witness,
        "`安全型 > 技术型 > 敏捷型`",
        "`技术型 > 安全型 > 敏捷型`",
    )
    reordered_outcome = build_customer_segmentation(reordered).analysis.outcome
    assert reordered_outcome.parameters.profile_priority == ["技术型", "安全型", "敏捷型"]
    assert _sample(reordered_outcome, "112").matched_profiles == [
        "技术型",
        "安全型",
        "敏捷型",
    ]
    assert _sample(reordered_outcome, "112").final_label == "技术型"


def test_missing_default_and_legal_new_sample_are_source_driven(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    new_sample = _append_csv_row(sources, "112,制造业,100-500人,运营负责人,,1,1,1")
    baseline = analyze_customer_sources(new_sample).outcome
    assert _sample(baseline, "112").cleaned_scores["tech"] == 0
    assert _sample(baseline, "112").final_label is None

    changed = _replace_rule(
        new_sample,
        "3. 缺失的评分字段统一按数值0处理",
        "3. 缺失的评分字段统一按数值8处理",
    )
    outcome = build_customer_segmentation(changed).analysis.outcome
    sample = _sample(outcome, "112")
    assert outcome.source_row_count == 12
    assert outcome.parameters.missing_score_default == 8
    assert sample.cleaned_scores["tech"] == 8
    assert sample.transformations == ["tech:空→8"]
    assert sample.final_label == "技术型"


def test_id_and_descriptive_fields_are_not_fixed_business_answers(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    renamed = _replace_csv(sources, "101,金融科技,500-1000人", "901,金融科技,500-1000人")
    outcome = build_customer_segmentation(renamed).analysis.outcome
    changed = _sample(outcome, "901")

    assert changed.industry == "金融科技"
    assert changed.company_size == "500-1000人"
    assert changed.final_label == "技术型"
    assert all(sample.sample_id != "101" for sample in outcome.samples)
    assert outcome.profile_counts == {"技术型": 3, "安全型": 3, "敏捷型": 2}


def test_exact_payload_duplicate_keeps_first_and_exposes_policy_assumption(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    outcome = analyze_customer_sources(sources).outcome
    duplicate = _sample(outcome, "111")

    assert duplicate.duplicate_of == "101"
    assert duplicate.final_label is None
    assert duplicate.exclusion_reason == "exact_duplicate"
    assert outcome.duplicate_policy_assumption == "exact_non_id_payload"
    assert outcome.policy_assumption_review_required is True


@pytest.mark.parametrize(
    ("mutator", "error_code"),
    [
        (lambda items: items[:-1], "source-count"),
        (
            lambda items: (*items, replace(items[-1], logical_id="sales-020-extra")),
            "source-count",
        ),
        (
            lambda items: (items[0], replace(items[1], logical_id=items[0].logical_id)),
            "duplicate-logical-id",
        ),
        (lambda items: tuple(reversed(items)), "source-order"),
        (lambda items: (replace(items[0], allowlist_verified=False), items[1]), "allowlist"),
        (lambda items: (replace(items[0], file_name="other.csv"), items[1]), "file-name"),
        (
            lambda items: (replace(items[0], display_path="销售运营/other.csv"), items[1]),
            "display-path",
        ),
        (lambda items: (replace(items[0], file_ref="forte-wrong"), items[1]), "file-ref"),
        (lambda items: (replace(items[0], content=b"", declared_size=0), items[1]), "empty-source"),
        (lambda items: (replace(items[0], declared_size=1), items[1]), "declared-size"),
        (
            lambda items: (
                replace(items[0], content=items[1].content, declared_size=len(items[1].content)),
                items[1],
            ),
            "same-content",
        ),
    ],
)
def test_source_bundle_failures_are_closed(
    sources: tuple[CustomerSourceInput, ...], mutator, error_code: str
) -> None:
    with pytest.raises(CustomerSegmentationValidationError) as captured:
        analyze_customer_sources(tuple(mutator(sources)))
    assert captured.value.code == error_code


@pytest.mark.parametrize(
    ("old", "new", "error_code"),
    [
        ("样本ID,企业所在行业", "样本ID,样本ID", "csv-header"),
        ("101,金融科技", "101", "csv-column-count"),
        ("101,金融科技", "102,金融科技", "duplicate-sample-id"),
        ("101,金融科技,500-1000人,技术架构师,9", "101,金融科技,500-1000人,技术架构师,=9", "csv-injection"),
        ("101,金融科技,500-1000人,技术架构师,9", "101,金融科技,500-1000人,技术架构师,十一", "score-format"),
        ("101,金融科技,500-1000人,技术架构师,9", "101,金融科技,500-1000人,技术架构师,11", "score-range"),
        ("101,金融科技,500-1000人,技术架构师,9", "101,金融科技,500-1000人,技术架构师,9.5", "score-format"),
    ],
)
def test_invalid_csv_values_fail_closed(
    sources: tuple[CustomerSourceInput, ...], old: str, new: str, error_code: str
) -> None:
    mutated = _replace_csv(sources, old, new)
    with pytest.raises(CustomerSegmentationValidationError) as captured:
        analyze_customer_sources(mutated)
    assert captured.value.code == error_code


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("\n4. 行业型：行业字段匹配时必须分类\n", "unknown-rule"),
        ("\n4. 必须自动创建 CRM 商机\n", "unknown-rule"),
        (
            "\n1. 技术型：专业(Stech)字段数值≥8的客户\n",
            "duplicate-rule",
        ),
    ],
)
def test_unknown_fourth_profile_or_duplicate_rules_fail_closed(
    sources: tuple[CustomerSourceInput, ...], mutation: str, error_code: str
) -> None:
    source = _source(sources, "sales-020-rules")
    mutated = _replace_source(
        sources,
        _mutated_source(source, source.content + mutation.encode("utf-8")),
    )
    with pytest.raises(CustomerSegmentationValidationError) as captured:
        analyze_customer_sources(mutated)
    assert captured.value.code == error_code


def test_empty_corrupt_and_truncated_inputs_fail_closed(
    sources: tuple[CustomerSourceInput, ...],
) -> None:
    survey = _source(sources, "sales-020-survey")
    rules = _source(sources, "sales-020-rules")
    variants = (
        (_replace_source(sources, _mutated_source(survey, b"a,b\n")), "csv-empty"),
        (_replace_source(sources, _mutated_source(survey, b"\xff\xfe\x00")), "csv-encoding"),
        (_replace_source(sources, _mutated_source(rules, b"\xff\xfe")), "rule-encoding"),
        (_replace_source(sources, _mutated_source(rules, b"# truncated")), "unknown-rule"),
    )
    for mutated, error_code in variants:
        with pytest.raises(CustomerSegmentationValidationError) as captured:
            analyze_customer_sources(mutated)
        assert captured.value.code == error_code


@pytest.mark.parametrize(
    ("artifact", "old", "new"),
    [
        ("report", "多标签优先级 witness：0", "多标签优先级 witness：9"),
        ("report", "no_approved_strategy_source", "approved_strategy"),
        ("ledger", "客户画像调研问卷.csv:row=2", "客户画像调研问卷.csv:row=999"),
        ("ledger", ",技术型,", ",安全型,"),
        ("ledger", "SEG-PROFILE-TECH", "SEG-PROFILE-UNKNOWN"),
    ],
)
def test_output_tampering_cannot_self_verify(
    sources: tuple[CustomerSourceInput, ...], artifact: str, old: str, new: str
) -> None:
    build = build_customer_segmentation(sources)
    report = build.report_markdown
    ledger = build.ledger_csv
    if artifact == "report":
        text = report.decode("utf-8")
        assert old in text
        report = text.replace(old, new, 1).encode("utf-8")
    else:
        text = ledger.decode("utf-8-sig")
        assert old in text
        ledger = text.replace(old, new, 1).encode("utf-8-sig")

    checks = verify_customer_artifacts(
        sources,
        report_markdown=report,
        ledger_csv=ledger,
    )
    assert any(not item.passed for item in checks)
    assert next(item for item in checks if item.check_id == "check-customer-canonical-bytes-v2").passed is False
