from __future__ import annotations

import io
import re
import zipfile
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.finance_reconciliation_effect import (
    FinanceReconciliationValidationError,
    FinanceSourceInput,
    analyze_finance_sources,
    build_finance_reconciliation,
    verify_finance_artifacts,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


@pytest.fixture(scope="module")
def sources() -> tuple[FinanceSourceInput, ...]:
    catalog = BenchmarkWorkspaceCatalog(FORTE_ROOT)
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-05")
    return ScenarioEffectEngine._finance_source_inputs(catalog, spec)


def _mutate_sheet(
    content: bytes,
    mutation,
) -> bytes:
    source = zipfile.ZipFile(io.BytesIO(content))
    target = io.BytesIO()
    with source, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for item in source.infolist():
            payload = source.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(payload)
                mutation(root)
                payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            output.writestr(item, payload)
    return target.getvalue()


def _cell(root: ET.Element, reference: str) -> ET.Element:
    found = root.find(f".//{{{SHEET_NS}}}c[@r='{reference}']")
    assert found is not None
    return found


def _set_cell(
    root: ET.Element,
    reference: str,
    value: str,
    *,
    cell_type: str | None = None,
    formula: str | None = None,
) -> None:
    cell = _cell(root, reference)
    if cell_type is None:
        cell.attrib.pop("t", None)
    else:
        cell.set("t", cell_type)
    for child in list(cell):
        cell.remove(child)
    if formula is not None:
        ET.SubElement(cell, f"{{{SHEET_NS}}}f").text = formula
    ET.SubElement(cell, f"{{{SHEET_NS}}}v").text = value


def _replace_source(
    sources: tuple[FinanceSourceInput, ...],
    period_id: str,
    mutation,
) -> tuple[FinanceSourceInput, ...]:
    output: list[FinanceSourceInput] = []
    for source in sources:
        if source.period_id != period_id:
            output.append(source)
            continue
        content = _mutate_sheet(source.content, mutation)
        output.append(replace(source, content=content, declared_size=len(content)))
    return tuple(output)


def test_baseline_recomputes_current_counts_totals_and_zero_candidates(
    sources: tuple[FinanceSourceInput, ...],
) -> None:
    build = build_finance_reconciliation(sources)

    assert len(build.analysis.unpaid_rows) == 31
    assert str(build.analysis.unpaid_total) == "3984606.46"
    assert len(build.analysis.unreceived_rows) == 2
    assert str(build.analysis.unreceived_total) == "4992891.47"
    assert build.analysis.candidates == ()
    assert build.analysis.outcome.candidate_count == 0
    assert all(check.passed for check in build.checks)
    assert "无僵尸账款" not in build.cross_period_markdown.decode("utf-8")
    assert "当前启发式未发现候选，仍需财务复核" in build.cross_period_markdown.decode(
        "utf-8"
    )


def test_positive_candidate_is_a_business_finding_not_a_verifier_failure(
    sources: tuple[FinanceSourceInput, ...],
) -> None:
    mutated = _replace_source(
        sources,
        "2026",
        lambda root: _set_cell(root, "J3", "1500000"),
    )
    build = build_finance_reconciliation(mutated)

    assert build.analysis.outcome.candidate_count == 1
    candidate = build.analysis.outcome.candidates[0]
    assert candidate.customer == "绵阳长城发展融资担保有限公司"
    assert [source.ending_balance for source in candidate.sources] == [
        "1500000",
        "1500000",
        "1500000",
    ]
    assert all(check.passed for check in build.checks)
    assert "发现 1 条" in build.analysis.outcome.decision
    assert "未执行付款、核销、记账或坏账确认" in build.analysis.outcome.decision


def test_mutating_only_an_older_period_keeps_2026_csvs_and_changes_cross_period_note(
    sources: tuple[FinanceSourceInput, ...],
) -> None:
    baseline = build_finance_reconciliation(sources)
    mutated = _replace_source(
        sources,
        "2025_h1",
        lambda root: _set_cell(root, "J5", "1499999"),
    )
    changed = build_finance_reconciliation(mutated)

    assert changed.unpaid_csv == baseline.unpaid_csv
    assert changed.unreceived_csv == baseline.unreceived_csv
    assert changed.cross_period_markdown != baseline.cross_period_markdown
    assert changed.analysis.outcome.candidate_count == 0
    assert all(check.passed for check in changed.checks)


def test_changing_one_period_again_removes_a_positive_candidate(
    sources: tuple[FinanceSourceInput, ...],
) -> None:
    positive = _replace_source(
        sources,
        "2026",
        lambda root: _set_cell(root, "J3", "1500000"),
    )
    removed = _replace_source(
        positive,
        "2025_h2",
        lambda root: _set_cell(root, "J3", "1490000"),
    )

    assert analyze_finance_sources(positive).outcome.candidate_count == 1
    assert analyze_finance_sources(removed).outcome.candidate_count == 0


def test_2026_add_delete_amount_and_direction_mutations_are_scoped(
    sources: tuple[FinanceSourceInput, ...],
) -> None:
    baseline = build_finance_reconciliation(sources)

    def add_row(root: ET.Element) -> None:
        sheet_data = root.find(f".//{{{SHEET_NS}}}sheetData")
        assert sheet_data is not None
        original = next(
            row for row in sheet_data.findall(f"{{{SHEET_NS}}}row") if row.get("r") == "5"
        )
        clone = ET.fromstring(ET.tostring(original))
        clone.set("r", "60")
        for cell in clone.findall(f"{{{SHEET_NS}}}c"):
            old_ref = str(cell.get("r"))
            cell.set("r", re.sub(r"[0-9]+$", "60", old_ref))
        _set_cell(clone, "B60", "新增客商", cell_type="str")
        _set_cell(clone, "J60", "123")
        sheet_data.append(clone)

    added = build_finance_reconciliation(_replace_source(sources, "2026", add_row))
    assert len(added.analysis.unpaid_rows) == len(baseline.analysis.unpaid_rows) + 1

    def delete_row(root: ET.Element) -> None:
        sheet_data = root.find(f".//{{{SHEET_NS}}}sheetData")
        assert sheet_data is not None
        row = next(
            item for item in sheet_data.findall(f"{{{SHEET_NS}}}row") if item.get("r") == "5"
        )
        sheet_data.remove(row)

    deleted = build_finance_reconciliation(_replace_source(sources, "2026", delete_row))
    assert len(deleted.analysis.unpaid_rows) == len(baseline.analysis.unpaid_rows) - 1

    amount_changed = build_finance_reconciliation(
        _replace_source(sources, "2026", lambda root: _set_cell(root, "J5", "341000"))
    )
    assert amount_changed.analysis.unpaid_total != baseline.analysis.unpaid_total
    assert amount_changed.analysis.unreceived_total == baseline.analysis.unreceived_total

    direction_changed = build_finance_reconciliation(
        _replace_source(
            sources,
            "2026",
            lambda root: _set_cell(root, "I3", "18", cell_type="s"),
        )
    )
    assert len(direction_changed.analysis.unreceived_rows) == 1
    assert len(direction_changed.analysis.unpaid_rows) == 32


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda root: _set_cell(root, "I3", "未知", cell_type="str"), "xlsx-direction"),
        (lambda root: _set_cell(root, "J3", "NaN", cell_type="str"), "xlsx-ending-balance"),
        (lambda root: _set_cell(root, "J3", "2", formula="1+1"), "xlsx-formula"),
        (lambda root: _set_cell(root, "J3", "#VALUE!", cell_type="e"), "xlsx-error-cell"),
    ],
)
def test_invalid_direction_amount_formula_and_error_cells_fail_closed(
    sources: tuple[FinanceSourceInput, ...], mutation, code: str
) -> None:
    mutated = _replace_source(sources, "2026", mutation)
    with pytest.raises(FinanceReconciliationValidationError) as raised:
        analyze_finance_sources(mutated)
    assert raised.value.code == code


def test_empty_sheet_and_duplicate_keys_fail_closed(
    sources: tuple[FinanceSourceInput, ...],
) -> None:
    def empty(root: ET.Element) -> None:
        sheet_data = root.find(f".//{{{SHEET_NS}}}sheetData")
        assert sheet_data is not None
        for row in list(sheet_data.findall(f"{{{SHEET_NS}}}row"))[1:]:
            sheet_data.remove(row)

    with pytest.raises(FinanceReconciliationValidationError) as empty_error:
        analyze_finance_sources(_replace_source(sources, "2026", empty))
    assert empty_error.value.code == "xlsx-empty"

    def duplicate(root: ET.Element) -> None:
        _set_cell(root, "A4", "12", cell_type="s")
        _set_cell(root, "B4", "10", cell_type="s")

    with pytest.raises(FinanceReconciliationValidationError) as duplicate_error:
        analyze_finance_sources(_replace_source(sources, "2026", duplicate))
    assert duplicate_error.value.code == "xlsx-duplicate-key"


@pytest.mark.parametrize("change", ["missing", "extra", "wrong-path", "same-content"])
def test_source_bundle_identity_failures_are_closed(
    sources: tuple[FinanceSourceInput, ...], change: str
) -> None:
    mutated = sources
    if change == "missing":
        mutated = sources[:-1]
    elif change == "extra":
        mutated = (*sources, replace(sources[-1], logical_id="finance-extra"))
    elif change == "wrong-path":
        mutated = (
            *sources[:-1],
            replace(sources[-1], display_path="财务管理/错误.xlsx"),
        )
    else:
        mutated = (
            sources[0],
            replace(
                sources[1],
                content=sources[0].content,
                declared_size=len(sources[0].content),
            ),
            sources[2],
        )
    with pytest.raises(FinanceReconciliationValidationError):
        analyze_finance_sources(tuple(mutated))


@pytest.mark.parametrize(
    "tamper",
    [
        "amount",
        "locator",
        "delete-row",
        "duplicate-row",
        "candidate-count",
        "old-fixed-conclusion",
        "corrupt",
    ],
)
def test_independent_verifier_turns_tampered_artifacts_red(
    sources: tuple[FinanceSourceInput, ...], tamper: str
) -> None:
    build = build_finance_reconciliation(sources)
    unpaid = build.unpaid_csv
    unreceived = build.unreceived_csv
    note = build.cross_period_markdown
    if tamper == "amount":
        unpaid = unpaid.replace(b"341677.91", b"341677.92", 1)
    elif tamper == "locator":
        unreceived = unreceived.replace(b"Sheet1!", b"Sheet9!", 1)
    elif tamper in {"delete-row", "duplicate-row"}:
        rows = unpaid.decode("utf-8-sig").splitlines()
        rows = rows[:-1] if tamper == "delete-row" else [*rows, rows[-1]]
        unpaid = ("\n".join(rows) + "\n").encode("utf-8-sig")
    elif tamper == "candidate-count":
        note = note.replace(b'"candidate_count": 0', b'"candidate_count": 1', 1)
    elif tamper == "old-fixed-conclusion":
        note = note.replace(
            "当前启发式未发现候选，仍需财务复核".encode(),
            "无僵尸账款".encode(),
            1,
        )
    else:
        note = b"\xff\xfe\x00"
    checks = verify_finance_artifacts(
        sources,
        unpaid_csv=unpaid,
        unreceived_csv=unreceived,
        cross_period_markdown=note,
    )
    assert any(not check.passed for check in checks)
