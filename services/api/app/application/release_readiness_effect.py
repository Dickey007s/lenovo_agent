"""Strict, source-derived release readiness ledger for the fixed pm-014 corpus."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from dataclasses import dataclass
from typing import Any
from xml.sax.saxutils import escape

from packages.contracts.harness_models import (
    AgentControlLoopBusinessGate,
    AgentControlLoopBusinessGateOutcome,
    AgentControlLoopBusinessMetric,
    AgentControlLoopBusinessRecord,
)


class ReleaseReadinessValidationError(ValueError):
    """The four source documents do not satisfy the fixed adapter contract."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SourceRow:
    row_number: int
    values: tuple[str, ...]


@dataclass(frozen=True)
class PrdFeature:
    code: str
    name: str
    module: str
    priority: str
    owner: str
    line_number: int


@dataclass(frozen=True)
class ReleaseReadinessBuild:
    report_docx: bytes
    ledger_csv: bytes
    outcome: AgentControlLoopBusinessGateOutcome
    risk_counts: dict[str, int]
    missing_feature_codes: tuple[str, ...]
    docx_table_count: int


CONFIG_HEADERS = (
    "功能编号",
    "功能名称",
    "所属模块",
    "优先级",
    "开发负责人",
    "提测日期",
    "代码分支",
    "提测状态",
)
TEST_HEADERS = (
    "功能编号",
    "功能名称",
    "所属模块",
    "优先级",
    "测试负责人",
    "测试开始",
    "测试完成",
    "用例总数",
    "通过数",
    "测试结论",
    "不通过原因类型",
    "不通过原因描述",
)
COMPATIBILITY_PREFIX_HEADERS = ("功能编号", "功能名称", "所属模块", "优先级")
CONFIG_STATUSES = frozenset({"已提测", "待提测", "未提测"})
TEST_CONCLUSIONS = frozenset({"通过", "有条件通过", "不通过", "待测"})
COMPATIBILITY_STATUSES = frozenset({"通过", "部分通过", "兼容问题"})
NO_ISSUE_VALUES = frozenset({"", "-", "—", "无", "不适用"})
RISK_ORDER = {"none": 0, "minor": 1, "major": 2, "severe": 3}
RISK_LABELS = {"none": "无", "minor": "次要", "major": "主要", "severe": "严重"}


def build_release_readiness(
    previews: dict[str, dict[str, Any]],
) -> ReleaseReadinessBuild:
    prd_text = str(previews.get("PRD_v2.5.md", {}).get("text") or "")
    features = _parse_prd_features(prd_text)
    rules = _parse_prd_rules(prd_text)
    config_rows = _parse_single_header_table(
        previews.get("上线配置清单.xlsx"),
        CONFIG_HEADERS,
        expected_count=13,
        label="上线配置清单.xlsx",
    )
    test_rows = _parse_single_header_table(
        previews.get("功能测试报告.xlsx"),
        TEST_HEADERS,
        expected_count=13,
        label="功能测试报告.xlsx",
    )
    compatibility_rows, environments = _parse_compatibility_table(
        previews.get("线上兼容环境测试报告.xlsx")
    )

    prd_by_code = _unique_map(
        features,
        key=lambda item: item.code,
        label="PRD 功能编号",
    )
    config_by_code = _validated_feature_rows(
        config_rows, prd_by_code, "上线配置清单.xlsx"
    )
    test_by_code = _validated_feature_rows(
        test_rows, prd_by_code, "功能测试报告.xlsx"
    )
    compatibility_by_code = _validated_feature_rows(
        compatibility_rows, prd_by_code, "线上兼容环境测试报告.xlsx"
    )
    if set(config_by_code) != set(test_by_code) or set(config_by_code) != set(
        compatibility_by_code
    ):
        raise ReleaseReadinessValidationError(
            "cross-table-feature-set",
            "上线配置、功能测试和兼容测试的 13 个功能编号集合不一致。",
        )

    _validate_config_rows(config_rows)
    _validate_test_rows(test_rows, rules["reason_levels"])
    _validate_compatibility_rows(compatibility_rows, environments)

    gates = _build_gates(
        features,
        config_by_code,
        test_by_code,
        rules,
    )
    metrics = _build_auxiliary_metrics(features, test_by_code)
    records = _build_records(
        features,
        config_by_code,
        test_by_code,
        compatibility_by_code,
        environments,
        rules,
    )
    severe_count = sum(record.final_risk_level == "severe" for record in records)
    gates = [
        gate.model_copy(
            update={
                "numerator": float(severe_count),
                "actual": float(severe_count),
                "passed": severe_count == 0,
                "result": (
                    "0 项严重问题，满足清零条件。"
                    if severe_count == 0
                    else f"{severe_count} 项严重问题未清零，不满足上线条件。"
                ),
            }
        )
        if gate.gate_id == "business-gate-severe-zero"
        else gate
        for gate in gates
    ]
    failed_gate_count = sum(not gate.passed for gate in gates)
    status = "passed" if failed_gate_count == 0 else "failed"
    decision = "可以进入人工上线审批" if status == "passed" else "不得上线"
    outcome = AgentControlLoopBusinessGateOutcome(
        outcome_id="business-outcome-release-readiness",
        status=status,
        decision=decision,
        summary=(
            "4 条正式上线条件全部满足；仍需发布负责人进行最终人工审批。"
            if status == "passed"
            else f"{failed_gate_count}/{len(gates)} 条正式上线条件未通过；确定性检查通过不等于可以上线。"
        ),
        total_gate_count=len(gates),
        failed_gate_count=failed_gate_count,
        gates=gates,
        auxiliary_metrics=metrics,
        records=records,
    )
    missing_codes = tuple(
        record.record_id
        for record in records
        if record.configuration_status != "已提测"
    )
    risk_counts = {
        level: sum(record.final_risk_level == level for record in records)
        for level in ("severe", "major", "minor")
    }
    ledger_csv = _ledger_csv(records)
    report_docx, table_count = _report_docx(
        outcome,
        risk_counts=risk_counts,
        missing_codes=missing_codes,
    )
    return ReleaseReadinessBuild(
        report_docx=report_docx,
        ledger_csv=ledger_csv,
        outcome=outcome,
        risk_counts=risk_counts,
        missing_feature_codes=missing_codes,
        docx_table_count=table_count,
    )


def invalid_release_outcome(detail: str) -> AgentControlLoopBusinessGateOutcome:
    return AgentControlLoopBusinessGateOutcome(
        outcome_id="business-outcome-release-readiness",
        status="invalid",
        decision="无法形成上线结论",
        summary=f"四份来源未通过数据合同校验：{detail}",
        total_gate_count=0,
        failed_gate_count=0,
        gates=[],
        auxiliary_metrics=[],
        records=[],
    )


def _parse_prd_features(text: str) -> list[PrdFeature]:
    if not text:
        raise ReleaseReadinessValidationError("prd-empty", "PRD_v2.5.md 为空。")
    features: list[PrdFeature] = []
    current_module = ""
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        heading = re.match(r"^##\s+[一二三四五六七八九十]+、(.+模块)\s*$", raw_line.strip())
        if heading:
            current_module = heading.group(1).strip()
            continue
        if not re.match(r"^\|\s*F\d+\s*\|", raw_line):
            continue
        cells = tuple(cell.strip() for cell in raw_line.strip().strip("|").split("|"))
        if len(cells) != 6:
            raise ReleaseReadinessValidationError(
                "prd-feature-shape",
                f"PRD 第 {line_number} 行功能表列数不是 6。",
            )
        code, name, _description, priority, owner, _date = cells
        if not current_module:
            raise ReleaseReadinessValidationError(
                "prd-module-missing", f"PRD 第 {line_number} 行未归属模块。"
            )
        if not re.fullmatch(r"F\d{2}", code) or priority not in {"P0", "P1", "P2", "P3"}:
            raise ReleaseReadinessValidationError(
                "prd-feature-invalid",
                f"PRD 第 {line_number} 行功能编号或优先级无效。",
            )
        if not name or not owner:
            raise ReleaseReadinessValidationError(
                "prd-feature-required", f"PRD 第 {line_number} 行缺少功能名称或负责人。"
            )
        features.append(
            PrdFeature(code, name, current_module, priority, owner, line_number)
        )
    if len(features) != 18:
        raise ReleaseReadinessValidationError(
            "prd-feature-count", f"PRD 应有 18 项功能，实际解析到 {len(features)} 项。"
        )
    _unique_map(features, key=lambda item: item.code, label="PRD 功能编号")
    return features


def _parse_prd_rules(text: str) -> dict[str, Any]:
    required_fragments = (
        "P0 功能提测率",
        "P0 功能测试通过率",
        "P1 功能完成率",
        "以上条件须**同时满足**",
        "P0 功能问题一律为「严重」",
        "同一功能仅纳入一类风险等级",
    )
    missing = [fragment for fragment in required_fragments if fragment not in text]
    if missing:
        raise ReleaseReadinessValidationError(
            "prd-rule-missing", "PRD 缺少规则：" + "、".join(missing)
        )
    p0_tested = re.search(r"\|\s*P0 功能提测率\s*\|\s*(\d+(?:\.\d+)?)%", text)
    p0_accepted = re.search(r"\|\s*P0 功能测试通过率\s*\|\s*(\d+(?:\.\d+)?)%", text)
    p1_passed = re.search(r"\|\s*P1 功能完成率\s*\|\s*[≥>=]+\s*(\d+(?:\.\d+)?)%", text)
    compat_threshold = re.search(r"(\d+)\s*个及以上[^\n]+升级为严重", text)
    if not all((p0_tested, p0_accepted, p1_passed, compat_threshold)):
        raise ReleaseReadinessValidationError(
            "prd-threshold-invalid", "PRD 的上线或兼容升级阈值无法解析。"
        )
    reason_levels: dict[str, str] = {}
    for raw_line in text.splitlines():
        if not raw_line.startswith("|"):
            continue
        cells = [cell.strip() for cell in raw_line.strip().strip("|").split("|")]
        if len(cells) != 3:
            continue
        reason, level_text, _description = cells
        if reason in {"功能缺陷", "性能问题", "数据一致性问题", "依赖异常"}:
            reason_levels[reason] = "major"
        elif reason in {"界面缺陷", "体验缺陷", "兼容性问题", "其它问题"}:
            reason_levels[reason] = "minor"
    expected_reasons = {
        "功能缺陷",
        "性能问题",
        "数据一致性问题",
        "依赖异常",
        "界面缺陷",
        "体验缺陷",
        "兼容性问题",
        "其它问题",
    }
    if set(reason_levels) != expected_reasons:
        raise ReleaseReadinessValidationError(
            "prd-reason-rules-invalid", "PRD 的原因类型与基础等级表不完整。"
        )
    return {
        "p0_tested_threshold": float(p0_tested.group(1)),
        "p0_accepted_threshold": float(p0_accepted.group(1)),
        "p1_passed_threshold": float(p1_passed.group(1)),
        "compatibility_severe_threshold": int(compat_threshold.group(1)),
        "reason_levels": reason_levels,
    }


def _preview_rows(preview: dict[str, Any] | None, label: str) -> list[SourceRow]:
    if not preview or preview.get("kind") != "table":
        raise ReleaseReadinessValidationError(
            "table-preview-missing", f"{label} 没有可校验的表格预览。"
        )
    rows: list[SourceRow] = []
    for raw in preview.get("rows") or []:
        row_number = raw.get("row_number")
        if not isinstance(row_number, int) or row_number < 1:
            raise ReleaseReadinessValidationError(
                "table-row-number", f"{label} 存在无效原始行号。"
            )
        rows.append(
            SourceRow(
                row_number=row_number,
                values=tuple(str(value or "").strip() for value in raw.get("values") or []),
            )
        )
    return rows


def _parse_single_header_table(
    preview: dict[str, Any] | None,
    expected_headers: tuple[str, ...],
    *,
    expected_count: int,
    label: str,
) -> list[SourceRow]:
    rows = _preview_rows(preview, label)
    if not rows or rows[0].values != expected_headers:
        raise ReleaseReadinessValidationError(
            "table-header-invalid", f"{label} 表头与固定数据合同不一致。"
        )
    records = rows[1:]
    if len(records) != expected_count:
        raise ReleaseReadinessValidationError(
            "table-row-count",
            f"{label} 应有 {expected_count} 条功能记录，实际为 {len(records)} 条。",
        )
    for row in records:
        if len(row.values) != len(expected_headers) or any(
            not value for value in row.values[:5]
        ):
            raise ReleaseReadinessValidationError(
                "table-required-column", f"{label} 第 {row.row_number} 行缺少必填列。"
            )
    return records


def _parse_compatibility_table(
    preview: dict[str, Any] | None,
) -> tuple[list[SourceRow], tuple[str, ...]]:
    label = "线上兼容环境测试报告.xlsx"
    rows = _preview_rows(preview, label)
    if len(rows) < 3 or len(rows[0].values) != len(rows[1].values):
        raise ReleaseReadinessValidationError(
            "compatibility-header-invalid", f"{label} 两行表头不完整。"
        )
    if rows[0].values[:4] != ("功能信息", "", "", ""):
        raise ReleaseReadinessValidationError(
            "compatibility-header-invalid", f"{label} 第一行功能信息表头无效。"
        )
    if rows[1].values[:4] != COMPATIBILITY_PREFIX_HEADERS:
        raise ReleaseReadinessValidationError(
            "compatibility-header-invalid", f"{label} 第二行功能表头无效。"
        )
    environments = tuple(
        f"{browser} / {system}"
        for browser, system in zip(rows[0].values[4:], rows[1].values[4:], strict=True)
    )
    if len(environments) != 8 or any(" / " == value for value in environments):
        raise ReleaseReadinessValidationError(
            "compatibility-environment-count", f"{label} 应定义 8 个浏览器与系统组合。"
        )
    if len(set(environments)) != len(environments):
        raise ReleaseReadinessValidationError(
            "compatibility-environment-duplicate", f"{label} 存在重复环境语义。"
        )
    records = rows[2:]
    if len(records) != 13:
        raise ReleaseReadinessValidationError(
            "table-row-count", f"{label} 应有 13 条功能记录，实际为 {len(records)} 条。"
        )
    for row in records:
        if len(row.values) != 4 + len(environments) or any(
            not value for value in row.values
        ):
            raise ReleaseReadinessValidationError(
                "table-required-column", f"{label} 第 {row.row_number} 行缺少必填列。"
            )
    return records, environments


def _unique_map(items: list[Any], *, key: Any, label: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in items:
        value = str(key(item))
        if value in result:
            raise ReleaseReadinessValidationError(
                "duplicate-id", f"{label} 出现重复值 {value}，禁止后行覆盖前行。"
            )
        result[value] = item
    return result


def _validated_feature_rows(
    rows: list[SourceRow],
    prd_by_code: dict[str, PrdFeature],
    label: str,
) -> dict[str, SourceRow]:
    result = _unique_map(rows, key=lambda item: item.values[0], label=f"{label} 功能编号")
    for code, row in result.items():
        if code not in prd_by_code:
            raise ReleaseReadinessValidationError(
                "unknown-feature", f"{label} 第 {row.row_number} 行包含未知功能编号 {code}。"
            )
        feature = prd_by_code[code]
        if row.values[1] != feature.name:
            raise ReleaseReadinessValidationError(
                "feature-name-conflict",
                f"{label} 第 {row.row_number} 行的 {code} 名称与 PRD 不一致。",
            )
        if row.values[3] != feature.priority:
            raise ReleaseReadinessValidationError(
                "feature-priority-conflict",
                f"{label} 第 {row.row_number} 行的 {code} 优先级与 PRD 不一致。",
            )
        if re.sub(r"\s+", "", row.values[2]) != re.sub(r"\s+", "", feature.module):
            raise ReleaseReadinessValidationError(
                "feature-module-conflict",
                f"{label} 第 {row.row_number} 行的 {code} 模块与 PRD 不一致。",
            )
    return result


def _validate_config_rows(rows: list[SourceRow]) -> None:
    for row in rows:
        if row.values[7] not in CONFIG_STATUSES:
            raise ReleaseReadinessValidationError(
                "config-status-invalid",
                f"上线配置清单.xlsx 第 {row.row_number} 行提测状态无效。",
            )


def _parse_nonnegative_int(value: str, *, label: str) -> int:
    if not re.fullmatch(r"\d+", value):
        raise ReleaseReadinessValidationError(
            "test-count-invalid", f"{label} 必须是非负整数。"
        )
    return int(value)


def _validate_test_rows(rows: list[SourceRow], reason_levels: dict[str, str]) -> None:
    for row in rows:
        conclusion = row.values[9]
        reason = row.values[10]
        if conclusion not in TEST_CONCLUSIONS:
            raise ReleaseReadinessValidationError(
                "test-conclusion-invalid",
                f"功能测试报告.xlsx 第 {row.row_number} 行测试结论无效。",
            )
        total = _parse_nonnegative_int(
            row.values[7], label=f"功能测试报告.xlsx 第 {row.row_number} 行用例总数"
        )
        passed = _parse_nonnegative_int(
            row.values[8], label=f"功能测试报告.xlsx 第 {row.row_number} 行通过数"
        )
        if passed > total:
            raise ReleaseReadinessValidationError(
                "test-count-order",
                f"功能测试报告.xlsx 第 {row.row_number} 行通过数大于用例总数。",
            )
        if conclusion in {"有条件通过", "不通过"} and reason not in reason_levels:
            raise ReleaseReadinessValidationError(
                "test-reason-invalid",
                f"功能测试报告.xlsx 第 {row.row_number} 行不通过原因类型无效。",
            )
        if conclusion == "通过" and reason not in NO_ISSUE_VALUES:
            raise ReleaseReadinessValidationError(
                "test-reason-conflict",
                f"功能测试报告.xlsx 第 {row.row_number} 行通过结论却记录了问题类型。",
            )


def _validate_compatibility_rows(
    rows: list[SourceRow], environments: tuple[str, ...]
) -> None:
    for row in rows:
        for offset, status in enumerate(row.values[4:]):
            if status not in COMPATIBILITY_STATUSES:
                raise ReleaseReadinessValidationError(
                    "compatibility-status-invalid",
                    f"线上兼容环境测试报告.xlsx 第 {row.row_number} 行环境“{environments[offset]}”状态无效。",
                )


def _safe_percent(numerator: int, denominator: int, *, label: str) -> float:
    if denominator <= 0:
        raise ReleaseReadinessValidationError(
            "zero-denominator", f"{label} 的分母为 0，不能形成上线 Gate。"
        )
    return round(numerator / denominator * 100, 1)


def _build_gates(
    features: list[PrdFeature],
    config_by_code: dict[str, SourceRow],
    test_by_code: dict[str, SourceRow],
    rules: dict[str, Any],
) -> list[AgentControlLoopBusinessGate]:
    p0_codes = [item.code for item in features if item.priority == "P0"]
    tested_p0_codes = [
        code
        for code in p0_codes
        if code in config_by_code and config_by_code[code].values[7] == "已提测"
    ]
    p0_accepted = sum(
        test_by_code[code].values[9] in {"通过", "有条件通过"}
        for code in tested_p0_codes
        if code in test_by_code
    )
    tested_p1_codes = [
        item.code
        for item in features
        if item.priority == "P1"
        and item.code in config_by_code
        and config_by_code[item.code].values[7] == "已提测"
    ]
    p1_passed = sum(
        test_by_code[code].values[9] == "通过"
        for code in tested_p1_codes
        if code in test_by_code
    )
    p0_tested_actual = _safe_percent(
        len(tested_p0_codes), len(p0_codes), label="P0 功能提测率"
    )
    p0_accepted_actual = _safe_percent(
        p0_accepted, len(tested_p0_codes), label="P0 功能测试通过率"
    )
    p1_passed_actual = _safe_percent(
        p1_passed, len(tested_p1_codes), label="P1 功能完成率"
    )
    return [
        AgentControlLoopBusinessGate(
            gate_id="business-gate-p0-tested",
            label="P0 功能提测率",
            passed=p0_tested_actual >= rules["p0_tested_threshold"],
            numerator=float(len(tested_p0_codes)),
            denominator=float(len(p0_codes)),
            operator=">=",
            threshold=rules["p0_tested_threshold"],
            actual=p0_tested_actual,
            unit="percent",
            formula="已提测 P0 功能数 / PRD P0 功能总数 × 100%",
            source_rule="PRD_v2.5.md 上线条件：P0 功能提测率必须达到 100%。",
            result=f"{len(tested_p0_codes)}/{len(p0_codes)} = {p0_tested_actual:.1f}%。",
        ),
        AgentControlLoopBusinessGate(
            gate_id="business-gate-p0-accepted",
            label="P0 已提测功能测试结论",
            passed=p0_accepted_actual >= rules["p0_accepted_threshold"],
            numerator=float(p0_accepted),
            denominator=float(len(tested_p0_codes)),
            operator=">=",
            threshold=rules["p0_accepted_threshold"],
            actual=p0_accepted_actual,
            unit="percent",
            formula="结论为通过或有条件通过的 P0 功能数 / P0 已提测功能数 × 100%",
            source_rule="PRD_v2.5.md 上线条件：P0 已提测功能结论通过率必须达到 100%。",
            result=f"{p0_accepted}/{len(tested_p0_codes)} = {p0_accepted_actual:.1f}%。",
        ),
        AgentControlLoopBusinessGate(
            gate_id="business-gate-p1-passed",
            label="P1 已提测功能完成率",
            passed=p1_passed_actual >= rules["p1_passed_threshold"],
            numerator=float(p1_passed),
            denominator=float(len(tested_p1_codes)),
            operator=">=",
            threshold=rules["p1_passed_threshold"],
            actual=p1_passed_actual,
            unit="percent",
            formula="结论为通过的 P1 功能数 / P1 已提测功能数 × 100%",
            source_rule="PRD_v2.5.md 上线条件：P1 已提测功能完成率必须达到 80%。",
            result=f"{p1_passed}/{len(tested_p1_codes)} = {p1_passed_actual:.1f}%。",
        ),
        AgentControlLoopBusinessGate(
            gate_id="business-gate-severe-zero",
            label="严重问题清零",
            passed=True,
            numerator=0,
            denominator=1,
            operator="==",
            threshold=0,
            actual=0,
            unit="count",
            formula="逐功能最终风险等级为严重的功能数",
            source_rule="PRD_v2.5.md 上线条件：严重等级问题必须清零。",
            result="等待逐功能风险台账计算。",
        ),
    ]


def _build_auxiliary_metrics(
    features: list[PrdFeature], test_by_code: dict[str, SourceRow]
) -> list[AgentControlLoopBusinessMetric]:
    metrics: list[AgentControlLoopBusinessMetric] = []
    for priority in ("P0", "P1", "P2"):
        rows = [
            test_by_code[item.code]
            for item in features
            if item.priority == priority and item.code in test_by_code
        ]
        total = sum(int(row.values[7]) for row in rows)
        passed = sum(int(row.values[8]) for row in rows)
        value = _safe_percent(passed, total, label=f"{priority} 用例通过率")
        metrics.append(
            AgentControlLoopBusinessMetric(
                metric_id=f"business-metric-{priority.lower()}-case-pass",
                label=f"{priority} 用例通过率",
                numerator=float(passed),
                denominator=float(total),
                value=value,
                unit="percent",
                formula="通过用例数 / 用例总数 × 100%",
                source_note="辅助质量指标，不是 PRD 正式上线 Gate。",
            )
        )
    total = sum(int(row.values[7]) for row in test_by_code.values())
    passed = sum(int(row.values[8]) for row in test_by_code.values())
    metrics.append(
        AgentControlLoopBusinessMetric(
            metric_id="business-metric-overall-case-pass",
            label="综合用例通过率",
            numerator=float(passed),
            denominator=float(total),
            value=_safe_percent(passed, total, label="综合用例通过率"),
            unit="percent",
            formula="全部已提测功能通过用例数 / 全部已提测功能用例总数 × 100%",
            source_note="辅助质量指标，不替代 P0/P1 功能结论 Gate。",
        )
    )
    return metrics


def _higher_risk(*levels: str) -> str:
    return max(levels, key=lambda level: RISK_ORDER[level])


def _build_records(
    features: list[PrdFeature],
    config_by_code: dict[str, SourceRow],
    test_by_code: dict[str, SourceRow],
    compatibility_by_code: dict[str, SourceRow],
    environments: tuple[str, ...],
    rules: dict[str, Any],
) -> list[AgentControlLoopBusinessRecord]:
    records: list[AgentControlLoopBusinessRecord] = []
    for feature in features:
        config = config_by_code.get(feature.code)
        test = test_by_code.get(feature.code)
        compatibility = compatibility_by_code.get(feature.code)
        configuration_status = config.values[7] if config else "未列入配置清单"
        test_status = test.values[9] if test else "未提测"
        test_reason = test.values[10] if test and test.values[10] not in NO_ISSUE_VALUES else "无"
        total_cases = int(test.values[7]) if test else 0
        passed_cases = int(test.values[8]) if test else 0
        compatibility_issues = [
            environments[index]
            for index, value in enumerate(compatibility.values[4:] if compatibility else ())
            if value in {"部分通过", "兼容问题"}
        ]
        test_has_issue = test_status in {"有条件通过", "不通过"}
        has_issue = test_has_issue or bool(compatibility_issues)
        rules_hit: list[str] = []
        base_level = "none"
        if feature.priority == "P0" and has_issue:
            base_level = "severe"
            rules_hit.append("规则一：P0 功能存在问题，直接判为严重")
        elif test_has_issue:
            base_level = rules["reason_levels"][test.values[10]]
            rules_hit.append(
                f"规则二：非 P0 的{test.values[10]}，基础等级为{RISK_LABELS[base_level]}"
            )
        compatibility_level = "none"
        if compatibility_issues:
            if len(compatibility_issues) >= rules["compatibility_severe_threshold"]:
                compatibility_level = "severe"
                rules_hit.append(
                    f"规则三：{len(compatibility_issues)} 个异常环境达到升级阈值 {rules['compatibility_severe_threshold']}"
                )
            else:
                compatibility_level = "minor"
                rules_hit.append(
                    f"规则三：{len(compatibility_issues)} 个异常环境未达到严重升级阈值"
                )
        final_level = _higher_risk(base_level, compatibility_level)
        affected_gates: list[str] = []
        if feature.priority == "P0" and configuration_status != "已提测":
            affected_gates.append("business-gate-p0-tested")
        if feature.priority == "P0" and configuration_status == "已提测" and test_status not in {
            "通过",
            "有条件通过",
        }:
            affected_gates.append("business-gate-p0-accepted")
        if feature.priority == "P1" and configuration_status == "已提测" and test_status != "通过":
            affected_gates.append("business-gate-p1-passed")
        if final_level == "severe":
            affected_gates.append("business-gate-severe-zero")
        source_locations = [f"PRD_v2.5.md 第 {feature.line_number} 行"]
        if config:
            source_locations.append(f"上线配置清单.xlsx 第 {config.row_number} 行")
        if test:
            source_locations.append(f"功能测试报告.xlsx 第 {test.row_number} 行")
        if compatibility:
            source_locations.append(
                f"线上兼容环境测试报告.xlsx 第 {compatibility.row_number} 行"
            )
        remediation_action, exit_condition = _remediation(
            feature,
            configuration_status=configuration_status,
            test_status=test_status,
            test_reason=test_reason,
            compatibility_issues=compatibility_issues,
            final_level=final_level,
        )
        records.append(
            AgentControlLoopBusinessRecord(
                record_id=feature.code,
                title=feature.name,
                module=feature.module,
                priority=feature.priority,
                owner=feature.owner,
                configuration_status=configuration_status,
                test_status=test_status,
                test_reason=test_reason,
                total_cases=total_cases,
                passed_cases=passed_cases,
                compatibility_issue_count=len(compatibility_issues),
                compatibility_issue_environments=compatibility_issues,
                rules_hit=rules_hit,
                base_risk_level=base_level,
                compatibility_risk_level=compatibility_level,
                final_risk_level=final_level,
                affected_gate_ids=affected_gates,
                source_locations=source_locations,
                remediation_action=remediation_action,
                exit_condition=exit_condition,
            )
        )
    return records


def _remediation(
    feature: PrdFeature,
    *,
    configuration_status: str,
    test_status: str,
    test_reason: str,
    compatibility_issues: list[str],
    final_level: str,
) -> tuple[str, str]:
    if configuration_status != "已提测":
        return (
            f"由{feature.owner}补齐可追溯的上线配置和提测记录，并安排功能与兼容测试。",
            f"{feature.code} 在三份执行清单中均存在且提测状态为已提测，测试结论满足对应优先级 Gate。",
        )
    actions: list[str] = []
    exits: list[str] = []
    if test_status != "通过":
        actions.append(f"由{feature.owner}修复“{test_reason}”对应问题并重新提测")
        exits.append(
            "功能测试结论为通过"
            if feature.priority != "P0"
            else "功能测试结论为通过或有条件通过，且 P0 问题清零"
        )
    if compatibility_issues:
        actions.append(
            f"由{feature.owner}修复 {len(compatibility_issues)} 个异常环境并完成八环境回归"
        )
        exits.append("八个浏览器与系统组合全部为通过")
    if final_level == "none":
        return (
            f"由{feature.owner}保留当前证据并在发布前复核配置、测试和兼容记录。",
            "三份记录仍可追溯且四项正式上线 Gate 均满足。",
        )
    return "；".join(actions) + "。", "；".join(exits) + "。"


def _ledger_csv(records: list[AgentControlLoopBusinessRecord]) -> bytes:
    headers = [
        "功能编号",
        "功能名称",
        "所属模块",
        "优先级",
        "研发负责人",
        "配置状态",
        "测试结论",
        "问题原因类型",
        "用例总数",
        "通过数",
        "异常环境数",
        "异常环境",
        "命中规则",
        "基础等级",
        "兼容升级等级",
        "最终等级",
        "影响上线Gate",
        "来源位置",
        "整改动作",
        "退出条件",
    ]
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(headers)
    for record in records:
        writer.writerow(
            [
                record.record_id,
                record.title,
                record.module,
                record.priority,
                record.owner,
                record.configuration_status,
                record.test_status,
                record.test_reason,
                record.total_cases,
                record.passed_cases,
                record.compatibility_issue_count,
                "；".join(record.compatibility_issue_environments),
                "；".join(record.rules_hit),
                RISK_LABELS[record.base_risk_level],
                RISK_LABELS[record.compatibility_risk_level],
                RISK_LABELS[record.final_risk_level],
                "；".join(record.affected_gate_ids),
                "；".join(record.source_locations),
                record.remediation_action,
                record.exit_condition,
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def _report_docx(
    outcome: AgentControlLoopBusinessGateOutcome,
    *,
    risk_counts: dict[str, int],
    missing_codes: tuple[str, ...],
) -> tuple[bytes, int]:
    risk_records = sorted(
        (record for record in outcome.records if record.final_risk_level != "none"),
        key=lambda item: (-RISK_ORDER[item.final_risk_level], int(item.record_id[1:])),
    )
    missing_records = [
        record for record in outcome.records if record.record_id in missing_codes
    ]
    tables = [
        (
            ["正式上线 Gate", "分子/分母", "实际值", "标准", "结果", "来源规则"],
            [
                [
                    gate.label,
                    f"{gate.numerator:g}/{gate.denominator:g}",
                    _format_gate_value(gate.actual, gate.unit),
                    f"{gate.operator} {_format_gate_value(gate.threshold, gate.unit)}",
                    "通过" if gate.passed else "未通过",
                    gate.source_rule,
                ]
                for gate in outcome.gates
            ],
        ),
        (
            ["辅助质量指标", "分子/分母", "结果", "说明"],
            [
                [
                    metric.label,
                    f"{metric.numerator:g}/{metric.denominator:g}",
                    _format_gate_value(metric.value, metric.unit),
                    metric.source_note,
                ]
                for metric in outcome.auxiliary_metrics
            ],
        ),
        (
            [
                "编号",
                "功能",
                "优先级",
                "负责人",
                "配置",
                "测试",
                "异常环境",
                "最终风险",
                "影响 Gate",
                "来源位置",
            ],
            [
                [
                    record.record_id,
                    record.title,
                    record.priority,
                    record.owner,
                    record.configuration_status,
                    record.test_status,
                    str(record.compatibility_issue_count),
                    RISK_LABELS[record.final_risk_level],
                    "、".join(record.affected_gate_ids) or "无",
                    "；".join(record.source_locations),
                ]
                for record in outcome.records
            ],
        ),
        (
            ["编号", "功能", "最终等级", "命中规则", "问题来源"],
            [
                [
                    record.record_id,
                    record.title,
                    RISK_LABELS[record.final_risk_level],
                    "；".join(record.rules_hit),
                    "；".join(record.source_locations),
                ]
                for record in risk_records
            ],
        ),
        (
            ["未提测编号", "功能", "负责人", "补齐动作", "退出条件"],
            [
                [
                    record.record_id,
                    record.title,
                    record.owner,
                    record.remediation_action,
                    record.exit_condition,
                ]
                for record in missing_records
            ],
        ),
        (
            ["顺序", "编号", "等级", "负责人", "整改动作", "可验证退出条件"],
            [
                [
                    str(index),
                    record.record_id,
                    RISK_LABELS[record.final_risk_level],
                    record.owner,
                    record.remediation_action,
                    record.exit_condition,
                ]
                for index, record in enumerate(
                    [*risk_records, *missing_records], start=1
                )
            ],
        ),
    ]
    paragraphs = [
        ("title", "AIPilot Console v2.5 上线合规与风险报告"),
        ("heading", f"上线结论：{outcome.decision}"),
        (
            "body",
            f"正式上线条件 {outcome.failed_gate_count}/{outcome.total_gate_count} 未通过。确定性检查只证明公式、台账和文件结构已复核，不代表可以上线。",
        ),
        ("heading", "一、正式上线 Gate"),
        ("table", tables[0]),
        ("heading", "二、辅助质量指标"),
        ("body", "以下指标用于理解测试质量，不是 PRD 正式上线 Gate。"),
        ("table", tables[1]),
        ("heading", "三、18 项逐功能矩阵"),
        ("table", tables[2]),
        ("heading", "四、8 项风险"),
        (
            "body",
            f"严重 {risk_counts['severe']} 项、主要 {risk_counts['major']} 项、次要 {risk_counts['minor']} 项；同一功能仅保留最高等级。",
        ),
        ("table", tables[3]),
        ("heading", "五、5 项未提测功能"),
        ("table", tables[4]),
        ("heading", "六、整改计划"),
        ("body", "先处理严重问题，再处理主要、次要问题，随后补齐未提测功能；不虚构日期、签字或完成状态。"),
        ("table", tables[5]),
        ("heading", "七、执行边界"),
        (
            "body",
            "本次只在隔离运行工作区生成并校验报告与台账；没有执行上线、没有修改配置、没有发送通知。成果仍需发布、研发、测试负责人共同复核。",
        ),
    ]
    return _docx_bytes(paragraphs), len(tables)


def _format_gate_value(value: float, unit: str) -> str:
    return f"{value:.1f}%" if unit == "percent" else f"{value:g} 项"


def _docx_bytes(blocks: list[tuple[str, Any]]) -> bytes:
    def run(text: str, *, bold: bool = False, size: int = 22) -> str:
        properties = f'<w:rPr>{"<w:b/>" if bold else ""}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
        return f'<w:r>{properties}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'

    def paragraph(text: str, *, bold: bool = False, size: int = 22) -> str:
        return f"<w:p>{run(text, bold=bold, size=size)}</w:p>"

    def table(headers: list[str], rows: list[list[str]]) -> str:
        def cell(value: str, *, header: bool = False) -> str:
            return "<w:tc><w:tcPr/><w:p>" + run(value, bold=header, size=18) + "</w:p></w:tc>"

        header_row = "<w:tr>" + "".join(cell(item, header=True) for item in headers) + "</w:tr>"
        body_rows = "".join(
            "<w:tr>" + "".join(cell(str(item)) for item in row) + "</w:tr>"
            for row in rows
        )
        return (
            '<w:tbl><w:tblPr><w:tblBorders>'
            '<w:top w:val="single" w:sz="4" w:color="999999"/>'
            '<w:left w:val="single" w:sz="4" w:color="999999"/>'
            '<w:bottom w:val="single" w:sz="4" w:color="999999"/>'
            '<w:right w:val="single" w:sz="4" w:color="999999"/>'
            '<w:insideH w:val="single" w:sz="4" w:color="BBBBBB"/>'
            '<w:insideV w:val="single" w:sz="4" w:color="BBBBBB"/>'
            "</w:tblBorders></w:tblPr>"
            + header_row
            + body_rows
            + "</w:tbl>"
        )

    body: list[str] = []
    for kind, value in blocks:
        if kind == "title":
            body.append(paragraph(str(value), bold=True, size=34))
        elif kind == "heading":
            body.append(paragraph(str(value), bold=True, size=28))
        elif kind == "body":
            body.append(paragraph(str(value), size=22))
        elif kind == "table":
            headers, rows = value
            body.append(table(headers, rows))
        else:
            raise ValueError(f"unknown DOCX block: {kind}")
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(body)
        + '<w:sectPr><w:pgSz w:w="16838" w:h="11906" w:orient="landscape"/>'
        '<w:pgMar w:top="720" w:right="720" w:bottom="720" w:left="720"/></w:sectPr>'
        "</w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return output.getvalue()
