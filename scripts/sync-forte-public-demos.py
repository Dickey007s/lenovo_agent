from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


PINNED_COMMIT = "345c1ec1487139db9dd319787fa9405ba85d1869"
SOURCE_URL = "https://github.com/AGI-Eval-Official/FORTE"

MIME_BY_SUFFIX = {
    ".csv": "text/csv",
    ".css": "text/css",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".html": "text/html",
    ".js": "text/javascript",
    ".json": "application/json",
    ".log": "text/plain",
    ".md": "text/markdown",
    ".pdf": "application/pdf",
    ".py": "text/x-python",
    ".sh": "text/x-shellscript",
    ".ts": "text/typescript",
    ".tsx": "text/typescript-jsx",
    ".txt": "text/plain",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

TASK_ONLY_DEPENDENCIES = {
    "ba-079": "remote_datasette",
    "Misc-AT-003": "web_search_and_cron",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _record(path: Path, root: Path, role: str) -> dict[str, object]:
    suffix = path.suffix.lower()
    if suffix not in MIME_BY_SUFFIX:
        raise ValueError(f"Unsupported public FORTE file type: {path}")
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": _sha256(path),
        "size": path.stat().st_size,
        "mime": MIME_BY_SUFFIX[suffix],
        "role": role,
    }


def _category(task_file: Path) -> str:
    for line in task_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("category:"):
            return line.partition(":")[2].strip()
    raise ValueError(f"Missing category in {task_file}")


def _git_head(repo: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def sync(upstream: Path, destination: Path) -> dict[str, object]:
    if _git_head(upstream) != PINNED_COMMIT:
        raise ValueError(f"FORTE checkout must be pinned to {PINNED_COMMIT}")

    tasks_root = upstream / "data" / "tasks"
    assets_root = upstream / "data" / "assets"
    task_files = sorted(tasks_root.glob("*.md"), key=lambda path: path.stem.lower())
    if len(task_files) != 15:
        raise ValueError(f"Expected 15 public demo tasks, found {len(task_files)}")

    destination.mkdir(parents=True, exist_ok=True)
    license_text = (upstream / "LICENSE").read_text(encoding="utf-8")
    (destination / "THIRD_PARTY_LICENSE.txt").write_text(
        license_text.replace("\r\n", "\n"),
        encoding="utf-8",
        newline="\n",
    )

    task_entries: list[dict[str, object]] = []
    input_file_count = 0
    input_bytes = 0
    task_bytes = 0

    for source_task in task_files:
        task_id = source_task.stem
        target_task_root = destination / task_id
        target_task_root.mkdir(parents=True, exist_ok=True)
        target_task = target_task_root / "task.md"
        shutil.copy2(source_task, target_task)

        source_input = assets_root / task_id / "input"
        target_input = target_task_root / "input"
        if target_input.exists():
            shutil.rmtree(target_input)
        if source_input.exists():
            shutil.copytree(source_input, target_input)

        copied_inputs = (
            sorted((path for path in target_input.rglob("*") if path.is_file()), key=str)
            if target_input.exists()
            else []
        )
        input_records = [_record(path, destination, "input") for path in copied_inputs]
        task_record = _record(target_task, destination, "task_instruction")
        task_input_bytes = sum(int(record["size"]) for record in input_records)

        input_file_count += len(input_records)
        input_bytes += task_input_bytes
        task_bytes += int(task_record["size"])
        task_entries.append(
            {
                "task_id": task_id,
                "category": _category(target_task),
                "availability": (
                    "local_input_bundle"
                    if input_records
                    else "task_only_requires_external_system"
                ),
                "external_dependency": TASK_ONLY_DEPENDENCIES.get(task_id),
                "task_file": task_record,
                "input_dir": f"{task_id}/input" if input_records else None,
                "input_file_count": len(input_records),
                "input_bytes": task_input_bytes,
                "file_extensions": sorted({Path(record["path"]).suffix.lower() for record in input_records}),
                "input_files": input_records,
            }
        )

    manifest = {
        "schema_version": "1.0",
        "dataset": "FORTE public demo suite",
        "source_url": SOURCE_URL,
        "source_commit": PINNED_COMMIT,
        "license": "MIT",
        "content_nature": "public_benchmark_demo_inputs",
        "scope": {
            "full_benchmark_task_count_reported_by_upstream": 180,
            "public_demo_task_count": len(task_entries),
            "local_input_bundle_task_count": sum(
                entry["availability"] == "local_input_bundle" for entry in task_entries
            ),
            "task_only_external_dependency_count": sum(
                entry["availability"] == "task_only_requires_external_system"
                for entry in task_entries
            ),
            "task_instruction_file_count": len(task_entries),
            "input_file_count": input_file_count,
            "task_instruction_bytes": task_bytes,
            "input_bytes": input_bytes,
            "imported_bytes": task_bytes + input_bytes,
        },
        "excluded_upstream_material": ["data/assets/*/solution/**", "data/assets/*/skills/**"],
        "tasks": task_entries,
    }
    manifest_path = destination / "public-suite-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import the complete public FORTE demo suite without solutions or skills."
    )
    parser.add_argument("upstream", type=Path, help="Pinned FORTE repository checkout")
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path("demo-enterprise-data/forte"),
        help="Repository data directory",
    )
    args = parser.parse_args()
    manifest = sync(args.upstream.resolve(), args.destination.resolve())
    scope = manifest["scope"]
    print(
        "Imported "
        f"{scope['public_demo_task_count']} public demos, "
        f"{scope['input_file_count']} inputs, "
        f"{scope['imported_bytes']} bytes."
    )


if __name__ == "__main__":
    main()
