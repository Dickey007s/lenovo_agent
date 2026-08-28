"""Export the TC-05 public E2E fixture from the Python server contract."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path
from xml.etree import ElementTree as ET

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.finance_reconciliation_effect import (
    FinanceSourceInput,
    build_finance_reconciliation,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


ROOT = Path(__file__).resolve().parents[1]
FORTE_ROOT = ROOT / "demo-enterprise-data" / "forte"
OUTPUT = ROOT / "docs" / "evidence" / "manifests" / "tc05-public-finance-review-outcome-20260829.json"
SHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def _artifact(item) -> dict[str, object]:
    return {
        "title": item.title,
        "file_name": item.file_name,
        "media_type": item.media_type,
        "size": len(item.content),
        "source_file_refs": list(item.source_file_refs),
        "validator_id": item.validator_id,
        "verifier_status": item.verifier_status,
        "checks": [check.model_dump(mode="json") for check in item.checks],
        "summary": item.summary,
        "covered_period": item.covered_period,
        "statistic_basis": item.statistic_basis,
        "purpose": item.purpose,
        "record_count": item.record_count,
        "deliverable_type": item.deliverable_type,
        "key_outputs": list(item.key_outputs),
        "key_outputs_label": item.key_outputs_label,
        "review_guidance": item.review_guidance,
        "execution_summary": item.execution_summary,
        "finance_review_outcome": (
            item.finance_review_outcome.model_dump(mode="json")
            if item.finance_review_outcome
            else None
        ),
    }


def _replace_2026_balance(source: FinanceSourceInput) -> FinanceSourceInput:
    source_zip = zipfile.ZipFile(io.BytesIO(source.content))
    target = io.BytesIO()
    with source_zip, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for item in source_zip.infolist():
            payload = source_zip.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                root = ET.fromstring(payload)
                cell = root.find(f".//{{{SHEET_NS}}}c[@r='J3']")
                if cell is None:
                    raise RuntimeError("TC-05 fixture cannot locate J3")
                cell.attrib.pop("t", None)
                for child in list(cell):
                    cell.remove(child)
                ET.SubElement(cell, f"{{{SHEET_NS}}}v").text = "1500000"
                payload = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            output.writestr(item, payload)
    content = target.getvalue()
    return replace(source, content=content, declared_size=len(content))


def main() -> None:
    catalog = BenchmarkWorkspaceCatalog(FORTE_ROOT)
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-05")
    engine = ScenarioEffectEngine()
    execution = engine.execute(spec.instruction, catalog)
    if execution is None:
        raise RuntimeError("TC-05 did not match")
    sources = engine._finance_source_inputs(catalog, spec)
    positive_sources = tuple(
        _replace_2026_balance(source) if source.period_id == "2026" else source
        for source in sources
    )
    positive = build_finance_reconciliation(positive_sources)
    manifest = {
        "schema_version": "tc05-finance-review-public.v1",
        "source_commit": "345c1ec1487139db9dd319787fa9405ba85d1869",
        "instruction": spec.instruction,
        "canonical": {
            "status": execution.status,
            "state": execution.state,
            "action": execution.action,
            "observation": execution.observation,
            "cost": execution.cost,
            "result": execution.result,
            "source_file_refs": list(execution.source_file_refs),
            "prohibited_side_effects": list(execution.prohibited_side_effects),
            "artifacts": [_artifact(item) for item in execution.artifacts],
            "finance_review_outcome": execution.artifacts[0].finance_review_outcome.model_dump(
                mode="json"
            ),
        },
        "positive_candidate": {
            "mutation": "2026往来明细.xlsx J3 从 1700000 改为 1500000，仅用于测试副本",
            "finance_review_outcome": positive.analysis.outcome.model_dump(mode="json"),
            "checks": [
                {
                    "artifact_name": check.artifact_name,
                    "check_id": check.check_id,
                    "label": check.label,
                    "passed": check.passed,
                    "detail": check.detail,
                }
                for check in positive.checks
            ],
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
