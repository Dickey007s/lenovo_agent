"""Narrow source-derived numeric guard; no Artifact, business approval or write."""

from typing import Any

from services.api.app.application.office_narrative_facts import metric_discrepancies
from services.api.app.application.release_readiness_effect import (
    ReleaseReadinessValidationError, analyze_release_readiness,
)


RELEASE_FILES = frozenset({
    "PRD_v2.5.md", "上线配置清单.xlsx", "功能测试报告.xlsx", "线上兼容环境测试报告.xlsx",
})


class ReadonlySourceFactsError(ValueError):
    pass


def readonly_source_context(files: list[dict[str, Any]]) -> dict[str, Any] | None:
    sources = [item for item in files if item.get("display_group") == "产品管理"
               and item.get("display_label") in RELEASE_FILES]
    if {item["display_label"] for item in sources} != RELEASE_FILES:
        return None  # Partial bundles cannot establish whole-product counts.
    if len(sources) != len(RELEASE_FILES) or any(
        item.get("truncated") or (
            item.get("kind") == "table" and len(item.get("rows") or []) != item.get("total_rows")
        ) for item in sources
    ):
        raise ReadonlySourceFactsError("批准的上线资料不完整或重复，尚不能核对数字。")
    try:
        outcome = analyze_release_readiness({item["display_label"]: item for item in sources})
    except ReleaseReadinessValidationError as exc:
        raise ReadonlySourceFactsError("上线资料未通过固定来源合同，数字结论暂不采用。") from exc
    records = outcome.records
    return {
        "kind": "release_source_counts",
        "source_file_refs": [item["file_ref"] for item in sources],
        "counts": {
            "prd_features": len(records),
            "p0_features": sum(item.priority == "P0" for item in records),
            "configured_features": sum(item.configuration_status != "未列入配置清单" for item in records),
            "submitted_features": sum(item.configuration_status == "已提测" for item in records),
        },
        "p0_feature_ids": [item.record_id for item in records if item.priority == "P0"],
        "unsubmitted_feature_ids": [item.record_id for item in records if item.configuration_status != "已提测"],
        "gates": [item.model_dump(mode="json") for item in outcome.gates],
        "boundary": "仅固定来源计数和规则复算；不是原文引用、文件验证、语义验证或上线批准。",
    }


def readonly_numeric_error(context: dict[str, Any] | None, result: dict[str, Any]) -> str | None:
    if context is None:
        return None
    texts = [result.get("summary") or "", *result.get("follow_ups", [])]
    for finding in result.get("findings", []):
        texts.extend(str(finding.get(key) or "") for key in ("title", "detail", "fact_summary", "impact"))
    texts.extend(item.get("explanation") or "" for item in result.get("dependency_assessments", []))
    _, conflicts = metric_discrepancies("release_source_counts", context, "\n".join(texts))
    if not conflicts:
        return None
    labels = {"p0_features": "P0 功能数", "prd_features": "PRD 功能数",
              "configured_features": "配置清单功能数", "submitted_features": "已提测功能数"}
    details = "；".join(f"{labels.get(key, '上线指标')}应为 {expected}，候选为 {actual}"
                       for key, expected, actual in dict.fromkeys(conflicts))
    return "数字与批准来源不一致：" + details[:180] + "。本次说明未采用，其他成果保留。"
