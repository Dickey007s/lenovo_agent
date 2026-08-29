from __future__ import annotations

import copy
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
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)
from services.api.app.application.ux_prioritization_effect import (
    BEHAVIOR_LOGICAL_ID,
    RULES_LOGICAL_ID,
    SPEC_LOGICAL_ID,
    UXPrioritizationValidationError,
    UXSourceInput,
    analyze_ux_sources,
    build_ux_prioritization,
    verify_ux_artifacts,
)


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


@pytest.fixture(scope="module")
def sources() -> tuple[UXSourceInput, ...]:
    catalog = BenchmarkWorkspaceCatalog(FORTE_ROOT)
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-15")
    return ScenarioEffectEngine._ux_source_inputs(catalog, spec)


def _source(sources: tuple[UXSourceInput, ...], logical_id: str) -> UXSourceInput:
    return next(item for item in sources if item.logical_id == logical_id)


def _replace_source(
    sources: tuple[UXSourceInput, ...], replacement: UXSourceInput
) -> tuple[UXSourceInput, ...]:
    return tuple(
        replacement if item.logical_id == replacement.logical_id else item
        for item in sources
    )


def _mutated_source(source: UXSourceInput, content: bytes) -> UXSourceInput:
    return replace(source, content=content, declared_size=len(content))


def _rewrite_zip(content: bytes, part_name: str, mutation) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(content))
    target = io.BytesIO()
    with source, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename == part_name:
                root = ET.fromstring(payload)
                mutation(root)
                payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            output.writestr(item, payload)
    return target.getvalue()


def _append_zip_entry(content: bytes, name: str, payload: bytes = b"blocked") -> bytes:
    source = zipfile.ZipFile(io.BytesIO(content))
    target = io.BytesIO()
    with source, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for item in source.infolist():
            output.writestr(item, source.read(item.filename))
        output.writestr(name, payload)
    return target.getvalue()


def _sheet_cell(root: ET.Element, reference: str) -> ET.Element:
    cell = root.find(f".//{{{SHEET_NS}}}c[@r='{reference}']")
    assert cell is not None
    return cell


def _set_inline_text(root: ET.Element, reference: str, value: str) -> None:
    cell = _sheet_cell(root, reference)
    for child in list(cell):
        cell.remove(child)
    cell.set("t", "inlineStr")
    inline = ET.SubElement(cell, f"{{{SHEET_NS}}}is")
    ET.SubElement(inline, f"{{{SHEET_NS}}}t").text = value


def _set_number(root: ET.Element, reference: str, value: str) -> None:
    cell = _sheet_cell(root, reference)
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop("t", None)
    ET.SubElement(cell, f"{{{SHEET_NS}}}v").text = value


def _mutate_workbook(
    sources: tuple[UXSourceInput, ...], mutation
) -> tuple[UXSourceInput, ...]:
    source = _source(sources, BEHAVIOR_LOGICAL_ID)
    content = _rewrite_zip(source.content, "xl/worksheets/sheet1.xml", mutation)
    return _replace_source(sources, _mutated_source(source, content))


def _replace_rule(
    sources: tuple[UXSourceInput, ...], old: str, new: str, *, count: int = 1
) -> tuple[UXSourceInput, ...]:
    source = _source(sources, RULES_LOGICAL_ID)
    text = source.content.decode("utf-8-sig")
    assert old in text
    content = text.replace(old, new, count).encode("utf-8")
    return _replace_source(sources, _mutated_source(source, content))


def _replace_spec_text(
    sources: tuple[UXSourceInput, ...], old: str, new: str
) -> tuple[UXSourceInput, ...]:
    source = _source(sources, SPEC_LOGICAL_ID)

    def mutate(root: ET.Element) -> None:
        candidates: list[list[ET.Element]] = []
        for cell in root.findall(f".//{{{WORD_NS}}}tc"):
            nodes = cell.findall(f".//{{{WORD_NS}}}t")
            if "".join(node.text or "" for node in nodes) == old:
                candidates.append(nodes)
        assert len(candidates) == 1
        candidates[0][0].text = new
        for node in candidates[0][1:]:
            node.text = ""

    content = _rewrite_zip(source.content, "word/document.xml", mutate)
    return _replace_source(sources, _mutated_source(source, content))


def _mutate_csv_cell(
    content: bytes, header: str, replacement, *, row_index: int = 0
) -> bytes:
    rows = list(csv.reader(io.StringIO(content.decode("utf-8-sig"), newline="")))
    column = rows[0].index(header)
    rows[row_index + 1][column] = replacement(rows[row_index + 1][column])
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _append_sheet_row(root: ET.Element, values: tuple[str, ...]) -> None:
    sheet_data = root.find(f".//{{{SHEET_NS}}}sheetData")
    assert sheet_data is not None
    source_row = sheet_data.findall(f"{{{SHEET_NS}}}row")[1]
    row = copy.deepcopy(source_row)
    row_number = len(sheet_data.findall(f"{{{SHEET_NS}}}row")) + 1
    row.set("r", str(row_number))
    for cell in row.findall(f"{{{SHEET_NS}}}c"):
        reference = str(cell.get("r"))
        cell.set("r", f"{reference.rstrip('0123456789')}{row_number}")
    sheet_data.append(row)
    for column, value in zip("ABCDEFGHI", values, strict=True):
        _set_inline_text(root, f"{column}{row_number}", value)


def _group(outcome, page: str, operation: str, pain: str | None = None):
    matches = [
        item
        for item in outcome.groups
        if item.page_name == page
        and item.operation == operation
        and (pain is None or item.pain_type == pain)
    ]
    assert matches
    return matches[0]


def test_canonical_full_workbook_builds_two_independently_verified_ledgers(
    sources: tuple[UXSourceInput, ...],
) -> None:
    build = build_ux_prioritization(sources)
    outcome = build.analysis.outcome

    assert (
        outcome.source_row_count,
        outcome.analyzed_row_count,
        outcome.included_pain_row_count,
        outcome.excluded_no_pain_count,
        outcome.success_with_pain_count,
        outcome.group_count,
    ) == (212, 212, 161, 51, 55, 87)
    assert outcome.priority_counts == {"P0": 25, "P1": 40, "P2": 14, "P3": 6, "P4": 2}
    assert (outcome.duplicate_group_count, outcome.duplicate_extra_count) == (16, 20)
    assert (len(outcome.rules), len(outcome.specs), len(outcome.mappings)) == (21, 28, 24)
    assert (outcome.unmapped_count, outcome.uncovered_spec_count) == (0, 4)
    assert len(outcome.rule_conflicts) == 1
    assert all(check.passed for check in build.checks)
    assert len(build.checks) == 12
    assert len(build.group_csv.decode("utf-8-sig").splitlines()) == 88
    assert len(build.row_ledger_csv.decode("utf-8-sig").splitlines()) == 213
    assert "拆主线程" not in build.group_csv.decode("utf-8-sig")
    assert "no_approved_solution_source" in build.group_csv.decode("utf-8-sig")

    save = _group(outcome, "笔记编辑页", "点击保存按钮")
    assert (save.scenario_count, save.denominator, save.frequency, save.priority) == (
        11,
        212,
        "高频",
        "P0",
    )
    assert save.ratio == "0.05188679245283018867924528302"
    assert save.contributing_row_locators
    assert [ref.role for ref in save.rule_refs] == ["severity", "frequency", "priority"]
    assert all(ref.application == "applied" for ref in save.rule_refs)
    assert all(ref.locator.startswith("交互行为痛点及优化规则.md:L") for ref in save.rule_refs)
    assert all(ref.rule_id in {rule.rule_id for rule in outcome.rules} for ref in save.rule_refs)


def test_tail_rows_change_the_old_preview_answer_and_remain_traceable(
    sources: tuple[UXSourceInput, ...],
) -> None:
    outcome = analyze_ux_sources(sources).outcome
    tail_groups = [
        group
        for group in outcome.groups
        if min(int(locator.split("!A", 1)[1].split(":", 1)[0]) for locator in group.contributing_row_locators)
        > 121
    ]
    assert len(tail_groups) >= 21
    assert any(
        int(locator.split("!A", 1)[1].split(":", 1)[0]) > 121
        for group in outcome.groups
        for locator in group.contributing_row_locators
    )


def test_appending_one_legal_source_row_updates_denominator_and_only_related_group(
    sources: tuple[UXSourceInput, ...],
) -> None:
    canonical = analyze_ux_sources(sources).outcome

    def append_row(root: ET.Element) -> None:
        _append_sheet_row(
            root,
            (
                "笔记编辑页",
                "/note/edit",
                "点击保存按钮",
                "失败",
                "操作卡顿",
                "保存提示延迟",
                "0",
                "保存按钮",
                "1",
            ),
        )

    changed = analyze_ux_sources(_mutate_workbook(sources, append_row)).outcome
    before = _group(canonical, "笔记编辑页", "点击保存按钮", "操作卡顿")
    after = _group(changed, "笔记编辑页", "点击保存按钮", "操作卡顿")

    assert changed.source_row_count == canonical.source_row_count + 1
    assert changed.analyzed_row_count == changed.source_row_count
    assert changed.included_pain_row_count == canonical.included_pain_row_count + 1
    assert after.denominator == 213
    assert after.scenario_count == before.scenario_count + 1
    assert "用户交互行为日志.xlsx:Sheet1!A214:I214" in after.contributing_row_locators
    untouched_before = _group(canonical, "首页", "点击Banner轮播图", "操作卡顿")
    untouched_after = _group(changed, "首页", "点击Banner轮播图", "操作卡顿")
    assert untouched_after.scenario_count == untouched_before.scenario_count


def test_synchronized_new_pain_rule_is_included_instead_of_silently_dropped(
    sources: tuple[UXSourceInput, ...],
) -> None:
    changed_rows = _mutate_workbook(
        sources, lambda root: _set_inline_text(root, "E2", "导航迟疑")
    )
    rules_source = _source(changed_rows, RULES_LOGICAL_ID)
    text = rules_source.content.decode("utf-8-sig")
    marker = "| 动效缺失 |"
    insert_at = text.index(marker)
    line_end = text.index("\n", insert_at)
    new_rule = "\n| 导航迟疑 | · 用户无法判断下一步导航入口 | 中等 |"
    changed_rules = _replace_source(
        changed_rows,
        _mutated_source(
            rules_source,
            (text[:line_end] + new_rule + text[line_end:]).encode("utf-8"),
        ),
    )

    outcome = analyze_ux_sources(changed_rules).outcome
    row = outcome.row_decisions[0]
    group = _group(outcome, "首页", "点击Banner轮播图", "导航迟疑")

    assert row.status == "included"
    assert group.severity == "中等"
    assert any(rule.name == "导航迟疑" for rule in outcome.rules)
    assert next(ref for ref in group.rule_refs if ref.role == "severity").rule_id == next(
        rule.rule_id for rule in outcome.rules if rule.name == "导航迟疑"
    )


def test_threshold_matrix_and_page_spec_mutations_are_source_driven(
    sources: tuple[UXSourceInput, ...],
) -> None:
    changed_threshold = sources
    replacements = (
        ("单场景操作占比 ≥ 5%", "单场景操作占比 ≥ 9%"),
        ("结果 ≥ 5% 即为高频", "结果 ≥ 9% 即为高频"),
        ("3% ≤ 单场景操作占比 < 5%", "3% ≤ 单场景操作占比 < 9%"),
        ("(3%, 5%)", "(3%, 9%)"),
    )
    for old, new in replacements:
        changed_threshold = _replace_rule(changed_threshold, old, new)
    threshold_outcome = build_ux_prioritization(changed_threshold).analysis.outcome
    save = _group(threshold_outcome, "笔记编辑页", "点击保存按钮")
    assert save.frequency == "中频"
    assert save.priority == "P1"
    canonical_save = _group(analyze_ux_sources(sources).outcome, "笔记编辑页", "点击保存按钮")
    canonical_frequency = next(ref.rule_id for ref in canonical_save.rule_refs if ref.role == "frequency")
    threshold_frequency = next(ref.rule_id for ref in save.rule_refs if ref.role == "frequency")
    canonical_priority = next(ref.rule_id for ref in canonical_save.rule_refs if ref.role == "priority")
    threshold_priority = next(ref.rule_id for ref in save.rule_refs if ref.role == "priority")
    assert canonical_frequency != threshold_frequency
    assert canonical_priority != threshold_priority
    canonical_high_rule = next(
        rule.rule_id
        for rule in analyze_ux_sources(sources).outcome.rules
        if rule.kind == "frequency" and rule.name == "高频"
    )
    threshold_high_rule = next(
        rule.rule_id
        for rule in threshold_outcome.rules
        if rule.kind == "frequency" and rule.name == "高频"
    )
    assert canonical_high_rule != threshold_high_rule
    assert threshold_outcome.priority_counts != analyze_ux_sources(sources).outcome.priority_counts

    changed_matrix = _replace_rule(
        sources,
        "**P0** 当前版本立即修复，阻塞发布",
        "**P1** 本迭代内修复，不可延期",
    )
    matrix_outcome = build_ux_prioritization(changed_matrix).analysis.outcome
    matrix_save = _group(matrix_outcome, "笔记编辑页", "点击保存按钮")
    assert matrix_save.priority == "P1"
    matrix_priority = next(
        ref.rule_id for ref in matrix_save.rule_refs if ref.role == "priority"
    )
    assert matrix_priority != canonical_priority

    changed_severity = _replace_rule(sources, " | 严重 |", " | 中等 |")
    severity_outcome = build_ux_prioritization(changed_severity).analysis.outcome
    severity_group = _group(
        severity_outcome, "首页", "点击Banner轮播图", "操作卡顿"
    )
    canonical_severity_group = _group(
        analyze_ux_sources(sources).outcome, "首页", "点击Banner轮播图", "操作卡顿"
    )
    assert severity_group.severity == "中等"
    assert severity_group.priority == "P1"
    assert next(
        ref.rule_id for ref in severity_group.rule_refs if ref.role == "severity"
    ) != next(
        ref.rule_id
        for ref in canonical_severity_group.rule_refs
        if ref.role == "severity"
    )

    changed_spec = _replace_spec_text(
        sources,
        '点击保存按钮，点击后编辑状态下显示"草稿已保存"提示',
        '点击保存按钮后立即显示"草稿已保存"提示，并保留错误恢复入口',
    )
    spec_outcome = build_ux_prioritization(changed_spec).analysis.outcome
    assert "错误恢复入口" in _group(
        spec_outcome, "笔记编辑页", "点击保存按钮"
    ).spec_requirement

    def swap_note_spec_rows(root: ET.Element) -> None:
        tables = root.findall(f".//{{{WORD_NS}}}tbl")
        assert len(tables) == 5
        table = tables[2]
        rows = table.findall(f"{{{WORD_NS}}}tr")
        assert len(rows) >= 3
        first_index = list(table).index(rows[1])
        second_index = list(table).index(rows[2])
        first = copy.deepcopy(rows[1])
        second = copy.deepcopy(rows[2])
        table.remove(rows[2])
        table.remove(rows[1])
        table.insert(first_index, second)
        table.insert(second_index, first)

    spec_source = _source(sources, SPEC_LOGICAL_ID)
    reordered_sources = _replace_source(
        sources,
        _mutated_source(
            spec_source,
            _rewrite_zip(
                spec_source.content, "word/document.xml", swap_note_spec_rows
            ),
        ),
    )
    reordered = build_ux_prioritization(reordered_sources).analysis.outcome
    reordered_save = _group(reordered, "笔记编辑页", "点击保存按钮")
    assert reordered_save.element_name == "关联书摘"
    assert reordered_save.spec_requirement != canonical_save.spec_requirement


def test_exact_three_percent_boundary_stays_manual_instead_of_guessing(
    sources: tuple[UXSourceInput, ...],
) -> None:
    def keep_first_two_hundred(root: ET.Element) -> None:
        sheet_data = root.find(f".//{{{SHEET_NS}}}sheetData")
        assert sheet_data is not None
        for row in list(sheet_data.findall(f"{{{SHEET_NS}}}row")):
            if int(str(row.get("r"))) > 201:
                sheet_data.remove(row)

    outcome = analyze_ux_sources(_mutate_workbook(sources, keep_first_two_hundred)).outcome
    boundary_groups = [
        group
        for group in outcome.groups
        if group.page_name == "书籍详情页" and group.operation == "展开书籍简介"
    ]
    assert outcome.source_row_count == 200
    assert boundary_groups
    assert all(group.scenario_count == 6 for group in boundary_groups)
    assert all(group.ratio == "0.03" for group in boundary_groups)
    assert all(group.frequency == "边界待确认" and group.priority is None for group in boundary_groups)
    assert all("frequency_boundary_ambiguous" in group.data_quality_flags for group in boundary_groups)
    assert all(
        len([ref for ref in group.rule_refs if ref.role == "frequency"]) == 2
        and not [ref for ref in group.rule_refs if ref.role == "priority"]
        and all(
            ref.application == "conflict_side"
            for ref in group.rule_refs
            if ref.role == "frequency"
        )
        for group in boundary_groups
    )
    assert all(check.passed for check in build_ux_prioritization(_mutate_workbook(sources, keep_first_two_hundred)).checks)


def test_resolved_three_percent_source_conflict_still_verifies(
    sources: tuple[UXSourceInput, ...],
) -> None:
    resolved = _replace_rule(sources, "(3%, 5%)", "[3%, 5%)")
    build = build_ux_prioritization(resolved)

    assert build.analysis.outcome.rule_conflicts == []
    assert all(group.frequency != "边界待确认" for group in build.analysis.outcome.groups)
    assert all(check.passed for check in build.checks)
    rule_check = next(
        check for check in build.checks if check.check_id == "check-ux-rules-and-conflict-v2"
    )
    assert "0 组来源冲突" in rule_check.detail


def test_unknown_pain_page_and_operation_are_preserved_for_manual_review(
    sources: tuple[UXSourceInput, ...],
) -> None:
    unknown_pain = _mutate_workbook(
        sources, lambda root: _set_inline_text(root, "E2", "新增未知痛点")
    )
    pain_outcome = analyze_ux_sources(unknown_pain).outcome
    assert pain_outcome.row_decisions[0].status == "manual_review"
    assert "痛点类型未出现在" in pain_outcome.row_decisions[0].reason
    assert pain_outcome.analyzed_row_count == 212

    def new_page(root: ET.Element) -> None:
        _set_inline_text(root, "A2", "新增页面")
        _set_inline_text(root, "B2", "/new-page")
        _set_inline_text(root, "C2", "新增操作")

    page_outcome = analyze_ux_sources(_mutate_workbook(sources, new_page)).outcome
    assert page_outcome.unmapped_count == 1
    assert page_outcome.row_decisions[0].status == "manual_review"
    assert page_outcome.row_decisions[0].mapping_status == "unmapped"


def test_duplicate_events_are_not_silently_deduplicated(
    sources: tuple[UXSourceInput, ...],
) -> None:
    outcome = analyze_ux_sources(sources).outcome
    duplicate_rows = [row for row in outcome.row_decisions if row.duplicate_group_id]
    assert len(duplicate_rows) == outcome.duplicate_group_count + outcome.duplicate_extra_count
    assert all("duplicate_event_ambiguity" in row.data_quality_flags for row in duplicate_rows)
    assert outcome.source_row_count == 212


@pytest.mark.parametrize("change", ["missing", "extra", "wrong-path", "same-content"])
def test_source_bundle_identity_failures_are_closed(
    sources: tuple[UXSourceInput, ...], change: str
) -> None:
    mutated = sources
    if change == "missing":
        mutated = sources[:-1]
    elif change == "extra":
        mutated = (*sources, replace(sources[-1], logical_id="uiux-021-extra"))
    elif change == "wrong-path":
        mutated = (*sources[:-1], replace(sources[-1], display_path="用户体验/错误.docx"))
    else:
        mutated = (
            sources[0],
            replace(sources[1], content=sources[0].content, declared_size=len(sources[0].content)),
            sources[2],
        )
    with pytest.raises(UXPrioritizationValidationError):
        analyze_ux_sources(tuple(mutated))


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda root: _set_number(root, "G2", "-1"), "xlsx-number"),
        (lambda root: _set_inline_text(root, "G2", "1.5"), "xlsx-number"),
        (lambda root: _set_inline_text(root, "C2", "=HYPERLINK('x')"), "xlsx-csv-injection"),
        (lambda root: _set_inline_text(root, "A2", "页" * 2001), "xlsx-text"),
    ],
)
def test_invalid_workbook_values_fail_closed(
    sources: tuple[UXSourceInput, ...], mutation, code: str
) -> None:
    with pytest.raises(UXPrioritizationValidationError) as captured:
        analyze_ux_sources(_mutate_workbook(sources, mutation))
    assert captured.value.code == code


def test_formula_sparse_duplicate_header_and_corrupt_inputs_fail_closed(
    sources: tuple[UXSourceInput, ...],
) -> None:
    def formula(root: ET.Element) -> None:
        cell = _sheet_cell(root, "G2")
        for child in list(cell):
            cell.remove(child)
        cell.attrib.pop("t", None)
        ET.SubElement(cell, f"{{{SHEET_NS}}}f").text = "1+1"
        ET.SubElement(cell, f"{{{SHEET_NS}}}v").text = "2"

    def sparse(root: ET.Element) -> None:
        row = root.find(f".//{{{SHEET_NS}}}row[@r='2']")
        assert row is not None
        row.remove(_sheet_cell(root, "I2"))

    def duplicate_header(root: ET.Element) -> None:
        _set_inline_text(root, "B1", "页面名称")

    variants = (
        (_mutate_workbook(sources, formula), "xlsx-formula"),
        (_mutate_workbook(sources, sparse), "xlsx-sparse-row"),
        (_mutate_workbook(sources, duplicate_header), "xlsx-header"),
    )
    for mutated, code in variants:
        with pytest.raises(UXPrioritizationValidationError) as captured:
            analyze_ux_sources(mutated)
        assert captured.value.code == code

    behavior = _source(sources, BEHAVIOR_LOGICAL_ID)
    corrupt = _replace_source(sources, _mutated_source(behavior, b"not-an-xlsx"))
    with pytest.raises(UXPrioritizationValidationError) as captured:
        analyze_ux_sources(corrupt)
    assert captured.value.code == "xlsx-corrupt"


@pytest.mark.parametrize("variant", ["multi-sheet", "hidden-sheet", "external", "macro", "truncated"])
def test_workbook_structure_and_active_content_fail_closed(
    sources: tuple[UXSourceInput, ...], variant: str
) -> None:
    behavior = _source(sources, BEHAVIOR_LOGICAL_ID)
    content = behavior.content
    if variant == "multi-sheet":
        def add_sheet(root: ET.Element) -> None:
            sheets = root.find(f".//{{{SHEET_NS}}}sheets")
            assert sheets is not None
            clone = copy.deepcopy(sheets.findall(f"{{{SHEET_NS}}}sheet")[0])
            clone.set("name", "Extra")
            sheets.append(clone)

        content = _rewrite_zip(content, "xl/workbook.xml", add_sheet)
    elif variant == "hidden-sheet":
        content = _rewrite_zip(
            content,
            "xl/workbook.xml",
            lambda root: root.find(f".//{{{SHEET_NS}}}sheet").set("state", "hidden"),
        )
    elif variant == "external":
        content = _append_zip_entry(content, "xl/externalLinks/externalLink1.xml")
    elif variant == "macro":
        content = _append_zip_entry(content, "xl/vbaProject.bin")
    else:
        content = content[:-32]

    with pytest.raises(UXPrioritizationValidationError) as captured:
        analyze_ux_sources(
            _replace_source(sources, _mutated_source(behavior, content))
        )
    assert captured.value.code in {"xlsx-sheet-count", "xlsx-active-content", "xlsx-corrupt"}


@pytest.mark.parametrize("variant", ["extra-table", "missing-table", "external", "macro", "truncated"])
def test_page_spec_table_and_active_content_fail_closed(
    sources: tuple[UXSourceInput, ...], variant: str
) -> None:
    spec = _source(sources, SPEC_LOGICAL_ID)
    content = spec.content
    if variant == "extra-table":
        def add_table(root: ET.Element) -> None:
            body = root.find(f"{{{WORD_NS}}}body")
            assert body is not None
            tables = body.findall(f"{{{WORD_NS}}}tbl")
            assert tables
            section = body.find(f"{{{WORD_NS}}}sectPr")
            insert_at = len(list(body)) if section is None else list(body).index(section)
            paragraph = ET.Element(f"{{{WORD_NS}}}p")
            run = ET.SubElement(paragraph, f"{{{WORD_NS}}}r")
            ET.SubElement(run, f"{{{WORD_NS}}}t").text = "新增页面"
            body.insert(insert_at, paragraph)
            body.insert(insert_at + 1, copy.deepcopy(tables[0]))

        content = _rewrite_zip(content, "word/document.xml", add_table)
    elif variant == "missing-table":
        def remove_table(root: ET.Element) -> None:
            body = root.find(f"{{{WORD_NS}}}body")
            assert body is not None
            tables = body.findall(f"{{{WORD_NS}}}tbl")
            body.remove(tables[-1])

        content = _rewrite_zip(content, "word/document.xml", remove_table)
    elif variant == "external":
        content = _append_zip_entry(
            content,
            "word/_rels/extra.xml.rels",
            b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rIdX" Type="x" Target="https://example.com" TargetMode="External"/></Relationships>',
        )
    elif variant == "macro":
        content = _append_zip_entry(content, "word/vbaProject.bin")
    else:
        content = content[:-32]

    with pytest.raises(UXPrioritizationValidationError) as captured:
        analyze_ux_sources(_replace_source(sources, _mutated_source(spec, content)))
    assert captured.value.code in {
        "docx-table-count",
        "docx-active-content",
        "docx-external",
        "docx-corrupt",
    }


@pytest.mark.parametrize(
    ("suffix", "code"),
    [
        ("\n必须自动发布生产界面。\n", "rules-unknown-normative"),
        ("\n| 第四档 | 10% | 未知规则 |\n", "rules-table-count"),
    ],
)
def test_unknown_normative_rules_do_not_disappear(
    sources: tuple[UXSourceInput, ...], suffix: str, code: str
) -> None:
    source = _source(sources, RULES_LOGICAL_ID)
    mutated = _replace_source(
        sources, _mutated_source(source, source.content + suffix.encode("utf-8"))
    )
    with pytest.raises(UXPrioritizationValidationError) as captured:
        analyze_ux_sources(mutated)
    assert captured.value.code == code


def test_output_tampering_cannot_self_verify(
    sources: tuple[UXSourceInput, ...],
) -> None:
    build = build_ux_prioritization(sources)
    group_text = build.group_csv.decode("utf-8-sig")
    row_text = build.row_ledger_csv.decode("utf-8-sig")
    mutations = (
        (
            group_text.replace(",P0,", ",P4,", 1).encode("utf-8-sig"),
            build.row_ledger_csv,
        ),
        (
            group_text.replace("Sheet1!", "Sheet9!", 1).encode("utf-8-sig"),
            build.row_ledger_csv,
        ),
        (
            build.group_csv,
            row_text.replace(",included,", ",excluded,", 1).encode("utf-8-sig"),
        ),
        (build.group_csv, b"\xff\xfe\x00"),
    )
    for group_csv, row_csv in mutations:
        checks = verify_ux_artifacts(
            sources, group_csv=group_csv, row_ledger_csv=row_csv
        )
        assert any(not check.passed for check in checks)


@pytest.mark.parametrize(
    ("artifact", "mutation"),
    [
        ("group", lambda content: _mutate_csv_cell(content, "全量分母", lambda value: str(int(value) + 1))),
        ("group", lambda content: _mutate_csv_cell(content, "场景次数", lambda value: str(int(value) + 1))),
        ("group", lambda content: _mutate_csv_cell(content, "规范要求", lambda value: value + "（被篡改）")),
        ("group", lambda content: _mutate_csv_cell(content, "suggestion_status", lambda _value: "approved")),
        ("group", lambda content: b"\n".join(content.splitlines()[:-1]) + b"\n"),
        ("group", lambda content: content + content.splitlines(keepends=True)[1]),
        ("row", lambda content: b"\n".join(content.splitlines()[:-1]) + b"\n"),
        ("row", lambda content: content + content.splitlines(keepends=True)[1]),
    ],
)
def test_denominator_spec_boundary_and_row_set_tampering_turns_verifier_red(
    sources: tuple[UXSourceInput, ...], artifact: str, mutation
) -> None:
    build = build_ux_prioritization(sources)
    group_csv = build.group_csv
    row_csv = build.row_ledger_csv
    if artifact == "group":
        group_csv = mutation(group_csv)
    else:
        row_csv = mutation(row_csv)

    checks = verify_ux_artifacts(sources, group_csv=group_csv, row_ledger_csv=row_csv)
    assert any(not check.passed for check in checks)
