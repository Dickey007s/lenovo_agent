from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any


EXPECTED_FILES = {"未付统计.csv", "未收统计.csv", "跨期核对说明.md"}
EXPECTED_HEADERS = [
    "科目名称",
    "客商名称",
    "方向",
    "期末余额",
    "来源文件",
    "来源文件Ref",
    "来源位置",
]
SOURCE_PATHS = [
    "Finance-018/input/2025往来明细-上半年.xlsx",
    "Finance-018/input/2025往来明细-下半年.xlsx",
    "Finance-018/input/2026往来明细.xlsx",
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get_json(url: str, *, owner: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"X-User-Id": owner})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _download(url: str, *, owner: str) -> bytes:
    request = urllib.request.Request(url, headers={"X-User-Id": owner})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _csv_facts(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    rows = list(reader)
    if reader.fieldnames != EXPECTED_HEADERS:
        raise ValueError(f"unexpected CSV headers: {reader.fieldnames}")
    amounts = [Decimal(row["期末余额"]) for row in rows]
    keys = [(row["科目名称"], row["客商名称"]) for row in rows]
    return {
        "row_count": len(rows),
        "unique_key_count": len(set(keys)),
        "total": format(sum(amounts, Decimal("0")), "f"),
        "directions": sorted({row["方向"] for row in rows}),
        "source_files": sorted({row["来源文件"] for row in rows}),
        "source_file_refs": sorted({row["来源文件Ref"] for row in rows}),
        "all_locators_are_excel_ranges": all(
            re.fullmatch(r"[^!]+!A\d+:J\d+", row["来源位置"] or "") is not None
            for row in rows
        ),
    }


def _markdown_facts(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8")
    blocks = re.findall(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if len(blocks) != 1:
        raise ValueError("cross-period note must contain one machine-readable JSON block")
    machine_summary = json.loads(blocks[0])
    return {
        "machine_summary": machine_summary,
        "contains_no_accounting_action_boundary": (
            "不是付款、核销、记账或坏账确认" in text
        ),
        "contains_human_review_action": "财务复核动作" in text,
        "contains_exit_condition": "退出条件" in text,
        "contains_fixed_zero_success_claim": "候选必须为 0" in text,
    }


def _source_integrity(repo_root: Path) -> list[dict[str, Any]]:
    public_manifest = json.loads(
        (repo_root / "demo-enterprise-data/forte/public-suite-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    declared = {
        item["path"]: item
        for task in public_manifest["tasks"]
        if task["task_id"] == "Finance-018"
        for item in task["input_files"]
    }
    entries: list[dict[str, Any]] = []
    for relative_path in SOURCE_PATHS:
        path = repo_root / "demo-enterprise-data/forte" / relative_path
        data = path.read_bytes()
        manifest_item = declared[relative_path]
        entries.append(
            {
                "path": relative_path,
                "size": len(data),
                "declared_size": manifest_item["size"],
                "sha256": _sha256(data),
                "declared_sha256": manifest_item["sha256"],
                "matches_pinned_manifest": (
                    len(data) == manifest_item["size"]
                    and _sha256(data) == manifest_item["sha256"]
                ),
            }
        )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并独立解析 TC-05 真实 Run 工件。")
    parser.add_argument("--api-base", default="http://127.0.0.1:8010")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--before-manifest", type=Path)
    args = parser.parse_args()

    health = _get_json(f"{args.api_base}/v1/health", owner=args.owner)
    snapshot = _get_json(
        f"{args.api_base}/v1/harness/runs/{args.run_id}", owner=args.owner
    )
    artifacts = [
        item
        for item in snapshot.get("workspace_artifacts", [])
        if item.get("scenario_id") == "TC-05"
    ]
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_entries: list[dict[str, Any]] = []
    for artifact in artifacts:
        data = _download(
            f"{args.api_base}/v1/harness/runs/{args.run_id}/artifacts/{artifact['artifact_id']}",
            owner=args.owner,
        )
        path = args.artifact_dir / artifact["file_name"]
        path.write_bytes(data)
        parsed = _csv_facts(data) if path.suffix == ".csv" else _markdown_facts(data)
        artifact_entries.append(
            {
                "artifact_id": artifact["artifact_id"],
                "file_name": path.name,
                "size": len(data),
                "declared_size": artifact.get("size"),
                "sha256": _sha256(data),
                "size_matches_snapshot": len(data) == artifact.get("size"),
                "verifier_status": artifact.get("verifier_status"),
                "source_file_refs": artifact.get("source_file_refs", []),
                "parsed": parsed,
            }
        )

    receipt = next(
        (
            item
            for item in snapshot.get("effect_receipts", [])
            if item.get("scenario_id") == "TC-05"
        ),
        {},
    )
    outcome = receipt.get("finance_review_outcome") or {}
    unique_checks = {
        check.get("check_id"): check
        for artifact in artifacts
        for check in artifact.get("checks", [])
        if check.get("check_id")
    }
    unpaid = next(
        item for item in artifact_entries if item["file_name"] == "未付统计.csv"
    )
    unreceived = next(
        item for item in artifact_entries if item["file_name"] == "未收统计.csv"
    )
    note = next(
        item for item in artifact_entries if item["file_name"] == "跨期核对说明.md"
    )
    machine_summary = note["parsed"]["machine_summary"]
    rounds = snapshot.get("rounds", [])
    first_round = rounds[0] if rounds else {}
    source_integrity = _source_integrity(args.repo_root.resolve())
    after_hashes = {item["file_name"]: item["sha256"] for item in artifact_entries}
    before_hashes: dict[str, str] = {}
    if args.before_manifest:
        before = json.loads(args.before_manifest.read_text(encoding="utf-8"))
        before_hashes = {
            item["file_name"]: item["sha256"] for item in before.get("artifacts", [])
        }
    restart_hashes_match = not before_hashes or before_hashes == after_hashes

    artifact_facts_match = bool(
        unpaid["parsed"]["row_count"] == outcome.get("unpaid_count")
        and unpaid["parsed"]["total"] == outcome.get("unpaid_total")
        and unpaid["parsed"]["directions"] == ["贷"]
        and unreceived["parsed"]["row_count"] == outcome.get("unreceived_count")
        and unreceived["parsed"]["total"] == outcome.get("unreceived_total")
        and unreceived["parsed"]["directions"] == ["借"]
        and machine_summary.get("unpaid_count") == outcome.get("unpaid_count")
        and machine_summary.get("unpaid_total") == outcome.get("unpaid_total")
        and machine_summary.get("unreceived_count") == outcome.get("unreceived_count")
        and machine_summary.get("unreceived_total") == outcome.get("unreceived_total")
        and machine_summary.get("candidate_count") == outcome.get("candidate_count")
        and machine_summary.get("candidates") == outcome.get("candidates")
    )
    verified = bool(
        health.get("model") == "deepseek-v4-pro"
        and health.get("checkpoint") == "postgres"
        and health.get("task_store") == "postgres"
        and snapshot.get("status") == "completed"
        and first_round.get("model_receipt", {}).get("called") is True
        and first_round.get("model_receipt", {}).get("output_used") is True
        and first_round.get("analysis_receipt", {}).get("called") is True
        and first_round.get("analysis_receipt", {}).get("output_used") is True
        and receipt.get("status") == "passed"
        and receipt.get("external_action") == "none"
        and {item["file_name"] for item in artifact_entries} == EXPECTED_FILES
        and all(
            item["size_matches_snapshot"] and item["verifier_status"] == "passed"
            for item in artifact_entries
        )
        and len(unique_checks) == 15
        and all(check.get("passed") is True for check in unique_checks.values())
        and outcome.get("status") == "review_required"
        and outcome.get("human_review_required") is True
        and outcome.get("external_action") == "none"
        and outcome.get("original_inputs_modified") is False
        and artifact_facts_match
        and all(item["matches_pinned_manifest"] for item in source_integrity)
        and all(
            item["parsed"].get("all_locators_are_excel_ranges") is True
            for item in (unpaid, unreceived)
        )
        and note["parsed"]["contains_no_accounting_action_boundary"]
        and note["parsed"]["contains_human_review_action"]
        and note["parsed"]["contains_exit_condition"]
        and not note["parsed"]["contains_fixed_zero_success_claim"]
        and restart_hashes_match
    )
    manifest = {
        "schema_version": "tc05-live-artifact-evidence.v1",
        "request": {
            "api_header": {"X-User-Id": args.owner},
            "run_id": args.run_id,
            "idempotency_key": args.idempotency_key,
            "instruction": snapshot.get("instruction"),
        },
        "runtime": {
            "health": health,
            "status": snapshot.get("status"),
            "version": snapshot.get("version"),
            "round_count": len(rounds),
            "planner_receipt": first_round.get("model_receipt"),
            "analyst_receipt": first_round.get("analysis_receipt"),
            "deterministic_effect_status": receipt.get("status"),
            "external_action": receipt.get("external_action"),
            "unique_check_count": len(unique_checks),
            "passed_unique_check_count": sum(
                1 for check in unique_checks.values() if check.get("passed") is True
            ),
            "finance_review_outcome": outcome,
            "event_names": [
                event.get("event_name") for event in snapshot.get("events", [])
            ],
        },
        "source_integrity": source_integrity,
        "artifacts": sorted(artifact_entries, key=lambda item: item["file_name"]),
        "artifact_facts_match_outcome": artifact_facts_match,
        "restart_verification": {
            "before_manifest": str(args.before_manifest) if args.before_manifest else None,
            "hashes_match": restart_hashes_match,
        },
        "verified": verified,
        "claim_boundary": (
            "This independently reparses the three downloaded artifacts and fixed Finance-018 "
            "inputs. It proves the current heuristic and sequential PostgreSQL-backed facts, "
            "not an accounting policy, zombie-account conclusion, multi-instance execution "
            "or any payment, write-off, posting or bad-debt action."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verified": verified, "output": str(args.output)}, ensure_ascii=False))
    return 0 if verified else 1


if __name__ == "__main__":
    raise SystemExit(main())
