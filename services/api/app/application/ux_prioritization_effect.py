"""Source-derived uiux-021 prioritization and independent CSV verification.

The fixed adapter reads the complete approved workbook, the prioritization rule
Markdown and the page-specification DOCX.  It keeps every workbook row, exposes
the controlled operation-to-element mapping as an assumption, and never turns a
priority label into an approved design change or a production action.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import posixpath
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from packages.contracts.harness_models import (
    AgentControlLoopUXGroup,
    AgentControlLoopUXGroupRuleRef,
    AgentControlLoopUXMappingDecision,
    AgentControlLoopUXPrioritizationOutcome,
    AgentControlLoopUXRowDecision,
    AgentControlLoopUXRule,
    AgentControlLoopUXRuleConflict,
    AgentControlLoopUXSpecElement,
)


BEHAVIOR_LOGICAL_ID = "uiux-021-behavior-log"
RULES_LOGICAL_ID = "uiux-021-prioritization-rules"
SPEC_LOGICAL_ID = "uiux-021-page-specification"
SOURCE_ORDER = (BEHAVIOR_LOGICAL_ID, RULES_LOGICAL_ID, SPEC_LOGICAL_ID)
EXPECTED_FILE_NAMES = {
    BEHAVIOR_LOGICAL_ID: "用户交互行为日志.xlsx",
    RULES_LOGICAL_ID: "交互行为痛点及优化规则.md",
    SPEC_LOGICAL_ID: "页面级交互规范.docx",
}
EXPECTED_DISPLAY_PATHS = {
    key: f"用户体验/{name}" for key, name in EXPECTED_FILE_NAMES.items()
}
EXPECTED_FILE_REFS = {
    BEHAVIOR_LOGICAL_ID: "forte-3913d2ccb62b9b02",
    RULES_LOGICAL_ID: "forte-0506a266b89dfef4",
    SPEC_LOGICAL_ID: "forte-3f48165dbc47276d",
}

WORKBOOK_HEADERS = (
    "页面名称",
    "页面路径",
    "操作动作",
    "最终操作结果",
    "痛点类型",
    "失败原因",
    "误触次数",
    "页面退出节点",
    "重试次数",
)
GROUP_HEADERS = (
    "group_id",
    "页面名称",
    "页面路径",
    "操作动作",
    "规范元素",
    "映射状态",
    "映射依据",
    "痛点类型",
    "严重程度",
    "场景次数",
    "全量分母",
    "精确占比",
    "场景频次",
    "优先级",
    "来源优先级处置",
    "规范要求",
    "贡献来源位置",
    "数据质量标记",
    "suggestion_status",
    "待审批模板",
    "规则Refs",
)
ROW_HEADERS = (
    "来源行号",
    "来源位置",
    "页面名称",
    "页面路径",
    "操作动作",
    "最终操作结果",
    "痛点类型",
    "失败原因",
    "误触次数",
    "页面退出节点",
    "重试次数",
    "处理状态",
    "group_id",
    "mapping_id",
    "映射状态",
    "规范元素",
    "duplicate_group_id",
    "duplicate_ordinal",
    "处理原因",
    "数据质量标记",
)
SUGGESTION_STATUS = "no_approved_solution_source"
BOUNDARY = (
    "这是固定公开日志的离线优先级排序，不是用户研究、线上遥测、设计效果证明或自动修复；"
    "具体优化建议仍需 UX 负责人补充和批准，生产界面、发布与实验均未发生。"
)
MAPPING_BASIS = (
    "固定 uiux-021 适配器按批准页面规范中的页面与元素序号建立候选映射；"
    "来源没有批准的操作到规范元素映射表，因此必须由 UX 负责人复核。"
)

# The source does not approve an operation-to-element crosswalk.  These 24
# decisions are therefore deliberately public adapter assumptions, expressed as
# a page-local source-table position rather than silently claiming DOCX support.
CONTROLLED_MAPPING_POSITIONS = {
    ("首页", "点击功能入口图标"): 1,
    ("首页", "点击Banner轮播图"): 2,
    ("首页", "点击最近阅读书籍"): 3,
    ("首页", "点击底部导航Tab"): 4,
    ("首页", "点击搜索框"): 5,
    ("阅读页", "左右滑动翻页"): 1,
    ("阅读页", "点击屏幕中央显示工具栏"): 2,
    ("阅读页", "点击笔记按钮"): 3,
    ("阅读页", "点击字体设置按钮"): 4,
    ("阅读页", "拖拽进度条跳转章节"): 5,
    ("阅读页", "点击退出按钮"): 6,
    ("笔记编辑页", "点击保存按钮"): 1,
    ("笔记编辑页", "关联书摘"): 2,
    ("笔记编辑页", "选择标签"): 3,
    ("笔记编辑页", "点击取消按钮"): 5,
    ("书籍详情页", "点击加入书架按钮"): 2,
    ("书籍详情页", "展开章节目录"): 3,
    ("书籍详情页", "展开书籍简介"): 4,
    ("书籍详情页", "点击相关推荐书籍"): 5,
    ("书籍详情页", "点击返回按钮"): 6,
    ("书架页", "切换网格/列表视图"): 1,
    ("书架页", "点击分类Tab筛选"): 3,
    ("书架页", "点击搜索图标"): 4,
    ("书架页", "长按书籍进入编辑模式"): 5,
}

_SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


class UXPrioritizationValidationError(ValueError):
    """The fixed uiux-021 source or generated artifact contract is invalid."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class UXSourceInput:
    logical_id: str
    file_name: str
    display_path: str
    file_ref: str
    content: bytes
    declared_size: int
    allowlist_verified: bool


@dataclass(frozen=True)
class UXRawRow:
    row_number: int
    page_name: str
    page_path: str
    operation: str
    operation_result: str
    pain_type: str
    failure_reason: str
    misclick_count: int
    exit_node: str
    retry_count: int

    @property
    def locator(self) -> str:
        return f"用户交互行为日志.xlsx:Sheet1!A{self.row_number}:I{self.row_number}"

    @property
    def payload(self) -> tuple[str, ...]:
        return (
            self.page_name,
            self.page_path,
            self.operation,
            self.operation_result,
            self.pain_type,
            self.failure_reason,
            str(self.misclick_count),
            self.exit_node,
            str(self.retry_count),
        )


@dataclass(frozen=True)
class UXParsedRules:
    rules: tuple[AgentControlLoopUXRule, ...]
    severity: dict[str, str]
    severity_order: tuple[str, ...]
    low_threshold: Decimal
    high_threshold: Decimal
    priority_matrix: dict[tuple[str, str], tuple[str, str]]
    conflicts: tuple[AgentControlLoopUXRuleConflict, ...]


@dataclass(frozen=True)
class UXAnalysis:
    outcome: AgentControlLoopUXPrioritizationOutcome
    source_file_refs: tuple[str, ...]


@dataclass(frozen=True)
class UXArtifactCheck:
    check_id: str
    label: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class UXPrioritizationBuild:
    group_csv: bytes
    row_ledger_csv: bytes
    analysis: UXAnalysis
    checks: tuple[UXArtifactCheck, ...]


def build_ux_prioritization(
    sources: tuple[UXSourceInput, ...],
) -> UXPrioritizationBuild:
    """Build both CSVs, then independently reparse source and artifact bytes."""

    analysis = analyze_ux_sources(sources)
    group_csv = _csv_bytes(GROUP_HEADERS, _group_rows(analysis.outcome))
    row_csv = _csv_bytes(ROW_HEADERS, _row_rows(analysis.outcome))
    checks = verify_ux_artifacts(sources, group_csv=group_csv, row_ledger_csv=row_csv)
    return UXPrioritizationBuild(
        group_csv=group_csv,
        row_ledger_csv=row_csv,
        analysis=analysis,
        checks=checks,
    )


def analyze_ux_sources(sources: tuple[UXSourceInput, ...]) -> UXAnalysis:
    by_id = _validate_source_bundle(sources)
    raw_rows = _parse_workbook(by_id[BEHAVIOR_LOGICAL_ID])
    rules = _parse_rules(by_id[RULES_LOGICAL_ID])
    specs = _parse_specs(by_id[SPEC_LOGICAL_ID])
    mappings = _mapping_decisions(raw_rows, specs)
    mapping_by_key = {(item.page_name, item.operation): item for item in mappings}
    duplicate_facts = _duplicate_facts(raw_rows)
    row_decisions, groups = _decide_rows_and_groups(
        raw_rows, rules, specs, mapping_by_key, duplicate_facts
    )
    duplicate_group_count = len({group for group, _ordinal in duplicate_facts.values() if group})
    duplicate_extra_count = sum(ordinal > 1 for _group, ordinal in duplicate_facts.values())
    mapped_spec_ids = {item.spec_id for item in mappings if item.spec_id is not None}
    uncovered_spec_count = sum(spec.spec_id not in mapped_spec_ids for spec in specs)
    priority_counts = {
        priority: sum(group.priority == priority for group in groups)
        for priority in ("P0", "P1", "P2", "P3", "P4")
    }
    outcome = AgentControlLoopUXPrioritizationOutcome(
        outcome_id="ux-prioritization-outcome-uiux-021",
        status="prioritization_review_required",
        decision=(
            "完整日志排序与两份台账已由服务端重算；3% 来源边界、重复事件口径、"
            "操作到规范元素映射和具体优化方案仍需 UX 负责人复核。生产界面、发布和实验均未发生。"
        ),
        summary=(
            f"完整覆盖 {len(raw_rows)}/{len(raw_rows)} 行；"
            f"有痛点 {sum(row.status == 'included' for row in row_decisions)} 行、"
            f"无痛点 {sum(row.status == 'excluded' for row in row_decisions)} 行、"
            f"形成 {len(groups)} 个可排序组合。重复事件未去重。"
        ),
        source_row_count=len(raw_rows),
        analyzed_row_count=len(row_decisions),
        included_pain_row_count=sum(row.status == "included" for row in row_decisions),
        excluded_no_pain_count=sum(row.status == "excluded" for row in row_decisions),
        success_with_pain_count=sum(
            row.operation_result == "成功" and row.pain_type != "无"
            for row in row_decisions
        ),
        group_count=len(groups),
        priority_counts=priority_counts,
        duplicate_group_count=duplicate_group_count,
        duplicate_extra_count=duplicate_extra_count,
        unmapped_count=sum(item.status == "unmapped" for item in mappings),
        uncovered_spec_count=uncovered_spec_count,
        rules=list(rules.rules),
        specs=list(specs),
        mappings=list(mappings),
        groups=list(groups),
        row_decisions=list(row_decisions),
        rule_conflicts=list(rules.conflicts),
    )
    return UXAnalysis(
        outcome=outcome,
        source_file_refs=tuple(by_id[logical_id].file_ref for logical_id in SOURCE_ORDER),
    )


def verify_ux_artifacts(
    sources: tuple[UXSourceInput, ...],
    *,
    group_csv: bytes,
    row_ledger_csv: bytes,
) -> tuple[UXArtifactCheck, ...]:
    """Recompute from approved bytes and compare both independently parsed CSVs."""

    expected = analyze_ux_sources(sources).outcome
    expected_groups = _group_rows(expected)
    expected_rows = _row_rows(expected)
    group_headers, actual_groups, group_error = _parse_csv(group_csv)
    row_headers, actual_rows, row_error = _parse_csv(row_ledger_csv)
    known_rules = {rule.rule_id: rule for rule in expected.rules}
    rule_projection_ok = (
        bool(known_rules)
        and len(known_rules) == len(expected.rules)
        and len({item.conflict_id for item in expected.rule_conflicts})
        == len(expected.rule_conflicts)
        and all(
            ref.rule_id in known_rules
            and ref.locator == known_rules[ref.rule_id].locator
            for group in expected.groups
            for ref in group.rule_refs
        )
        and all(
            (
                group.frequency == "边界待确认"
                and len([ref for ref in group.rule_refs if ref.role == "frequency"]) == 2
                and not [ref for ref in group.rule_refs if ref.role == "priority"]
            )
            or (
                group.frequency != "边界待确认"
                and len([ref for ref in group.rule_refs if ref.role == "frequency"]) == 1
                and len([ref for ref in group.rule_refs if ref.role == "priority"]) == 1
            )
            for group in expected.groups
        )
    )
    checks = (
        UXArtifactCheck(
            "check-ux-source-contract-v2",
            "三份批准来源身份与原始字节",
            True,
            "逻辑 ID、路径、file ref、声明大小、allowlist 和互异冻结字节均已复核。",
        ),
        UXArtifactCheck(
            "check-ux-full-workbook-v2",
            "完整工作簿逐行覆盖",
            expected.analyzed_row_count == expected.source_row_count,
            f"服务端直接读取完整 XLSX，覆盖 {expected.analyzed_row_count}/{expected.source_row_count} 行，不使用 120 行 Preview。",
        ),
        UXArtifactCheck(
            "check-ux-row-conservation-v2",
            "included/excluded/manual_review 守恒",
            len(expected.row_decisions) == expected.source_row_count,
            "每个批准数据行都进入逐行台账，不静默去重或丢弃。",
        ),
        UXArtifactCheck(
            "check-ux-rules-and-conflict-v2",
            "规则、矩阵、冲突与逐组引用",
            rule_projection_ok,
            (
                f"解析 {len(expected.rules)} 条规则；{len(expected.rule_conflicts)} 组来源冲突"
                "与每个聚合组实际采用的规则 ID、来源位置保持一致。"
            ),
        ),
        UXArtifactCheck(
            "check-ux-page-specs-v2",
            "页面规范与元素顺序",
            bool(expected.specs),
            f"从批准 DOCX 解析 {len(expected.specs)} 个规范元素及其顺序和要求。",
        ),
        UXArtifactCheck(
            "check-ux-mapping-boundary-v2",
            "操作映射假设显式保留",
            all(item.review_required for item in expected.mappings),
            f"{len(expected.mappings)} 个操作映射均标为受控适配器假设；未映射 {expected.unmapped_count} 个。",
        ),
        UXArtifactCheck(
            "check-ux-group-math-v2",
            "全量分母、次数与精确占比",
            all(group.denominator == expected.source_row_count for group in expected.groups),
            f"{expected.group_count} 个组合均使用完整 {expected.source_row_count} 行作分母。",
        ),
        UXArtifactCheck(
            "check-ux-priority-matrix-v2",
            "严重度、频次和 P0-P4 来源推导",
            sum(expected.priority_counts.values())
            == sum(group.priority is not None for group in expected.groups),
            (
                f"动态分布 {expected.priority_counts}；"
                f"{sum(group.priority is None for group in expected.groups)} 个边界冲突组合待人工核对。"
            ),
        ),
        UXArtifactCheck(
            "check-ux-group-artifact-v2",
            "交互规范优化方案 CSV 独立复核",
            group_headers == list(GROUP_HEADERS) and actual_groups == expected_groups,
            group_error or f"独立解析并逐字段核对 {len(expected_groups)} 个聚合组合。",
        ),
        UXArtifactCheck(
            "check-ux-row-artifact-v2",
            "逐行归因台账 CSV 独立复核",
            row_headers == list(ROW_HEADERS) and actual_rows == expected_rows,
            row_error or f"独立解析并逐字段核对 {len(expected_rows)} 个原始行裁决。",
        ),
        UXArtifactCheck(
            "check-ux-no-approved-solution-v2",
            "具体优化方案未冒充批准来源",
            all(
                group.suggestion_status == SUGGESTION_STATUS for group in expected.groups
            ),
            "来源只批准排序规则与页面规范；具体方案保留为待 UX 负责人补充/批准的模板。",
        ),
        UXArtifactCheck(
            "check-ux-no-production-action-v2",
            "生产界面、发布和实验均未发生",
            expected.external_action == "none" and not expected.original_inputs_modified,
            "只写隔离 Run Workspace 两份 CSV；不修改原件、生产 UI、发布状态或实验。",
        ),
    )
    return checks


def _validate_source_bundle(sources: tuple[UXSourceInput, ...]) -> dict[str, UXSourceInput]:
    if len(sources) != 3:
        raise UXPrioritizationValidationError(
            "source-count", "uiux-021 必须恰好包含日志、规则和页面规范三份来源。"
        )
    by_id: dict[str, UXSourceInput] = {}
    refs: set[str] = set()
    digests: set[str] = set()
    for source in sources:
        if source.logical_id not in SOURCE_ORDER or source.logical_id in by_id:
            raise UXPrioritizationValidationError(
                "source-logical-id", "来源逻辑 ID 未知或重复。"
            )
        if (
            source.file_name != EXPECTED_FILE_NAMES[source.logical_id]
            or source.display_path != EXPECTED_DISPLAY_PATHS[source.logical_id]
            or source.file_ref != EXPECTED_FILE_REFS[source.logical_id]
        ):
            raise UXPrioritizationValidationError(
                "source-identity", f"{source.logical_id} 的名称、路径或 file ref 不匹配。"
            )
        if not source.allowlist_verified or not source.file_ref:
            raise UXPrioritizationValidationError(
                "source-allowlist", f"{source.file_name} 未通过服务端 allowlist。"
            )
        if not source.content or source.declared_size != len(source.content):
            raise UXPrioritizationValidationError(
                "source-size", f"{source.file_name} 为空或声明大小与冻结字节不一致。"
            )
        digest = hashlib.sha256(source.content).hexdigest()
        if source.file_ref in refs or digest in digests:
            raise UXPrioritizationValidationError(
                "source-duplicate", "file ref 或原始内容重复，不能冒充三份不同来源。"
            )
        by_id[source.logical_id] = source
        refs.add(source.file_ref)
        digests.add(digest)
    if tuple(by_id) != SOURCE_ORDER:
        by_id = {logical_id: by_id[logical_id] for logical_id in SOURCE_ORDER}
    return by_id


def _parse_workbook(source: UXSourceInput) -> tuple[UXRawRow, ...]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(source.content))
    except (OSError, zipfile.BadZipFile) as exc:
        raise UXPrioritizationValidationError("xlsx-corrupt", "行为日志不是可读取的 XLSX。") from exc
    with archive:
        names = archive.namelist()
        _validate_archive(names, archive, kind="xlsx")
        if any(
            name.lower().endswith("vbaproject.bin")
            or "externallinks/" in name.lower()
            for name in names
        ):
            raise UXPrioritizationValidationError(
                "xlsx-active-content", "行为日志含宏或外部链接。"
            )
        shared_strings = _shared_strings(archive)
        sheet_name, sheet_path = _single_sheet(archive)
        try:
            root = ET.fromstring(archive.read(sheet_path))
        except (KeyError, ET.ParseError) as exc:
            raise UXPrioritizationValidationError("xlsx-sheet", "工作表 XML 损坏。") from exc
    parsed: list[tuple[int, list[str]]] = []
    for row_element in root.findall(f".//{{{_SHEET_NS}}}sheetData/{{{_SHEET_NS}}}row"):
        row_number = _positive_int(row_element.get("r"), "xlsx-row")
        cells = row_element.findall(f"{{{_SHEET_NS}}}c")
        if len(cells) != len(WORKBOOK_HEADERS):
            raise UXPrioritizationValidationError(
                "xlsx-sparse-row", f"第 {row_number} 行不是完整的九列表格行。"
            )
        values = [""] * len(WORKBOOK_HEADERS)
        seen_columns: set[int] = set()
        for cell in cells:
            reference = str(cell.get("r") or "")
            matched = re.fullmatch(r"([A-Z]+)([0-9]+)", reference)
            if matched is None or int(matched.group(2)) != row_number:
                raise UXPrioritizationValidationError(
                    "xlsx-cell-ref", f"第 {row_number} 行存在无效单元格引用。"
                )
            column = _column_index(matched.group(1))
            if column >= len(WORKBOOK_HEADERS) or column in seen_columns:
                raise UXPrioritizationValidationError(
                    "xlsx-column", f"第 {row_number} 行存在额外或重复列。"
                )
            seen_columns.add(column)
            values[column] = _cell_text(cell, shared_strings)
        if seen_columns != set(range(len(WORKBOOK_HEADERS))):
            raise UXPrioritizationValidationError(
                "xlsx-column", f"第 {row_number} 行列集合不完整。"
            )
        parsed.append((row_number, values))
    if not parsed or parsed[0][0] != 1 or tuple(parsed[0][1]) != WORKBOOK_HEADERS:
        raise UXPrioritizationValidationError(
            "xlsx-header", "行为日志必须包含唯一、顺序固定的九列表头。"
        )
    row_numbers = [number for number, _values in parsed]
    if row_numbers != list(range(1, len(parsed) + 1)):
        raise UXPrioritizationValidationError(
            "xlsx-row-sequence", "行为日志存在缺失、重复或稀疏行号。"
        )
    rows: list[UXRawRow] = []
    for row_number, values in parsed[1:]:
        if not any(value.strip() for value in values):
            raise UXPrioritizationValidationError("xlsx-empty-row", f"第 {row_number} 行为空。")
        cleaned = [
            _safe_text(
                value,
                row_number=row_number,
                allow_negative_number=index in {6, 8},
            )
            for index, value in enumerate(values)
        ]
        page_name, page_path, operation, result, pain, reason = cleaned[:6]
        if not page_name or not page_path or not operation or not result or not pain:
            raise UXPrioritizationValidationError(
                "xlsx-required", f"第 {row_number} 行缺少页面、路径、操作、结果或痛点。"
            )
        if not page_path.startswith("/"):
            raise UXPrioritizationValidationError(
                "xlsx-page-path", f"第 {row_number} 行页面路径非法。"
            )
        rows.append(
            UXRawRow(
                row_number=row_number,
                page_name=page_name,
                page_path=page_path,
                operation=operation,
                operation_result=result,
                pain_type=pain,
                failure_reason=reason,
                misclick_count=_nonnegative_int(cleaned[6], row_number, "误触次数"),
                exit_node=cleaned[7],
                retry_count=_nonnegative_int(cleaned[8], row_number, "重试次数"),
            )
        )
    if not rows:
        raise UXPrioritizationValidationError("xlsx-empty", "行为日志没有数据行。")
    page_paths: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        page_paths[row.page_name].add(row.page_path)
    conflicting_pages = {page: paths for page, paths in page_paths.items() if len(paths) > 1}
    if conflicting_pages:
        raise UXPrioritizationValidationError(
            "xlsx-page-path-conflict", f"同一页面对应多个路径：{conflicting_pages}。"
        )
    return tuple(rows)


def _parse_rules(source: UXSourceInput) -> UXParsedRules:
    try:
        text = source.content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise UXPrioritizationValidationError("rules-encoding", "规则文件不是 UTF-8。") from exc
    if not text.strip() or "\x00" in text:
        raise UXPrioritizationValidationError("rules-empty", "规则文件为空或损坏。")
    lines = text.splitlines()
    tables = _markdown_tables(lines)
    if len(tables) != 3:
        raise UXPrioritizationValidationError(
            "rules-table-count", "规则文件必须恰好包含严重度、频次和优先级三张表。"
        )
    severity_table, frequency_table, matrix_table = tables
    if severity_table[0][1] != ["痛点类型", "示例", "严重程度"]:
        raise UXPrioritizationValidationError("severity-header", "严重度表头不匹配。")
    severity: dict[str, str] = {}
    rules: list[AgentControlLoopUXRule] = []
    for line_number, cells in severity_table[1:]:
        pain, example, level = cells
        if not pain or pain in severity or level not in {"严重", "中等", "轻微"}:
            raise UXPrioritizationValidationError(
                "severity-row", f"规则第 {line_number} 行痛点或等级重复、未知或含糊。"
            )
        severity[pain] = level
        excerpt = " | ".join(cells)
        parameters = {"severity": level, "example": _strip_html(example)}
        rules.append(
            AgentControlLoopUXRule(
                rule_id=_source_rule_id(
                    kind="severity",
                    semantic_key=_slug_hash(pain),
                    excerpt=excerpt,
                    parameters=parameters,
                ),
                kind="severity",
                name=pain,
                locator=f"交互行为痛点及优化规则.md:L{line_number}",
                excerpt=excerpt,
                parameters=parameters,
            )
        )
    if not severity:
        raise UXPrioritizationValidationError("severity-empty", "严重度规则为空。")
    if frequency_table[0][1] != ["场景档位", "占比阈值", "计算方式"]:
        raise UXPrioritizationValidationError("frequency-header", "频次表头不匹配。")
    frequency_rows: dict[str, tuple[int, list[str]]] = {}
    for line_number, cells in frequency_table[1:]:
        label = _frequency_label(cells[0])
        if label is None or label in frequency_rows:
            raise UXPrioritizationValidationError(
                "frequency-row", f"规则第 {line_number} 行频次档位未知或重复。"
            )
        frequency_rows[label] = (line_number, cells)
    if set(frequency_rows) != {"高频", "中频", "低频"}:
        raise UXPrioritizationValidationError("frequency-set", "频次档位必须为高/中/低三档。")
    high_values = _percents(frequency_rows["高频"][1][1])
    medium_values = _percents(frequency_rows["中频"][1][1])
    low_values = _percents(frequency_rows["低频"][1][1])
    if len(high_values) != 1 or len(medium_values) != 2 or len(low_values) != 1:
        raise UXPrioritizationValidationError("frequency-values", "频次阈值缺失或含糊。")
    high_threshold = high_values[0]
    low_threshold, medium_high = medium_values
    if not (Decimal(0) < low_threshold < high_threshold == medium_high < Decimal(1)):
        raise UXPrioritizationValidationError("frequency-order", "频次阈值顺序冲突或越界。")
    if low_values[0] != low_threshold:
        raise UXPrioritizationValidationError("frequency-low", "低频阈值与中频下界冲突。")
    conflicts: list[AgentControlLoopUXRuleConflict] = []
    medium_line, medium_cells = frequency_rows["中频"]
    low_percent_text = _decimal_text(low_threshold * Decimal(100))
    open_interval_pattern = rf"\(\s*{re.escape(low_percent_text)}%\s*,"
    if "≤" in medium_cells[1] and re.search(open_interval_pattern, medium_cells[2]):
        conflicts.append(
            AgentControlLoopUXRuleConflict(
                conflict_id="ux-conflict-frequency-3-percent-boundary",
                title="3% 频次边界定义不一致",
                locators=[f"交互行为痛点及优化规则.md:L{medium_line}"],
                statement=(
                    f"同一行阈值列包含 {low_percent_text}%，"
                    f"计算说明却把 {low_percent_text}% 放在开区间之外。"
                ),
                impact=(
                    f"当前没有恰好 {low_percent_text}% 的聚合组；"
                    "未来命中边界时必须标记待确认，不能猜测优先级。"
                ),
                status="open",
            )
        )
    for label, (line_number, cells) in frequency_rows.items():
        values = _percents(cells[1])
        excerpt = " | ".join(cells)
        parameters = {
            "thresholds": ",".join(_decimal_text(value) for value in values)
        }
        rules.append(
            AgentControlLoopUXRule(
                rule_id=_source_rule_id(
                    kind="frequency",
                    semantic_key=_frequency_code(label),
                    excerpt=excerpt,
                    parameters=parameters,
                ),
                kind="frequency",
                name=label,
                locator=f"交互行为痛点及优化规则.md:L{line_number}",
                excerpt=excerpt,
                parameters=parameters,
            )
        )
    expected_matrix_header = ["场景频次 \\ 严重程度", "严重", "中等", "轻微"]
    if matrix_table[0][1] != expected_matrix_header:
        raise UXPrioritizationValidationError("matrix-header", "优先级矩阵表头不匹配。")
    matrix: dict[tuple[str, str], tuple[str, str]] = {}
    for line_number, cells in matrix_table[1:]:
        frequency = _frequency_label(cells[0])
        if frequency is None:
            raise UXPrioritizationValidationError(
                "matrix-frequency", f"矩阵第 {line_number} 行频次未知。"
            )
        for index, severity_level in enumerate(("严重", "中等", "轻微"), start=1):
            matched = re.match(r"\*\*(P[0-4])\*\*\s*(.+)", cells[index].strip())
            if matched is None:
                raise UXPrioritizationValidationError(
                    "matrix-cell", f"矩阵第 {line_number} 行缺少唯一 P0-P4 与处置说明。"
                )
            key = (frequency, severity_level)
            if key in matrix:
                raise UXPrioritizationValidationError("matrix-duplicate", "优先级矩阵键重复。")
            priority, disposition = matched.groups()
            matrix[key] = (priority, disposition.strip())
            excerpt = cells[index]
            parameters = {"priority": priority, "disposition": disposition.strip()}
            rules.append(
                AgentControlLoopUXRule(
                    rule_id=_source_rule_id(
                        kind="priority",
                        semantic_key=(
                            f"{_frequency_code(frequency)}-{_severity_code(severity_level)}"
                        ),
                        excerpt=excerpt,
                        parameters=parameters,
                    ),
                    kind="priority",
                    name=f"{frequency}×{severity_level}",
                    locator=f"交互行为痛点及优化规则.md:L{line_number}",
                    excerpt=excerpt,
                    parameters=parameters,
                )
            )
    if set(matrix) != {
        (frequency, level)
        for frequency in ("高频", "中频", "低频")
        for level in ("严重", "中等", "轻微")
    }:
        raise UXPrioritizationValidationError("matrix-coverage", "3×3 优先级矩阵不完整。")
    _validate_rule_narrative(lines, tables)
    return UXParsedRules(
        rules=tuple(rules),
        severity=severity,
        severity_order=tuple(severity),
        low_threshold=low_threshold,
        high_threshold=high_threshold,
        priority_matrix=matrix,
        conflicts=tuple(conflicts),
    )


def _parse_specs(source: UXSourceInput) -> tuple[AgentControlLoopUXSpecElement, ...]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(source.content))
    except (OSError, zipfile.BadZipFile) as exc:
        raise UXPrioritizationValidationError("docx-corrupt", "页面规范不是可读取的 DOCX。") from exc
    with archive:
        names = archive.namelist()
        _validate_archive(names, archive, kind="docx")
        if "word/document.xml" not in names:
            raise UXPrioritizationValidationError("docx-parts", "页面规范缺少 document.xml。")
        if any(
            name.lower().endswith("vbaproject.bin")
            or "embeddings/" in name.lower()
            for name in names
        ):
            raise UXPrioritizationValidationError("docx-active-content", "页面规范含宏或嵌入对象。")
        for name in names:
            if not name.endswith(".rels"):
                continue
            try:
                rels = ET.fromstring(archive.read(name))
            except ET.ParseError as exc:
                raise UXPrioritizationValidationError("docx-rel", "DOCX 关系文件损坏。") from exc
            if any(rel.get("TargetMode") == "External" for rel in rels):
                raise UXPrioritizationValidationError("docx-external", "页面规范含外部关系。")
        try:
            root = ET.fromstring(archive.read("word/document.xml"))
        except ET.ParseError as exc:
            raise UXPrioritizationValidationError("docx-xml", "页面规范正文 XML 损坏。") from exc
    body = root.find(f"{{{_WORD_NS}}}body")
    if body is None:
        raise UXPrioritizationValidationError("docx-body", "页面规范缺少正文。")
    page_name: str | None = None
    page_order = 0
    seen_pages: set[str] = set()
    specs: list[AgentControlLoopUXSpecElement] = []
    table_count = 0
    for child in list(body):
        local = child.tag.rsplit("}", 1)[-1]
        if local == "p":
            text = _word_text(child).strip()
            normalized = re.sub(r"^[（(]?\d+[）)]\s*", "", text).strip()
            if text and text != "页面级交互规范" and normalized:
                page_name = normalized
        elif local == "tbl":
            table_count += 1
            if page_name is None or page_name in seen_pages:
                raise UXPrioritizationValidationError(
                    "docx-page", "每张规范表必须绑定唯一页面标题。"
                )
            page_order += 1
            seen_pages.add(page_name)
            rows = child.findall(f"{{{_WORD_NS}}}tr")
            parsed_rows = [
                [_word_text(cell).strip() for cell in row.findall(f"{{{_WORD_NS}}}tc")]
                for row in rows
            ]
            if not parsed_rows or parsed_rows[0] != ["交互元素", "规范要求"]:
                raise UXPrioritizationValidationError(
                    "docx-header", f"{page_name} 的规范表头不匹配。"
                )
            seen_elements: set[str] = set()
            for element_order, cells in enumerate(parsed_rows[1:], start=1):
                if len(cells) != 2 or not cells[0] or not cells[1] or cells[0] in seen_elements:
                    raise UXPrioritizationValidationError(
                        "docx-spec-row", f"{page_name} 存在空、重复或列数异常的规范元素。"
                    )
                seen_elements.add(cells[0])
                specs.append(
                    AgentControlLoopUXSpecElement(
                        spec_id=f"ux-spec-{_hash12(f'{page_name}|{element_order}|{cells[0]}')}",
                        page_name=page_name,
                        page_order=page_order,
                        element_name=cells[0],
                        element_order=element_order,
                        requirement=cells[1],
                        locator=f"页面级交互规范.docx:T{table_count}R{element_order + 1}",
                    )
                )
    if table_count != 5 or len(seen_pages) != 5 or not specs:
        raise UXPrioritizationValidationError(
            "docx-table-count", "固定 uiux-021 页面规范必须恰好包含五张唯一页面表。"
        )
    return tuple(specs)


def _mapping_decisions(
    rows: tuple[UXRawRow, ...],
    specs: tuple[AgentControlLoopUXSpecElement, ...],
) -> tuple[AgentControlLoopUXMappingDecision, ...]:
    by_page_order = {(spec.page_name, spec.element_order): spec for spec in specs}
    page_candidates: dict[str, list[str]] = defaultdict(list)
    for spec in specs:
        page_candidates[spec.page_name].append(spec.spec_id)
    decisions: list[AgentControlLoopUXMappingDecision] = []
    for page_name, operation in sorted(
        {(row.page_name, row.operation) for row in rows}, key=lambda item: (item[0], item[1])
    ):
        position = CONTROLLED_MAPPING_POSITIONS.get((page_name, operation))
        spec = by_page_order.get((page_name, position)) if position is not None else None
        status = "controlled_adapter_assumption" if spec is not None else "unmapped"
        decisions.append(
            AgentControlLoopUXMappingDecision(
                mapping_id=f"ux-mapping-{_hash12(f'{page_name}|{operation}')}",
                page_name=page_name,
                operation=operation,
                status=status,
                spec_id=spec.spec_id if spec else None,
                element_name=spec.element_name if spec else None,
                candidate_spec_ids=page_candidates.get(page_name, []),
                mapping_basis=(
                    f"{MAPPING_BASIS} 当前候选为该页面规范表第 {position} 项。"
                    if spec is not None
                    else "来源没有可批准的操作到规范元素映射；保留为 unmapped/manual_review。"
                ),
            )
        )
    return tuple(decisions)


def _duplicate_facts(
    rows: tuple[UXRawRow, ...],
) -> dict[int, tuple[str | None, int]]:
    by_payload: dict[tuple[str, ...], list[UXRawRow]] = defaultdict(list)
    for row in rows:
        by_payload[row.payload].append(row)
    facts: dict[int, tuple[str | None, int]] = {}
    for payload_rows in by_payload.values():
        group_id = (
            f"ux-duplicate-{_hash12('|'.join(payload_rows[0].payload))}"
            if len(payload_rows) > 1
            else None
        )
        for ordinal, row in enumerate(payload_rows, start=1):
            facts[row.row_number] = (group_id, ordinal)
    return facts


def _decide_rows_and_groups(
    raw_rows: tuple[UXRawRow, ...],
    rules: UXParsedRules,
    specs: tuple[AgentControlLoopUXSpecElement, ...],
    mapping_by_key: dict[tuple[str, str], AgentControlLoopUXMappingDecision],
    duplicate_facts: dict[int, tuple[str | None, int]],
) -> tuple[tuple[AgentControlLoopUXRowDecision, ...], tuple[AgentControlLoopUXGroup, ...]]:
    specs_by_id = {spec.spec_id: spec for spec in specs}
    scenario_counts = Counter((row.page_name, row.operation) for row in raw_rows)
    operation_set = sorted({row.operation for row in raw_rows})
    quality_flags = {
        row.row_number: _quality_flags(row, raw_rows, operation_set) for row in raw_rows
    }
    grouped_rows: dict[tuple[str, str, str], list[UXRawRow]] = defaultdict(list)
    statuses: dict[int, tuple[str, str, str | None]] = {}
    for row in raw_rows:
        mapping = mapping_by_key[(row.page_name, row.operation)]
        if row.pain_type == "无":
            statuses[row.row_number] = (
                "excluded",
                "无痛点记录仍计入全量分母，但不进入痛点聚合。",
                None,
            )
        elif row.pain_type not in rules.severity:
            statuses[row.row_number] = (
                "manual_review",
                "痛点类型未出现在批准严重度规则中，不能静默归类。",
                None,
            )
        elif mapping.status == "unmapped" or mapping.spec_id is None:
            statuses[row.row_number] = (
                "manual_review",
                "操作没有批准映射，保留原始行等待 UX 负责人确认规范元素。",
                None,
            )
        else:
            group_id = f"ux-group-{_hash12(f'{row.page_name}|{row.operation}|{row.pain_type}')}"
            statuses[row.row_number] = (
                "included",
                "痛点、映射候选和来源规则可用于离线优先级计算。",
                group_id,
            )
            grouped_rows[(row.page_name, row.operation, row.pain_type)].append(row)
    groups: list[AgentControlLoopUXGroup] = []
    rules_by_id = {rule.rule_id: rule for rule in rules.rules}
    rule_ref_by_pain = {
        rule.name: rule.rule_id for rule in rules.rules if rule.kind == "severity"
    }
    frequency_rule_ids = {
        rule.name: rule.rule_id for rule in rules.rules if rule.kind == "frequency"
    }
    priority_rule_ids = {
        rule.name: rule.rule_id for rule in rules.rules if rule.kind == "priority"
    }
    for (page, operation, pain), contributors in grouped_rows.items():
        mapping = mapping_by_key[(page, operation)]
        spec = specs_by_id[str(mapping.spec_id)]
        count = scenario_counts[(page, operation)]
        ratio = Decimal(count) / Decimal(len(raw_rows))
        boundary_ambiguous = ratio == rules.low_threshold and bool(rules.conflicts)
        if boundary_ambiguous:
            frequency = "边界待确认"
            priority = None
            disposition = "3% 来源定义冲突，等待 UX 负责人确认后再计算优先级。"
            frequency_rule_refs = (
                frequency_rule_ids["中频"],
                frequency_rule_ids["低频"],
            )
            priority_rule_ref = None
        else:
            frequency = (
                "高频"
                if ratio >= rules.high_threshold
                else "中频"
                if ratio >= rules.low_threshold
                else "低频"
            )
            priority, disposition = rules.priority_matrix[(frequency, rules.severity[pain])]
            frequency_rule_refs = (frequency_rule_ids[frequency],)
            priority_rule_ref = priority_rule_ids[f"{frequency}×{rules.severity[pain]}"]
        severity_rule_ref = rule_ref_by_pain[pain]
        applied_rule_refs = [
            AgentControlLoopUXGroupRuleRef(
                role="severity",
                rule_id=severity_rule_ref,
                locator=rules_by_id[severity_rule_ref].locator,
                application="applied",
            ),
            *[
                AgentControlLoopUXGroupRuleRef(
                    role="frequency",
                    rule_id=rule_id,
                    locator=rules_by_id[rule_id].locator,
                    application="conflict_side" if boundary_ambiguous else "applied",
                )
                for rule_id in frequency_rule_refs
            ],
        ]
        if priority_rule_ref is not None:
            applied_rule_refs.append(
                AgentControlLoopUXGroupRuleRef(
                    role="priority",
                    rule_id=priority_rule_ref,
                    locator=rules_by_id[priority_rule_ref].locator,
                    application="applied",
                )
            )
        data_flags = sorted(
            {
                flag
                for row in contributors
                for flag in quality_flags[row.row_number]
            }
        )
        if boundary_ambiguous:
            data_flags.append("frequency_boundary_ambiguous")
        groups.append(
            AgentControlLoopUXGroup(
                group_id=f"ux-group-{_hash12(f'{page}|{operation}|{pain}')}",
                page_name=page,
                page_path=contributors[0].page_path,
                operation=operation,
                spec_id=spec.spec_id,
                element_name=spec.element_name,
                pain_type=pain,
                severity=rules.severity[pain],
                scenario_count=count,
                denominator=len(raw_rows),
                ratio=_decimal_text(ratio),
                frequency=frequency,
                priority=priority,
                disposition=disposition,
                spec_requirement=spec.requirement,
                contributing_row_locators=[row.locator for row in contributors],
                mapping_basis=mapping.mapping_basis,
                rule_refs=applied_rule_refs,
                data_quality_flags=data_flags,
                suggestion_template=(
                    f"待 UX 负责人结合“{spec.element_name}”规范、贡献行和产品目标，"
                    "补充具体方案、验证指标与批准记录。"
                ),
            )
        )
    priority_order = {f"P{index}": index for index in range(5)}
    spec_order = {spec.spec_id: (spec.page_order, spec.element_order) for spec in specs}
    pain_order = {pain: index for index, pain in enumerate(rules.severity_order)}
    groups.sort(
        key=lambda item: (
            priority_order.get(str(item.priority), 99),
            *spec_order[item.spec_id],
            pain_order[item.pain_type],
            item.group_id,
        )
    )
    rows: list[AgentControlLoopUXRowDecision] = []
    for raw in raw_rows:
        status, reason, group_id = statuses[raw.row_number]
        mapping = mapping_by_key[(raw.page_name, raw.operation)]
        duplicate_group_id, duplicate_ordinal = duplicate_facts[raw.row_number]
        flags = list(quality_flags[raw.row_number])
        if duplicate_group_id is not None:
            flags.append("duplicate_event_ambiguity")
        rows.append(
            AgentControlLoopUXRowDecision(
                row_number=raw.row_number,
                locator=raw.locator,
                page_name=raw.page_name,
                page_path=raw.page_path,
                operation=raw.operation,
                operation_result=raw.operation_result,
                pain_type=raw.pain_type,
                failure_reason=raw.failure_reason,
                misclick_count=raw.misclick_count,
                exit_node=raw.exit_node,
                retry_count=raw.retry_count,
                status=status,
                group_id=group_id,
                mapping_id=mapping.mapping_id if status != "excluded" else None,
                mapping_status=(mapping.status if status != "excluded" else "not_applicable"),
                duplicate_group_id=duplicate_group_id,
                duplicate_ordinal=duplicate_ordinal,
                reason=reason,
                data_quality_flags=sorted(set(flags)),
            )
        )
    return tuple(rows), tuple(groups)


def _quality_flags(
    row: UXRawRow,
    rows: tuple[UXRawRow, ...],
    operations: list[str],
) -> list[str]:
    flags: list[str] = []
    if row.operation_result == "成功" and row.pain_type != "无":
        flags.append("success_with_pain")
    if row.failure_reason:
        current_variants = _operation_variants(row.operation)
        other_match = False
        for operation in operations:
            if operation == row.operation:
                continue
            if any(
                len(variant) >= 2 and variant in row.failure_reason
                for variant in _operation_variants(operation)
            ):
                other_match = True
                break
        current_match = any(
            len(variant) >= 2 and variant in row.failure_reason for variant in current_variants
        )
        if other_match and not current_match:
            flags.append("possible_operation_reason_mismatch")
    return flags


def _operation_variants(operation: str) -> set[str]:
    variants = {operation}
    stripped = operation
    for token in ("点击", "长按", "拖拽", "展开", "选择", "切换"):
        if stripped.startswith(token):
            stripped = stripped[len(token) :]
            break
    variants.add(stripped)
    variants.add(stripped.replace("按钮", "").replace("图标", ""))
    return {item for item in variants if item}


def _group_rows(outcome: AgentControlLoopUXPrioritizationOutcome) -> list[list[str]]:
    return [
        [
            group.group_id,
            group.page_name,
            group.page_path,
            group.operation,
            group.element_name,
            group.mapping_status,
            group.mapping_basis,
            group.pain_type,
            group.severity,
            str(group.scenario_count),
            str(group.denominator),
            group.ratio,
            group.frequency,
            group.priority or "",
            group.disposition,
            group.spec_requirement,
            _json(group.contributing_row_locators),
            _json(group.data_quality_flags),
            group.suggestion_status,
            group.suggestion_template,
            _json([item.model_dump(mode="json") for item in group.rule_refs]),
        ]
        for group in outcome.groups
    ]


def _row_rows(outcome: AgentControlLoopUXPrioritizationOutcome) -> list[list[str]]:
    mappings = {item.mapping_id: item for item in outcome.mappings}
    return [
        [
            str(row.row_number),
            row.locator,
            row.page_name,
            row.page_path,
            row.operation,
            row.operation_result,
            row.pain_type,
            row.failure_reason,
            str(row.misclick_count),
            row.exit_node,
            str(row.retry_count),
            row.status,
            row.group_id or "",
            row.mapping_id or "",
            row.mapping_status,
            mappings[row.mapping_id].element_name if row.mapping_id else "",
            row.duplicate_group_id or "",
            str(row.duplicate_ordinal),
            row.reason,
            _json(row.data_quality_flags),
        ]
        for row in outcome.row_decisions
    ]


def _csv_bytes(headers: tuple[str, ...], rows: list[list[str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _parse_csv(content: bytes) -> tuple[list[str], list[list[str]], str]:
    try:
        text = content.decode("utf-8-sig")
        rows = list(csv.reader(io.StringIO(text, newline="")))
    except (UnicodeDecodeError, csv.Error) as exc:
        return [], [], f"CSV 无法解析：{exc}"
    if not rows:
        return [], [], "CSV 为空。"
    headers = rows[0]
    if len(headers) != len(set(headers)):
        return headers, [], "CSV 表头重复。"
    if any(len(row) != len(headers) for row in rows[1:]):
        return headers, [], "CSV 存在列数不一致的行。"
    return headers, rows[1:], ""


def _markdown_tables(lines: list[str]) -> list[list[tuple[int, list[str]]]]:
    tables: list[list[tuple[int, list[str]]]] = []
    current: list[tuple[int, list[str]]] = []
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [cell.strip() for cell in stripped.strip("|").split("|")]
            if all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                continue
            current.append((line_number, cells))
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    widths = {len(row) for table in tables for _line, row in table}
    if any(len({len(row) for _line, row in table}) != 1 for table in tables) or not widths:
        raise UXPrioritizationValidationError("rules-table-shape", "Markdown 表格列数不一致。")
    return tables


def _validate_rule_narrative(
    lines: list[str], tables: list[list[tuple[int, list[str]]]]
) -> None:
    table_lines = {line for table in tables for line, _cells in table}
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if (
            not stripped
            or line_number in table_lines
            or stripped.startswith("#")
            or stripped == "---"
            or re.fullmatch(r"\|(?:\s*:?-{3,}:?\s*\|)+", stripped)
        ):
            continue
        if stripped.startswith(">"):
            normalized = stripped.lstrip("> ")
            if normalized.startswith("场景频次 =") and (
                "全量日志" in normalized or "严重程度取痛点识别表" in normalized
            ):
                continue
        raise UXPrioritizationValidationError(
            "rules-unknown-normative",
            f"规则第 {line_number} 行存在未被适配器消费的规范性片段：{stripped[:120]}。",
        )


def _shared_strings(archive: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    try:
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    except ET.ParseError as exc:
        raise UXPrioritizationValidationError("xlsx-shared-strings", "共享字符串表损坏。") from exc
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{_SHEET_NS}}}t"))
        for item in root.findall(f"{{{_SHEET_NS}}}si")
    ]


def _single_sheet(archive: zipfile.ZipFile) -> tuple[str, str]:
    try:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    except (KeyError, ET.ParseError) as exc:
        raise UXPrioritizationValidationError("xlsx-workbook", "工作簿元数据损坏。") from exc
    sheets = workbook.findall(f".//{{{_SHEET_NS}}}sheets/{{{_SHEET_NS}}}sheet")
    if len(sheets) != 1 or sheets[0].get("state") not in {None, "visible"}:
        raise UXPrioritizationValidationError(
            "xlsx-sheet-count", "行为日志必须恰好包含一个可见工作表，不能含隐藏表。"
        )
    relation_id = sheets[0].get(f"{{{_REL_NS}}}id")
    relation_map = {
        relation.get("Id"): relation.get("Target")
        for relation in relationships.findall(f"{{{_PKG_REL_NS}}}Relationship")
    }
    target = relation_map.get(relation_id)
    if not target:
        raise UXPrioritizationValidationError("xlsx-sheet-relation", "工作表关系缺失。")
    path = posixpath.normpath(posixpath.join("xl", str(target).lstrip("/")))
    if _unsafe_archive_name(path) or path not in archive.namelist():
        raise UXPrioritizationValidationError("xlsx-sheet-relation", "工作表关系越界或缺失。")
    return str(sheets[0].get("name") or "Sheet1"), path


def _cell_text(cell: ET.Element, shared_strings: list[str]) -> str:
    if cell.find(f"{{{_SHEET_NS}}}f") is not None:
        raise UXPrioritizationValidationError(
            "xlsx-formula", "行为日志包含公式；固定适配器不接受未验证缓存值。"
        )
    cell_type = str(cell.get("t") or "n")
    if cell_type == "e":
        raise UXPrioritizationValidationError("xlsx-error-cell", "行为日志包含错误单元格。")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{{{_SHEET_NS}}}t"))
    value_node = cell.find(f"{{{_SHEET_NS}}}v")
    value = "" if value_node is None else str(value_node.text or "")
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError) as exc:
            raise UXPrioritizationValidationError(
                "xlsx-shared-string-index", "共享字符串索引越界。"
            ) from exc
    if cell_type not in {"n", "str", "b"}:
        raise UXPrioritizationValidationError(
            "xlsx-cell-type", f"行为日志出现未知单元格类型：{cell_type}。"
        )
    return value


def _word_text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(f".//{{{_WORD_NS}}}t"))


def _validate_archive(names: list[str], archive: zipfile.ZipFile, *, kind: str) -> None:
    if len(names) > 512 or any(_unsafe_archive_name(name) for name in names):
        raise UXPrioritizationValidationError(f"{kind}-archive", "Office 压缩包结构越界。")
    total = sum(info.file_size for info in archive.infolist())
    if total > 30 * 1024 * 1024 or any(info.file_size > 10 * 1024 * 1024 for info in archive.infolist()):
        raise UXPrioritizationValidationError(f"{kind}-archive-size", "Office 文件解压大小越界。")


def _unsafe_archive_name(name: str) -> bool:
    normalized = name.replace("\\", "/")
    return normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized


def _safe_text(
    value: str, *, row_number: int, allow_negative_number: bool = False
) -> str:
    cleaned = value.strip()
    if len(cleaned) > 2_000 or any(ord(character) < 32 and character not in "\t\n\r" for character in cleaned):
        raise UXPrioritizationValidationError(
            "xlsx-text", f"第 {row_number} 行包含越界文本或控制字符。"
        )
    injection_prefix = cleaned.lstrip().startswith(("=", "+", "-", "@"))
    negative_number = allow_negative_number and re.fullmatch(r"-[0-9]+(?:\.[0-9]+)?", cleaned)
    if injection_prefix and not negative_number:
        raise UXPrioritizationValidationError(
            "xlsx-csv-injection", f"第 {row_number} 行包含 CSV 注入前缀。"
        )
    return cleaned


def _nonnegative_int(value: str, row_number: int, field: str) -> int:
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise UXPrioritizationValidationError(
            "xlsx-number", f"第 {row_number} 行 {field} 不是数字。"
        ) from exc
    if not number.is_finite() or number != number.to_integral_value() or not (0 <= number <= 100_000):
        raise UXPrioritizationValidationError(
            "xlsx-number", f"第 {row_number} 行 {field} 必须是 0..100000 的整数。"
        )
    return int(number)


def _positive_int(value: str | None, code: str) -> int:
    try:
        number = int(str(value))
    except (TypeError, ValueError) as exc:
        raise UXPrioritizationValidationError(code, "行号不是正整数。") from exc
    if number <= 0:
        raise UXPrioritizationValidationError(code, "行号不是正整数。")
    return number


def _column_index(label: str) -> int:
    index = 0
    for character in label:
        index = index * 26 + ord(character) - ord("A") + 1
    return index - 1


def _frequency_label(text: str) -> str | None:
    cleaned = re.sub(r"[\*（）()]", "", text)
    for label in ("高频", "中频", "低频"):
        if label in cleaned:
            return label
    return None


def _percents(text: str) -> list[Decimal]:
    return [Decimal(value) / Decimal(100) for value in re.findall(r"([0-9]+(?:\.[0-9]+)?)%", text)]


def _strip_html(text: str) -> str:
    return re.sub(r"<br\s*/?>", "；", text, flags=re.IGNORECASE).replace("·", "").strip()


def _frequency_code(label: str) -> str:
    return {"高频": "high", "中频": "medium", "低频": "low"}[label]


def _severity_code(label: str) -> str:
    return {"严重": "severe", "中等": "medium", "轻微": "minor"}[label]


def _hash12(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _slug_hash(value: str) -> str:
    return _hash12(value)


def _source_rule_id(
    *, kind: str, semantic_key: str, excerpt: str, parameters: dict[str, str]
) -> str:
    """Bind public rule references to both their semantic slot and approved content."""

    content_digest = _hash12(
        _json(
            {
                "kind": kind,
                "semantic_key": semantic_key,
                "excerpt": excerpt,
                "parameters": parameters,
            }
        )
    )
    return f"ux-rule-{kind}-{semantic_key}-{content_digest}"


def _decimal_text(value: Decimal) -> str:
    if not value.is_finite():
        raise UXPrioritizationValidationError("decimal", "计算结果不是有限数。")
    text = format(value.normalize(), "f")
    return "0" if text in {"-0", ""} else text


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def public_ux_manifest(
    sources: tuple[UXSourceInput, ...],
) -> dict[str, object]:
    """Machine-readable public fixture used by Python and browser gates."""

    outcome = analyze_ux_sources(sources).outcome
    return {"ux_prioritization_outcome": outcome.model_dump(mode="json")}


__all__ = [
    "BEHAVIOR_LOGICAL_ID",
    "RULES_LOGICAL_ID",
    "SPEC_LOGICAL_ID",
    "UXArtifactCheck",
    "UXPrioritizationBuild",
    "UXPrioritizationValidationError",
    "UXSourceInput",
    "analyze_ux_sources",
    "build_ux_prioritization",
    "public_ux_manifest",
    "verify_ux_artifacts",
]
