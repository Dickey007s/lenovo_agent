from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from services.api.app.application.benchmark_scenario_catalog import (
    BenchmarkScenarioError,
)
from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)


ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"


def copy_package(tmp_path: Path) -> Path:
    destination = tmp_path / "forte"
    shutil.copytree(ROOT, destination)
    return destination


def public_files(workspace: dict[str, object]) -> list[dict[str, object]]:
    folders = workspace["folders"]
    assert isinstance(folders, list)
    return [item for folder in folders for item in folder["files"]]


def test_workspace_indexes_complete_pinned_public_suite() -> None:
    catalog = BenchmarkWorkspaceCatalog(ROOT)
    manifest, folders = catalog.load()
    workspace = catalog.public_workspace()

    assert manifest.source_commit == "345c1ec1487139db9dd319787fa9405ba85d1869"
    assert manifest.scope.full_benchmark_task_count_reported_by_upstream == 180
    assert manifest.scope.public_demo_task_count == 15
    assert len(folders) == workspace["folder_count"] == 15
    assert workspace["file_count"] == workspace["previewable_file_count"] == 96
    assert sum(folder["file_count"] for folder in workspace["folders"]) == 96
    assert {file["extension"] for file in public_files(workspace)}.issuperset(
        {"XLSX", "CSV", "PDF", "DOCX", "TXT"}
    )
    assert {folder["display_label"] for folder in workspace["folders"]}.issuperset(
        {"财务管理", "人力招聘", "综合办公", "可靠性工程"}
    )
    assert any(folder["file_count"] == 0 for folder in workspace["folders"])


def test_public_workspace_hides_benchmark_prompts_paths_and_hashes() -> None:
    workspace = BenchmarkWorkspaceCatalog(ROOT).public_workspace()
    serialized = json.dumps(workspace, ensure_ascii=False)

    assert workspace["workspace_id"] == "forte-public-office"
    assert "task_instruction" not in serialized
    assert "task.md" not in serialized
    assert "solution" not in serialized.lower()
    assert "rubric" not in serialized.lower()
    assert "/workspace/input" not in serialized
    assert "\\" not in serialized
    assert "sha256" not in serialized
    assert not re.search(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])", serialized)
    assert not re.search(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", serialized)
    assert all(
        re.fullmatch(r"forte-[0-9a-f]{16}", str(file["file_ref"]))
        for file in public_files(workspace)
    )


@pytest.mark.parametrize(
    ("extension", "expected_kind"),
    [("CSV", "table"), ("PDF", "pdf"), ("DOCX", "document"), ("TXT", "text")],
)
def test_csv_pdf_docx_txt_previews_are_bounded_and_safe(
    extension: str, expected_kind: str
) -> None:
    catalog = BenchmarkWorkspaceCatalog(ROOT)
    workspace = catalog.public_workspace()
    item = next(file for file in public_files(workspace) if file["extension"] == extension)
    preview = catalog.public_file(str(item["file_ref"]))
    serialized = json.dumps(preview, ensure_ascii=False)

    assert preview["kind"] == expected_kind
    assert preview["security"] == {
        "integrity_verified": True,
        "read_only": True,
        "active_content_executed": False,
        "external_resources_loaded": False,
        "notes": preview["security"]["notes"],
    }
    assert preview["security"]["notes"]
    assert "sha256" not in serialized
    assert "task_instruction" not in serialized
    assert str(item["display_path"]) in serialized
    if expected_kind == "table":
        assert preview["total_rows"] is not None
        assert preview["rows"]
    else:
        assert preview["text"]


def test_all_96_public_files_have_a_safe_preview() -> None:
    catalog = BenchmarkWorkspaceCatalog(ROOT)
    workspace = catalog.public_workspace()

    previews = [catalog.public_file(str(file["file_ref"])) for file in public_files(workspace)]

    assert len(previews) == 96
    assert {preview["kind"] for preview in previews} == {
        "table",
        "document",
        "pdf",
        "text",
    }
    assert all(preview["security"]["integrity_verified"] for preview in previews)


def test_agent_inputs_are_selected_only_and_context_bounded() -> None:
    catalog = BenchmarkWorkspaceCatalog(ROOT)
    workspace = catalog.public_workspace()
    refs = [str(file["file_ref"]) for file in public_files(workspace)[:2]]

    inputs = catalog.agent_file_inputs(refs)

    assert [item["file_ref"] for item in inputs] == refs
    assert all("path" not in item and "sha256" not in item for item in inputs)
    with pytest.raises(KeyError):
        catalog.agent_file_inputs(["forte-0000000000000000"])


def test_manifest_matches_imported_bytes() -> None:
    manifest = json.loads((ROOT / "public-suite-manifest.json").read_text(encoding="utf-8"))
    entries = [
        entry
        for task in manifest["tasks"]
        for entry in [task["task_file"], *task["input_files"]]
    ]
    for entry in entries:
        raw = (ROOT / entry["path"]).read_bytes()
        assert len(raw) == entry["size"]
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]


def test_catalog_fails_closed_when_declared_file_is_tampered(tmp_path: Path) -> None:
    root = copy_package(tmp_path)
    manifest = json.loads((root / "public-suite-manifest.json").read_text(encoding="utf-8"))
    target = root / manifest["tasks"][0]["input_files"][0]["path"]
    raw = bytearray(target.read_bytes())
    raw[-1] ^= 1
    target.write_bytes(raw)

    with pytest.raises(BenchmarkScenarioError, match="完整性"):
        BenchmarkWorkspaceCatalog(root).load()


def test_catalog_fails_closed_on_undeclared_file(tmp_path: Path) -> None:
    root = copy_package(tmp_path)
    (root / "unexpected.txt").write_text("not allowlisted", encoding="utf-8")

    with pytest.raises(BenchmarkScenarioError, match="未声明"):
        BenchmarkWorkspaceCatalog(root).load()


def test_catalog_fails_closed_on_path_escape(tmp_path: Path) -> None:
    root = copy_package(tmp_path)
    manifest_path = root / "public-suite-manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["tasks"][0]["input_files"][0]["path"] = "Finance-018/input/../task.md"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkScenarioError, match="清单"):
        BenchmarkWorkspaceCatalog(root).load()
