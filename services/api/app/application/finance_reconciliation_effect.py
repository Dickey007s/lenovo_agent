"""Source-derived Finance-018 reconciliation and independent artifact verification.

The adapter is deliberately narrow. It reads three approved XLSX workbooks,
keeps their row locators, writes two 2026 detail CSVs plus one cross-period
Markdown review, and never turns a heuristic candidate into an accounting
decision or an external action.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import posixpath
import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from packages.contracts.harness_models import (
    AgentControlLoopFinanceCandidate,
    AgentControlLoopFinanceCandidateSource,
    AgentControlLoopFinanceReviewOutcome,
)


class FinanceReconciliationValidationError(ValueError):
    """The fixed Finance-018 source or generated artifact contract is invalid."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class FinanceSourceInput:
    logical_id: str
    period_id: str
    period_label: str
    file_name: str
    display_path: str
    file_ref: str
    content: bytes
    declared_size: int
    allowlist_verified: bool


@dataclass(frozen=True)
class FinanceLedgerRow:
    period_id: str
    period_label: str
    source_file_ref: str
    file_name: str
    sheet_name: str
    row_number: int
    subject: str
    customer: str
    opening_direction: str
    ending_direction: str
    ending_balance: Decimal

    @property
    def key(self) -> tuple[str, str]:
        return self.subject, self.customer

    @property
    def locator(self) -> str:
        return f"{self.sheet_name}!A{self.row_number}:J{self.row_number}"


@dataclass(frozen=True)
class FinanceAnalysis:
    rows_by_period: dict[str, tuple[FinanceLedgerRow, ...]]
    period_summaries: dict[str, dict[str, object]]
    unpaid_rows: tuple[FinanceLedgerRow, ...]
    unreceived_rows: tuple[FinanceLedgerRow, ...]
    unpaid_total: Decimal
    unreceived_total: Decimal
    candidates: tuple[AgentControlLoopFinanceCandidate, ...]
    outcome: AgentControlLoopFinanceReviewOutcome


@dataclass(frozen=True)
class FinanceArtifactCheck:
    artifact_name: str
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class FinanceReconciliationBuild:
    unpaid_csv: bytes
    unreceived_csv: bytes
    cross_period_markdown: bytes
    analysis: FinanceAnalysis
    checks: tuple[FinanceArtifactCheck, ...]


PERIOD_ORDER = ("2025_h1", "2025_h2", "2026")
SOURCE_SPECS = {
    "2025_h1": (
        "finance-2025-h1",
        "2025 年上半年",
        "2025往来明细-上半年.xlsx",
        "财务管理/2025往来明细-上半年.xlsx",
    ),
    "2025_h2": (
        "finance-2025-h2",
        "2025 年下半年",
        "2025往来明细-下半年.xlsx",
        "财务管理/2025往来明细-下半年.xlsx",
    ),
    "2026": (
        "finance-2026",
        "2026 年",
        "2026往来明细.xlsx",
        "财务管理/2026往来明细.xlsx",
    ),
}
EXPECTED_HEADERS = (
    "科目名称",
    "客商名称",
    "方向",
    "期初余额",
    "本期借方",
    "本期贷方",
    "借方累计",
    "贷方累计",
    "方向",
    "期末余额",
)
DETAIL_HEADERS = (
    "科目名称",
    "客商名称",
    "方向",
    "期末余额",
    "来源文件",
    "来源文件Ref",
    "来源位置",
)
METHOD = (
    "同一“科目名称+客商名称”在 2025 年上半年、2025 年下半年和 2026 年"
    "均为正数借方期末余额，且三期金额完全相同，才列为僵尸账款候选。"
)
LIMITATIONS = (
    "当前固定适配器没有主体、科目编码、币种或子项字段，名称相同不代表会计主体相同。",
    "没有检查期间内发生额、账龄、核销记录或贷方余额，候选不是僵尸账款业务定论。",
    "只处理固定 Finance-018 三个期间，不能替代总账、应收应付或坏账确认流程。",
)
REVIEW_ACTION = "财务人员回开三期原表，核对期间内发生额、账龄、币种、主体和核销记录。"
EXIT_CONDITION = "财务人员记录逐项复核结论和依据后，才能决定是否进入后续会计处理。"

_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def build_finance_reconciliation(
    sources: tuple[FinanceSourceInput, ...],
) -> FinanceReconciliationBuild:
    """Build artifacts, then reparse sources and artifacts for verification."""

    analysis = analyze_finance_sources(sources)
    unpaid_csv = _detail_csv(analysis.unpaid_rows)
    unreceived_csv = _detail_csv(analysis.unreceived_rows)
    cross_period_markdown = _cross_period_markdown(analysis)
    checks = verify_finance_artifacts(
        sources,
        unpaid_csv=unpaid_csv,
        unreceived_csv=unreceived_csv,
        cross_period_markdown=cross_period_markdown,
    )
    return FinanceReconciliationBuild(
        unpaid_csv=unpaid_csv,
        unreceived_csv=unreceived_csv,
        cross_period_markdown=cross_period_markdown,
        analysis=analysis,
        checks=checks,
    )


def analyze_finance_sources(
    sources: tuple[FinanceSourceInput, ...],
) -> FinanceAnalysis:
    validated = _validate_source_bundle(sources)
    rows_by_period = {
        period_id: tuple(_parse_workbook(validated[period_id])) for period_id in PERIOD_ORDER
    }
    current_rows = rows_by_period["2026"]
    unpaid_rows = tuple(
        sorted(
            (
                row
                for row in current_rows
                if row.ending_direction == "贷" and row.ending_balance > 0
            ),
            key=_detail_sort_key,
        )
    )
    unreceived_rows = tuple(
        sorted(
            (
                row
                for row in current_rows
                if row.ending_direction == "借" and row.ending_balance > 0
            ),
            key=_detail_sort_key,
        )
    )
    candidates = _candidate_records(rows_by_period)
    period_summaries = {
        period_id: {
            "period_label": rows_by_period[period_id][0].period_label,
            "source_file_ref": rows_by_period[period_id][0].source_file_ref,
            "file_name": rows_by_period[period_id][0].file_name,
            "row_count": len(rows_by_period[period_id]),
            "positive_debit_total": _decimal_text(
                sum(
                    (
                        row.ending_balance
                        for row in rows_by_period[period_id]
                        if row.ending_direction == "借" and row.ending_balance > 0
                    ),
                    Decimal(0),
                )
            ),
        }
        for period_id in PERIOD_ORDER
    }
    unpaid_total = sum((row.ending_balance for row in unpaid_rows), Decimal(0))
    unreceived_total = sum((row.ending_balance for row in unreceived_rows), Decimal(0))
    candidate_count = len(candidates)
    decision = (
        f"发现 {candidate_count} 条跨期风险候选，需财务复核；"
        if candidate_count
        else "当前启发式未发现跨期风险候选，仍需财务复核；"
    ) + "未执行付款、核销、记账或坏账确认。"
    outcome = AgentControlLoopFinanceReviewOutcome(
        outcome_id="finance-review-outcome-finance-018",
        status="review_required",
        decision=decision,
        summary=(
            f"2026 期末未付 {len(unpaid_rows)} 条、未收 {len(unreceived_rows)} 条；"
            f"三期启发式候选 {candidate_count} 条。来源计算通过不等于会计处置已完成。"
        ),
        period_ids=list(PERIOD_ORDER),
        unpaid_count=len(unpaid_rows),
        unpaid_total=_decimal_text(unpaid_total),
        unreceived_count=len(unreceived_rows),
        unreceived_total=_decimal_text(unreceived_total),
        candidate_count=candidate_count,
        candidates=list(candidates),
        method=METHOD,
        limitations=list(LIMITATIONS),
    )
    return FinanceAnalysis(
        rows_by_period=rows_by_period,
        period_summaries=period_summaries,
        unpaid_rows=unpaid_rows,
        unreceived_rows=unreceived_rows,
        unpaid_total=unpaid_total,
        unreceived_total=unreceived_total,
        candidates=candidates,
        outcome=outcome,
    )


def verify_finance_artifacts(
    sources: tuple[FinanceSourceInput, ...],
    *,
    unpaid_csv: bytes,
    unreceived_csv: bytes,
    cross_period_markdown: bytes,
) -> tuple[FinanceArtifactCheck, ...]:
    """Independently reparse approved sources and all three generated files."""

    expected = analyze_finance_sources(sources)
    checks: list[FinanceArtifactCheck] = []
    checks.extend(
        _verify_detail_artifact(
            "未付统计.csv",
            unpaid_csv,
            expected.unpaid_rows,
            expected.unpaid_total,
            prefix="unpaid",
        )
    )
    checks.extend(
        _verify_detail_artifact(
            "未收统计.csv",
            unreceived_csv,
            expected.unreceived_rows,
            expected.unreceived_total,
            prefix="unreceived",
        )
    )
    checks.extend(_verify_cross_period_artifact(cross_period_markdown, expected))
    return tuple(checks)


def _validate_source_bundle(
    sources: tuple[FinanceSourceInput, ...],
) -> dict[str, FinanceSourceInput]:
    if len(sources) != 3:
        raise FinanceReconciliationValidationError(
            "source-count", "Finance-018 必须恰好包含三个固定期间工作簿。"
        )
    by_period: dict[str, FinanceSourceInput] = {}
    logical_ids: set[str] = set()
    file_refs: set[str] = set()
    digests: set[str] = set()
    for source in sources:
        spec = SOURCE_SPECS.get(source.period_id)
        if spec is None:
            raise FinanceReconciliationValidationError(
                "unknown-period", f"出现未知期间：{source.period_id}。"
            )
        if source.period_id in by_period:
            raise FinanceReconciliationValidationError(
                "duplicate-period", f"期间 {source.period_id} 重复。"
            )
        logical_id, period_label, file_name, display_path = spec
        if (
            source.logical_id != logical_id
            or source.period_label != period_label
            or source.file_name != file_name
            or source.display_path != display_path
        ):
            raise FinanceReconciliationValidationError(
                "source-identity", f"{source.period_id} 的逻辑身份、名称或路径不匹配。"
            )
        if not source.allowlist_verified or not source.file_ref:
            raise FinanceReconciliationValidationError(
                "source-allowlist", f"{source.file_name} 未通过服务端 allowlist。"
            )
        if not source.content or source.declared_size != len(source.content):
            raise FinanceReconciliationValidationError(
                "source-size", f"{source.file_name} 为空或声明大小与冻结字节不一致。"
            )
        digest = hashlib.sha256(source.content).hexdigest()
        if source.logical_id in logical_ids or source.file_ref in file_refs or digest in digests:
            raise FinanceReconciliationValidationError(
                "source-duplicate", "逻辑 ID、file_ref 或原始内容重复，不能冒充三个期间。"
            )
        logical_ids.add(source.logical_id)
        file_refs.add(source.file_ref)
        digests.add(digest)
        by_period[source.period_id] = source
    if tuple(period_id for period_id in PERIOD_ORDER if period_id in by_period) != PERIOD_ORDER:
        raise FinanceReconciliationValidationError(
            "period-set", "固定期间集合不完整。"
        )
    return by_period


def _parse_workbook(source: FinanceSourceInput) -> list[FinanceLedgerRow]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(source.content))
    except (OSError, zipfile.BadZipFile) as exc:
        raise FinanceReconciliationValidationError(
            "xlsx-corrupt", f"{source.file_name} 不是可读取的 XLSX。"
        ) from exc
    with archive:
        names = archive.namelist()
        if len(names) > 128 or any(_unsafe_archive_name(name) for name in names):
            raise FinanceReconciliationValidationError(
                "xlsx-archive", f"{source.file_name} 的压缩包结构越界。"
            )
        total_size = sum(item.file_size for item in archive.infolist())
        if total_size > 20 * 1024 * 1024 or any(
            item.file_size > 5 * 1024 * 1024 for item in archive.infolist()
        ):
            raise FinanceReconciliationValidationError(
                "xlsx-archive-size", f"{source.file_name} 解压后大小越界。"
            )
        if any(
            name.lower().endswith("vbaproject.bin") or "externallinks/" in name.lower()
            for name in names
        ):
            raise FinanceReconciliationValidationError(
                "xlsx-active-content", f"{source.file_name} 含宏或外部链接。"
            )
        required = {
            "xl/workbook.xml",
            "xl/_rels/workbook.xml.rels",
            "xl/worksheets/sheet1.xml",
        }
        if not required.issubset(names):
            raise FinanceReconciliationValidationError(
                "xlsx-parts", f"{source.file_name} 缺少必要工作簿部件。"
            )
        shared_strings = _shared_strings(archive)
        sheet_name, sheet_path = _single_sheet(archive)
        try:
            root = ET.fromstring(archive.read(sheet_path))
        except (KeyError, ET.ParseError) as exc:
            raise FinanceReconciliationValidationError(
                "xlsx-sheet", f"{source.file_name} 工作表 XML 损坏。"
            ) from exc

    parsed_rows: list[tuple[int, list[str]]] = []
    for row_element in root.findall(f".//{{{_SHEET_NS}}}sheetData/{{{_SHEET_NS}}}row"):
        row_number = _positive_int(row_element.get("r"), "xlsx-row")
        values = [""] * 10
        for cell in row_element.findall(f"{{{_SHEET_NS}}}c"):
            reference = str(cell.get("r") or "")
            matched = re.fullmatch(r"([A-Z]+)([0-9]+)", reference)
            if matched is None or int(matched.group(2)) != row_number:
                raise FinanceReconciliationValidationError(
                    "xlsx-cell-ref", f"{source.file_name} 存在无效单元格引用。"
                )
            column_index = _column_index(matched.group(1))
            value = _cell_text(cell, shared_strings, source.file_name)
            if column_index >= 10:
                if value:
                    raise FinanceReconciliationValidationError(
                        "xlsx-extra-column", f"{source.file_name} 在 J 列之后出现业务值。"
                    )
                continue
            values[column_index] = value
        parsed_rows.append((row_number, values))
    if not parsed_rows or parsed_rows[0][0] != 1:
        raise FinanceReconciliationValidationError(
            "xlsx-header", f"{source.file_name} 缺少第 1 行表头。"
        )
    if tuple(parsed_rows[0][1]) != EXPECTED_HEADERS:
        raise FinanceReconciliationValidationError(
            "xlsx-header",
            f"{source.file_name} 表头必须按位置区分期初方向和期末方向，不能生成 direction#2。",
        )

    output: list[FinanceLedgerRow] = []
    keys: set[tuple[str, str]] = set()
    for row_number, values in parsed_rows[1:]:
        if not any(value.strip() for value in values):
            continue
        subject, customer = values[0].strip(), _clean_customer(values[1])
        if not subject or not customer:
            raise FinanceReconciliationValidationError(
                "xlsx-business-key",
                f"{source.file_name} 第 {row_number} 行缺少科目或客商。",
            )
        opening_direction = values[2].strip()
        ending_direction = values[8].strip()
        if opening_direction not in {"借", "贷", "平"} or ending_direction not in {
            "借",
            "贷",
            "平",
        }:
            raise FinanceReconciliationValidationError(
                "xlsx-direction",
                f"{source.file_name} 第 {row_number} 行存在未知借贷方向。",
            )
        for column in range(3, 8):
            _optional_decimal(
                values[column],
                code="xlsx-amount",
                detail=f"{source.file_name} 第 {row_number} 行金额非法。",
            )
        ending_balance = _optional_decimal(
            values[9],
            code="xlsx-ending-balance",
            detail=f"{source.file_name} 第 {row_number} 行期末余额非法。",
        )
        if ending_balance is None:
            if ending_direction != "平":
                raise FinanceReconciliationValidationError(
                    "xlsx-ending-balance",
                    f"{source.file_name} 第 {row_number} 行非平账方向缺少期末余额。",
                )
            ending_balance = Decimal(0)
        if ending_balance < 0 or (ending_direction == "平" and ending_balance != 0):
            raise FinanceReconciliationValidationError(
                "xlsx-ending-balance",
                f"{source.file_name} 第 {row_number} 行期末方向与余额不一致。",
            )
        key = (subject, customer)
        if key in keys:
            raise FinanceReconciliationValidationError(
                "xlsx-duplicate-key",
                f"{source.file_name} 同一期间出现重复“科目+客商”键：{subject} / {customer}。",
            )
        keys.add(key)
        output.append(
            FinanceLedgerRow(
                period_id=source.period_id,
                period_label=source.period_label,
                source_file_ref=source.file_ref,
                file_name=source.file_name,
                sheet_name=sheet_name,
                row_number=row_number,
                subject=subject,
                customer=customer,
                opening_direction=opening_direction,
                ending_direction=ending_direction,
                ending_balance=ending_balance,
            )
        )
    if not output:
        raise FinanceReconciliationValidationError(
            "xlsx-empty", f"{source.file_name} 没有业务行。"
        )
    return output


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except ET.ParseError as exc:
        raise FinanceReconciliationValidationError(
            "xlsx-shared-strings", "共享字符串表损坏。"
        ) from exc
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{_SHEET_NS}}}t"))
        for item in root.findall(f"{{{_SHEET_NS}}}si")
    ]


def _single_sheet(archive: zipfile.ZipFile) -> tuple[str, str]:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except ET.ParseError as exc:
        raise FinanceReconciliationValidationError(
            "xlsx-workbook", "工作簿元数据损坏。"
        ) from exc
    sheets = workbook.findall(f".//{{{_SHEET_NS}}}sheets/{{{_SHEET_NS}}}sheet")
    if len(sheets) != 1:
        raise FinanceReconciliationValidationError(
            "xlsx-sheet-count", "固定 Finance-018 工作簿必须恰好包含一个工作表。"
        )
    relation_id = sheets[0].get(f"{{{_REL_NS}}}id")
    relation_map = {
        relation.get("Id"): relation.get("Target")
        for relation in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship")
    }
    target = relation_map.get(relation_id)
    if not target:
        raise FinanceReconciliationValidationError(
            "xlsx-sheet-relation", "工作表关系缺失。"
        )
    path = posixpath.normpath(posixpath.join("xl", target.lstrip("/")))
    if _unsafe_archive_name(path):
        raise FinanceReconciliationValidationError(
            "xlsx-sheet-relation", "工作表关系越界。"
        )
    return str(sheets[0].get("name") or "Sheet1"), path


def _cell_text(cell: ET.Element, shared_strings: list[str], file_name: str) -> str:
    if cell.find(f"{{{_SHEET_NS}}}f") is not None:
        raise FinanceReconciliationValidationError(
            "xlsx-formula", f"{file_name} 的业务表包含公式，固定适配器不接受未验证缓存值。"
        )
    cell_type = str(cell.get("t") or "n")
    if cell_type == "e":
        raise FinanceReconciliationValidationError(
            "xlsx-error-cell", f"{file_name} 包含错误单元格。"
        )
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.findall(f".//{{{_SHEET_NS}}}t")
        ).strip()
    value_node = cell.find(f"{{{_SHEET_NS}}}v")
    value = "" if value_node is None else str(value_node.text or "").strip()
    if cell_type == "s":
        try:
            return shared_strings[int(value)].strip()
        except (ValueError, IndexError) as exc:
            raise FinanceReconciliationValidationError(
                "xlsx-shared-string-index", f"{file_name} 共享字符串索引越界。"
            ) from exc
    if cell_type not in {"n", "str"}:
        raise FinanceReconciliationValidationError(
            "xlsx-cell-type", f"{file_name} 包含不支持的单元格类型 {cell_type}。"
        )
    return value


def _candidate_records(
    rows_by_period: dict[str, tuple[FinanceLedgerRow, ...]],
) -> tuple[AgentControlLoopFinanceCandidate, ...]:
    maps = {
        period_id: {row.key: row for row in rows_by_period[period_id]}
        for period_id in PERIOD_ORDER
    }
    common_keys = set.intersection(*(set(period_map) for period_map in maps.values()))
    candidates: list[AgentControlLoopFinanceCandidate] = []
    for subject, customer in sorted(common_keys, key=lambda item: (item[1], item[0])):
        rows = [maps[period_id][(subject, customer)] for period_id in PERIOD_ORDER]
        if not all(row.ending_direction == "借" and row.ending_balance > 0 for row in rows):
            continue
        if len({row.ending_balance for row in rows}) != 1:
            continue
        candidate_id = "finance-candidate-" + hashlib.sha256(
            f"{subject}\0{customer}".encode("utf-8")
        ).hexdigest()[:12]
        candidates.append(
            AgentControlLoopFinanceCandidate(
                candidate_id=candidate_id,
                key=f"{subject} / {customer}",
                subject=subject,
                customer=customer,
                sources=[
                    AgentControlLoopFinanceCandidateSource(
                        period_id=row.period_id,
                        period_label=row.period_label,
                        source_file_ref=row.source_file_ref,
                        file_name=row.file_name,
                        sheet_name=row.sheet_name,
                        row_number=row.row_number,
                        locator=row.locator,
                        ending_balance=_decimal_text(row.ending_balance),
                    )
                    for row in rows
                ],
                review_action=REVIEW_ACTION,
                exit_condition=EXIT_CONDITION,
            )
        )
    return tuple(candidates)


def _detail_csv(rows: tuple[FinanceLedgerRow, ...]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(DETAIL_HEADERS)
    for row in rows:
        writer.writerow(
            (
                row.subject,
                row.customer,
                row.ending_direction,
                _decimal_text(row.ending_balance),
                row.file_name,
                row.source_file_ref,
                row.locator,
            )
        )
    return buffer.getvalue().encode("utf-8-sig")


def _cross_period_markdown(analysis: FinanceAnalysis) -> bytes:
    lines = [
        "# 三期僵尸账款候选核对说明",
        "",
        "> 这是跨期风险候选，不是付款、核销、记账或坏账确认。",
        "",
        "## 本次范围",
        "",
        f"- 2026 期末未付：{len(analysis.unpaid_rows)} 条，合计 {_display_amount(analysis.unpaid_total)}。",
        f"- 2026 期末未收：{len(analysis.unreceived_rows)} 条，合计 {_display_amount(analysis.unreceived_total)}。",
        f"- 跨期僵尸账款候选：{len(analysis.candidates)} 条。",
        "",
        "## 三期来源概况",
        "",
        "| 期间 | 来源文件 | 业务行 | 正数借方期末余额合计 |",
        "|---|---|---:|---:|",
        *(
            "| "
            + " | ".join(
                (
                    str(analysis.period_summaries[period_id]["period_label"]),
                    str(analysis.period_summaries[period_id]["file_name"]),
                    str(analysis.period_summaries[period_id]["row_count"]),
                    str(analysis.period_summaries[period_id]["positive_debit_total"]),
                )
            )
            + " |"
            for period_id in PERIOD_ORDER
        ),
        "",
        "## 候选",
        "",
    ]
    if not analysis.candidates:
        lines.extend(("当前启发式未发现候选，仍需财务复核。", ""))
    else:
        lines.extend(
            (
                "| 候选 | 科目 | 客商 | 2025 上半年 | 2025 下半年 | 2026 |",
                "|---|---|---|---|---|---|",
            )
        )
        for candidate in analysis.candidates:
            cells = []
            for source in candidate.sources:
                cells.append(
                    f"{source.ending_balance}（{source.file_name}，{source.locator}）"
                )
            lines.append(
                "| "
                + " | ".join(
                    (
                        candidate.candidate_id,
                        _markdown_cell(candidate.subject),
                        _markdown_cell(candidate.customer),
                        *(_markdown_cell(cell) for cell in cells),
                    )
                )
                + " |"
            )
        lines.append("")
    lines.extend(
        (
            "## 方法与边界",
            "",
            f"- 方法：{METHOD}",
            *(f"- 局限：{item}" for item in LIMITATIONS),
            f"- 财务复核动作：{REVIEW_ACTION}",
            f"- 退出条件：{EXIT_CONDITION}",
            "- 外部动作：无；FORTE 原始工作簿未修改。",
            "",
            "## 机器可复核摘要",
            "",
            "```json",
            json.dumps(_machine_summary(analysis), ensure_ascii=False, sort_keys=True),
            "```",
            "",
        )
    )
    return "\n".join(lines).encode("utf-8")


def _machine_summary(analysis: FinanceAnalysis) -> dict[str, object]:
    return {
        "period_ids": list(PERIOD_ORDER),
        "period_summaries": analysis.period_summaries,
        "unpaid_count": len(analysis.unpaid_rows),
        "unpaid_total": _decimal_text(analysis.unpaid_total),
        "unreceived_count": len(analysis.unreceived_rows),
        "unreceived_total": _decimal_text(analysis.unreceived_total),
        "candidate_count": len(analysis.candidates),
        "candidates": [candidate.model_dump(mode="json") for candidate in analysis.candidates],
        "method": METHOD,
        "limitations": list(LIMITATIONS),
        "review_action": REVIEW_ACTION,
        "exit_condition": EXIT_CONDITION,
        "external_action": "none",
        "original_inputs_modified": False,
    }


def _verify_detail_artifact(
    artifact_name: str,
    content: bytes,
    expected_rows: tuple[FinanceLedgerRow, ...],
    expected_total: Decimal,
    *,
    prefix: str,
) -> list[FinanceArtifactCheck]:
    parsed_rows: list[tuple[str, ...]] = []
    headers: tuple[str, ...] = ()
    error = ""
    try:
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text, newline=""))
        table = list(reader)
        if not table:
            raise ValueError("CSV 为空")
        headers = tuple(table[0])
        parsed_rows = [tuple(row) for row in table[1:]]
        if any(len(row) != len(DETAIL_HEADERS) for row in parsed_rows):
            raise ValueError("CSV 行列数不一致")
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        error = str(exc)
    expected = [
        (
            row.subject,
            row.customer,
            row.ending_direction,
            _decimal_text(row.ending_balance),
            row.file_name,
            row.source_file_ref,
            row.locator,
        )
        for row in expected_rows
    ]
    shape_ok = not error and headers == DETAIL_HEADERS
    rows_ok = shape_ok and parsed_rows == expected
    unique_ok = rows_ok and len({(row[0], row[1]) for row in parsed_rows}) == len(parsed_rows)
    amount_ok = False
    if rows_ok:
        try:
            amount_ok = sum((_strict_decimal(row[3]) for row in parsed_rows), Decimal(0)) == (
                expected_total
            )
        except FinanceReconciliationValidationError:
            amount_ok = False
    return [
        FinanceArtifactCheck(
            artifact_name,
            f"check-finance-{prefix}-schema",
            "表头与文件结构",
            shape_ok,
            "CSV 表头、UTF-8 编码和每行列数通过复核。" if shape_ok else f"CSV 结构失败：{error or headers}",
        ),
        FinanceArtifactCheck(
            artifact_name,
            f"check-finance-{prefix}-rows",
            "来源行、方向与定位逐字段复算",
            rows_ok,
            f"{len(expected)} 条来源行的科目、客商、方向、金额、file_ref 与 Excel 位置完全一致。",
        ),
        FinanceArtifactCheck(
            artifact_name,
            f"check-finance-{prefix}-unique-sort",
            "唯一键与排序",
            unique_ok,
            "按客商升序、同客商金额降序，且科目+客商不重复。",
        ),
        FinanceArtifactCheck(
            artifact_name,
            f"check-finance-{prefix}-total",
            "记录数与合计复算",
            amount_ok,
            f"{len(expected)} 条记录，合计 {_decimal_text(expected_total)}，均由批准来源重新计算。",
        ),
    ]


def _verify_cross_period_artifact(
    content: bytes, expected: FinanceAnalysis
) -> list[FinanceArtifactCheck]:
    error = ""
    parsed: dict[str, object] = {}
    text = ""
    try:
        text = content.decode("utf-8")
        matched = re.search(r"```json\s*\n([^\n]+)\n```", text)
        if matched is None:
            raise ValueError("缺少机器可复核摘要")
        value = json.loads(matched.group(1))
        if not isinstance(value, dict):
            raise ValueError("机器摘要不是对象")
        parsed = value
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        error = str(exc)
    expected_summary = _machine_summary(expected)
    summary_ok = not error and parsed == expected_summary
    candidate_ok = summary_ok and parsed.get("candidates") == expected_summary["candidates"]
    narrative_ok = (
        summary_ok
        and "这是跨期风险候选，不是付款、核销、记账或坏账确认" in text
        and METHOD in text
        and all(item in text for item in LIMITATIONS)
        and REVIEW_ACTION in text
        and EXIT_CONDITION in text
        and "无僵尸账款" not in text
        and (
            "当前启发式未发现候选，仍需财务复核" in text
            if not expected.candidates
            else f"跨期僵尸账款候选：{len(expected.candidates)} 条" in text
        )
    )
    return [
        FinanceArtifactCheck(
            "跨期核对说明.md",
            "check-finance-source-contract",
            "三期来源合同与业务行解析",
            True,
            "三个固定期间、工作簿结构、行唯一键、方向、金额与 Excel 位置均由原始字节重读。",
        ),
        FinanceArtifactCheck(
            "跨期核对说明.md",
            "check-finance-zombie",
            "候选枚举与来源重算一致",
            candidate_ok,
            f"候选可以为 0 或多条；本次 {len(expected.candidates)} 条与三期来源逐项重算一致。",
        ),
        FinanceArtifactCheck(
            "跨期核对说明.md",
            "check-finance-summary",
            "数量、合计与来源位置",
            summary_ok,
            "未付、未收、候选数量、金额、file_ref 和 locator 与机器摘要一致。"
            if summary_ok
            else f"Markdown 摘要校验失败：{error or '字段被篡改'}。",
        ),
        FinanceArtifactCheck(
            "跨期核对说明.md",
            "check-finance-boundary",
            "启发式边界与人工处置",
            narrative_ok,
            "报告明确候选不是会计结论，不执行付款、核销、记账或坏账确认，并给出人工复核动作。",
        ),
    ]


def _detail_sort_key(row: FinanceLedgerRow) -> tuple[str, Decimal, str]:
    return row.customer, -row.ending_balance, row.subject


def _decimal_text(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f").rstrip("0").rstrip(".")


def _display_amount(value: Decimal) -> str:
    normalized = _decimal_text(value)
    integer, dot, fraction = normalized.partition(".")
    return f"{int(integer):,}" + (f".{fraction}" if dot else "")


def _strict_decimal(value: str) -> Decimal:
    normalized = str(value or "").replace(",", "").strip()
    if not normalized:
        raise FinanceReconciliationValidationError("decimal-empty", "金额为空。")
    try:
        parsed = Decimal(normalized)
    except InvalidOperation as exc:
        raise FinanceReconciliationValidationError("decimal-invalid", "金额不是合法数值。") from exc
    if not parsed.is_finite() or not math.isfinite(float(parsed)):
        raise FinanceReconciliationValidationError("decimal-nonfinite", "金额不是有限数值。")
    return parsed


def _optional_decimal(value: str, *, code: str, detail: str) -> Decimal | None:
    if not str(value or "").strip():
        return None
    try:
        return _strict_decimal(value)
    except FinanceReconciliationValidationError as exc:
        raise FinanceReconciliationValidationError(code, detail) from exc


def _clean_customer(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("【") and cleaned.endswith("】") and len(cleaned) > 2:
        return cleaned[1:-1].strip()
    return cleaned


def _markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _column_index(column: str) -> int:
    value = 0
    for character in column:
        value = value * 26 + ord(character) - ord("A") + 1
    return value - 1


def _positive_int(value: str | None, code: str) -> int:
    try:
        parsed = int(str(value or ""))
    except ValueError as exc:
        raise FinanceReconciliationValidationError(code, "行号不是整数。") from exc
    if parsed <= 0:
        raise FinanceReconciliationValidationError(code, "行号必须大于 0。")
    return parsed


def _unsafe_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return (
        not normalized
        or normalized.startswith("/")
        or re.match(r"^[A-Za-z]:", normalized) is not None
        or ".." in normalized.split("/")
    )
