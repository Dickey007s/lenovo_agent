from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from services.api.app.application.benchmark_scenario_catalog import (
    BenchmarkScenarioCatalog,
    BenchmarkScenarioError,
)


ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"


def copy_package(tmp_path: Path) -> Path:
    destination = tmp_path / "forte"
    shutil.copytree(ROOT, destination)
    return destination


def test_catalog_indexes_only_three_public_input_workspaces() -> None:
    manifest, scenarios = BenchmarkScenarioCatalog(ROOT).load()

    assert manifest.dataset == "FORTE"
    assert manifest.source_commit == "345c1ec1487139db9dd319787fa9405ba85d1869"
    assert manifest.content_nature == "public_benchmark_input"
    assert [item.task_id for item in scenarios] == [
        "Finance-018",
        "pm-014",
        "Operations-008",
    ]
    assert [len(item.files) for item in scenarios] == [4, 5, 2]
    assert scenarios[0].projection["demo_id"] == "demo1"
    assert scenarios[1].projection["experience_policy"] == "adaptive_team"
    assert scenarios[2].projection["demo_id"] == "demo3"

    finance = scenarios[0]
    workbook = finance.file("Finance-018/input/2026往来明细.xlsx")
    assert workbook.summary["kind"] == "xlsx"
    assert workbook.summary["has_formulas"] is False
    assert workbook.summary["has_macros"] is False
    assert workbook.summary["has_external_links"] is False
    assert workbook.summary["sheets"][0]["state"] == "visible"
    assert workbook.summary["sheets"][0]["dimension"] == "A1:J59"

    instruction = finance.file("Finance-018/task.md")
    assert instruction.role == "task_instruction"
    assert instruction.provenance_only is True
    assert instruction.summary["kind"] == "markdown"
    assert instruction.summary["heading_count"] > 0
    planner_instruction = instruction.summary["planner_instruction"]
    assert "查阅公司近两年的往来明细" in planner_instruction
    assert "rubrics:" not in planner_instruction
    assert "solution_files" not in planner_instruction
    assert "标准答案" not in planner_instruction
    assert "/workspace/input" not in planner_instruction
    assert "/workspace/solution" not in planner_instruction


def test_public_projection_hides_planner_prompt_and_raw_paths() -> None:
    catalog = BenchmarkScenarioCatalog(ROOT)
    public = catalog.public_scenarios()
    assert {item["demo_id"] for item in public} == {"demo1", "demo2", "demo3"}
    required = {
        "title", "goal", "deliverables", "data_boundary", "human_gate_summary",
        "allowed_capabilities", "files",
    }
    for item in public:
        assert required.issubset(item)
        serialized = json.dumps(item, ensure_ascii=False)
        assert "task_instruction" not in serialized
        assert "/workspace/input" not in serialized
        assert "rubrics" not in serialized
        assert "solution_files" not in serialized
        assert "customer-a" not in serialized
        assert "2400" not in serialized
        assert "2680" not in serialized
        assert not re.search(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", serialized)
        assert not re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", serialized)
        assert "input_dir" not in item
        assert all(
            set(file)
            == {"file_ref", "display_label", "display_group", "display_summary"}
            for file in item["files"]
        )
        assert all(re.fullmatch(r"forte-[0-9a-f]{16}", file["file_ref"]) for file in item["files"])
        assert all("/workspace/input" not in file["display_summary"] for file in item["files"])
    finance_files = public[0]["files"]
    assert any("工作表" in file["display_summary"] and "A1:J59" in file["display_summary"] for file in finance_files)
    assert any("列：" in file["display_summary"] for file in finance_files)
    assert public[0]["dataset_version"].startswith("FORTE 公开版本 · ")
    assert len(public[0]["dataset_version"].rsplit("· ", 1)[-1]) == 7


def test_manifest_matches_checkout_bytes(tmp_path: Path) -> None:
    copied_root = copy_package(tmp_path)
    manifest = json.loads((copied_root / "manifest.json").read_text(encoding="utf-8"))
    for task in manifest["tasks"]:
        for entry in task["files"]:
            path = copied_root / entry["path"]
            raw = path.read_bytes()
            assert len(raw) == entry["size"]
            assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


def test_internal_task_has_sanitized_prompt_and_raw_input_with_display_projection() -> None:
    internal = BenchmarkScenarioCatalog(ROOT).internal_task("Operations-008")
    assert "task_instruction" in internal
    assert "/workspace/input" not in internal["task_instruction"]
    assert "rubrics" not in internal["task_instruction"]
    assert internal["files"]
    assert all(file["path"].startswith("Operations-008/input/") for file in internal["files"])
    assert all(file["display_label"] and file["display_group"] and file["display_summary"] for file in internal["files"])
    assert all(re.fullmatch(r"forte-[0-9a-f]{16}", file["file_ref"]) for file in internal["files"])


def test_public_file_preview_exposes_real_rows_without_raw_metadata() -> None:
    catalog = BenchmarkScenarioCatalog(ROOT)
    public = catalog.public_task("Finance-018")
    file_ref = public["files"][0]["file_ref"]
    preview = catalog.public_file("Finance-018", file_ref)

    assert preview["kind"] == "table"
    assert preview["columns"][:3] == ["科目名称", "客商名称", "方向"]
    assert preview["total_rows"] == 75
    assert preview["rows"][0]["row_number"] == 2
    assert "黄杉文化传播有限公司" in preview["rows"][0]["values"][1]
    serialized = json.dumps(preview, ensure_ascii=False)
    assert "Finance-018/input" not in serialized
    assert "sha256" not in serialized
    assert "task_instruction" not in serialized


def test_public_markdown_preview_never_exposes_task_instruction() -> None:
    catalog = BenchmarkScenarioCatalog(ROOT)
    public = catalog.public_task("Operations-008")
    assert len(public["files"]) == 1
    preview = catalog.public_file("Operations-008", public["files"][0]["file_ref"])

    assert preview["kind"] == "markdown"
    assert "外呼" in preview["text"]
    assert "## Prompt" not in preview["text"]
    assert "Grading Criteria" not in preview["text"]
    with pytest.raises(KeyError):
        catalog.public_file("Operations-008", "forte-0000000000000000")


def test_catalog_fails_closed_when_a_declared_file_is_tampered(tmp_path: Path) -> None:
    root = copy_package(tmp_path)
    target = root / "Finance-018" / "input" / "2026往来明细.xlsx"
    raw = bytearray(target.read_bytes())
    raw[-1] ^= 1
    target.write_bytes(raw)

    with pytest.raises(BenchmarkScenarioError, match="完整性"):
        BenchmarkScenarioCatalog(root).load()


def test_catalog_fails_closed_on_extra_task_file(tmp_path: Path) -> None:
    root = copy_package(tmp_path)
    (root / "pm-014" / "input" / "unexpected.txt").write_text("not allowlisted", encoding="utf-8")

    with pytest.raises(BenchmarkScenarioError, match="未声明"):
        BenchmarkScenarioCatalog(root).load()


def test_catalog_fails_closed_on_path_escape_in_manifest(tmp_path: Path) -> None:
    root = copy_package(tmp_path)
    manifest_path = root / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["tasks"][0]["files"][0]["path"] = "Finance-018/input/../task.md"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkScenarioError, match="manifest"):
        BenchmarkScenarioCatalog(root).load()
