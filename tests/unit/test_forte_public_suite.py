from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "demo-enterprise-data" / "forte"
PUBLIC_MANIFEST = DATA_ROOT / "public-suite-manifest.json"
ACTIVE_MANIFEST = DATA_ROOT / "manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def test_public_suite_contains_every_published_demo_input() -> None:
    manifest = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    scope = manifest["scope"]

    assert manifest["source_commit"] == "345c1ec1487139db9dd319787fa9405ba85d1869"
    assert scope == {
        "full_benchmark_task_count_reported_by_upstream": 180,
        "public_demo_task_count": 15,
        "local_input_bundle_task_count": 13,
        "task_only_external_dependency_count": 2,
        "task_instruction_file_count": 15,
        "input_file_count": 96,
        "task_instruction_bytes": 143462,
        "input_bytes": 1636983,
        "imported_bytes": 1780445,
    }

    declared_paths: set[str] = set()
    for task in manifest["tasks"]:
        records = [task["task_file"], *task["input_files"]]
        assert task["input_file_count"] == len(task["input_files"])
        assert task["input_bytes"] == sum(record["size"] for record in task["input_files"])
        assert (task["availability"] == "local_input_bundle") == bool(task["input_files"])

        for record in records:
            relative_path = record["path"]
            assert relative_path not in declared_paths
            declared_paths.add(relative_path)
            path = DATA_ROOT / relative_path
            assert path.is_file()
            assert path.stat().st_size == record["size"]
            assert _sha256(path) == record["sha256"]
            assert "/solution/" not in f"/{relative_path}/"
            assert "/skills/" not in f"/{relative_path}/"

    actual_paths = {
        path.relative_to(DATA_ROOT).as_posix()
        for task_dir in DATA_ROOT.iterdir()
        if task_dir.is_dir()
        for path in task_dir.rglob("*")
        if path.is_file()
    }
    assert actual_paths == declared_paths


def test_current_runtime_pack_is_an_exact_subset_of_the_public_suite() -> None:
    public = json.loads(PUBLIC_MANIFEST.read_text(encoding="utf-8"))
    active = json.loads(ACTIVE_MANIFEST.read_text(encoding="utf-8"))
    public_records = {
        record["path"]: record
        for task in public["tasks"]
        for record in [task["task_file"], *task["input_files"]]
    }

    assert {task["task_id"] for task in active["tasks"]} == {
        "Finance-018",
        "Operations-008",
        "pm-014",
    }
    for task in active["tasks"]:
        for record in task["files"]:
            public_record = public_records[record["path"]]
            assert record["sha256"] == public_record["sha256"]
            assert record["size"] == public_record["size"]
            assert record["mime"] == public_record["mime"]
            assert record["role"] == public_record["role"]
