from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from services.api.app.application.sre_diagnosis_effect import (
    EXPECTED_DISPLAY_PATH,
    EXPECTED_FILE_NAME,
    EXPECTED_FILE_REF,
    SOURCE_LOGICAL_ID,
    SRESourceInput,
    analyze_sre_source,
    verify_sre_artifacts,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "demo-enterprise-data" / "forte" / "sre-010" / "input" / "log.txt"
PINNED_MANIFEST = REPO_ROOT / "demo-enterprise-data" / "forte" / "public-suite-manifest.json"
EXPECTED_FILES = {"ES故障诊断与止损建议.md", "SRE事故观察与动作台账.csv"}


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


def _pinned_source() -> dict[str, Any]:
    manifest = json.loads(PINNED_MANIFEST.read_text(encoding="utf-8"))
    task = next(item for item in manifest["tasks"] if item["task_id"] == "sre-010")
    return next(item for item in task["input_files"] if item["path"] == "sre-010/input/log.txt")


def _ledger_facts(content: bytes) -> dict[str, Any]:
    reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline=""))
    rows = list(reader)
    ids = [row["记录ID"] for row in rows]
    return {
        "row_count": len(rows),
        "unique_id_count": len(set(ids)),
        "record_type_counts": dict(Counter(row["记录类型"] for row in rows)),
        "all_proposals_require_approval": all(
            row["需审批"] == "true" for row in rows if row["记录类型"] == "proposal"
        ),
        "all_proposals_unexecuted": all(
            row["已执行"] == "false" for row in rows if row["记录类型"] == "proposal"
        ),
        "all_es_targets_unresolved": all(
            row["目标状态"] == "unresolved"
            for row in rows
            if row["记录类型"] == "proposal" and row["记录ID"].startswith("proposal-es-")
        ),
    }


def _report_facts(content: bytes) -> dict[str, Any]:
    text = content.decode("utf-8")
    required_sections = (
        "## 来源概览",
        "## 时间线与观察",
        "## 来源冲突",
        "## 根因假设与反证",
        "## 只读预检与条件式写提案",
        "## 业务止损提案",
        "## 审批与未执行边界",
    )
    return {
        "required_sections_present_once": all(text.count(item) == 1 for item in required_sections),
        "contains_offline_boundary": "离线事故复盘" in text,
        "contains_no_execution_boundary": "external_action=none" in text and "executed=false" in text,
        "contains_unresolved_target": "unresolved" in text,
        "contains_three_conflicts": all(
            item in text
            for item in (
                "sre-conflict-node-count",
                "sre-conflict-unassigned-count",
                "sre-conflict-disk-threshold",
            )
        ),
        "contains_dedicated_master_boundary": "dedicated master" in text,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify TC-14 live artifacts after download")
    parser.add_argument("--api-base", default="http://127.0.0.1:8010")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--before-manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    health = _get_json(f"{args.api_base}/v1/health", owner=args.owner)
    snapshot = _get_json(f"{args.api_base}/v1/harness/runs/{args.run_id}", owner=args.owner)
    source_bytes = SOURCE_PATH.read_bytes()
    pinned = _pinned_source()
    source = SRESourceInput(
        logical_id=SOURCE_LOGICAL_ID,
        file_name=EXPECTED_FILE_NAME,
        display_path=EXPECTED_DISPLAY_PATH,
        file_ref=EXPECTED_FILE_REF,
        content=source_bytes,
        declared_size=len(source_bytes),
        allowlist_verified=True,
    )
    expected = analyze_sre_source(source)
    artifacts = [
        item for item in snapshot.get("workspace_artifacts", []) if item.get("scenario_id") == "TC-14"
    ]
    receipts = [
        item for item in snapshot.get("effect_receipts", []) if item.get("scenario_id") == "TC-14"
    ]
    if len(receipts) != 1:
        raise RuntimeError(f"expected one TC-14 receipt, got {len(receipts)}")
    receipt = receipts[0]
    downloaded: dict[str, bytes] = {}
    artifact_entries: list[dict[str, Any]] = []
    for artifact in artifacts:
        content = _download(
            f"{args.api_base}/v1/harness/runs/{args.run_id}/artifacts/{artifact['artifact_id']}",
            owner=args.owner,
        )
        downloaded[artifact["file_name"]] = content
        artifact_entries.append(
            {
                "artifact_id": artifact["artifact_id"],
                "file_name": artifact["file_name"],
                "media_type": artifact["media_type"],
                "declared_size": artifact["size"],
                "downloaded_size": len(content),
                "size_matches_snapshot": len(content) == artifact["size"],
                "sha256": _sha256(content),
                "verifier_status": artifact["verifier_status"],
                "check_count": len(artifact.get("checks", [])),
            }
        )
    if set(downloaded) != EXPECTED_FILES:
        raise RuntimeError(f"unexpected TC-14 artifacts: {sorted(downloaded)}")

    independent_checks = verify_sre_artifacts(
        source,
        report_markdown=downloaded["ES故障诊断与止损建议.md"],
        ledger_csv=downloaded["SRE事故观察与动作台账.csv"],
    )
    expected_payload = expected.model_dump(mode="json")
    receipt_outcome = receipt.get("sre_diagnosis_outcome")
    artifact_outcomes = [item.get("sre_diagnosis_outcome") for item in artifacts]
    ledger_facts = _ledger_facts(downloaded["SRE事故观察与动作台账.csv"])
    report_facts = _report_facts(downloaded["ES故障诊断与止损建议.md"])
    source_after = SOURCE_PATH.read_bytes()
    restart_hashes_match = True
    if args.before_manifest:
        before = json.loads(args.before_manifest.read_text(encoding="utf-8"))
        before_hashes = {
            item["file_name"]: item["sha256"] for item in before.get("artifacts", [])
        }
        restart_hashes_match = all(
            before_hashes.get(item["file_name"]) == item["sha256"] for item in artifact_entries
        )
    rounds = snapshot.get("rounds", [])
    first_round = rounds[0] if rounds else {}
    verified = (
        health.get("model") == "deepseek-v4-pro"
        and health.get("checkpoint") == "postgres"
        and health.get("task_store") == "postgres"
        and snapshot.get("status") in {"completed", "waiting_input"}
        and first_round.get("model_receipt", {}).get("called") is True
        and first_round.get("model_receipt", {}).get("output_used") is True
        and first_round.get("analysis_receipt", {}).get("called") is True
        and first_round.get("analysis_receipt", {}).get("output_used") is True
        and receipt.get("status") == "passed"
        and receipt.get("external_action") == "none"
        and {item["file_name"] for item in artifact_entries} == EXPECTED_FILES
        and all(item["size_matches_snapshot"] for item in artifact_entries)
        and all(item["verifier_status"] == "passed" for item in artifact_entries)
        and all(item["check_count"] == 12 for item in artifact_entries)
        and len(independent_checks) == 12
        and all(item.passed for item in independent_checks)
        and receipt_outcome == expected_payload
        and artifact_outcomes == [expected_payload, expected_payload]
        and ledger_facts["unique_id_count"] == ledger_facts["row_count"]
        and ledger_facts["record_type_counts"]
        == {
            "observation": expected.observation_count,
            "conflict": expected.conflict_count,
            "hypothesis": expected.hypothesis_count,
            "proposal": expected.proposal_count + expected.business_mitigation_count,
        }
        and ledger_facts["all_proposals_require_approval"]
        and ledger_facts["all_proposals_unexecuted"]
        and ledger_facts["all_es_targets_unresolved"]
        and all(report_facts.values())
        and _sha256(source_bytes) == pinned["sha256"]
        and len(source_bytes) == pinned["size"]
        and source_after == source_bytes
        and restart_hashes_match
    )
    manifest = {
        "schema_version": "tc14-live-artifact-evidence.v1",
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
            "planner_receipt": first_round.get("model_receipt"),
            "analyst_receipt": first_round.get("analysis_receipt"),
            "deterministic_effect_status": receipt.get("status"),
            "unique_check_count": len({item.check_id for item in independent_checks}),
            "sre_diagnosis_outcome": receipt_outcome,
        },
        "source_integrity": {
            "path": "sre-010/input/log.txt",
            "size": len(source_bytes),
            "sha256": _sha256(source_bytes),
            "matches_pinned_manifest": _sha256(source_bytes) == pinned["sha256"],
            "original_input_modified": source_after != source_bytes,
        },
        "artifacts": sorted(artifact_entries, key=lambda item: item["file_name"]),
        "independent_verifier": [item.__dict__ for item in independent_checks],
        "ledger_facts": ledger_facts,
        "report_facts": report_facts,
        "restart_verification": {
            "before_manifest": str(args.before_manifest) if args.before_manifest else None,
            "artifact_hashes_match": restart_hashes_match,
        },
        "no_execution_evidence": {
            "external_action": receipt.get("external_action"),
            "resolved_target_count": expected.resolved_target_count,
            "all_proposals_approval_required": ledger_facts["all_proposals_require_approval"],
            "all_proposals_executed_false": ledger_facts["all_proposals_unexecuted"],
            "all_es_targets_unresolved": ledger_facts["all_es_targets_unresolved"],
        },
        "verified": verified,
        "claim_boundary": (
            "该清单独立重读批准日志和两份下载成果；只证明固定 SRE-010 离线复盘的"
            "来源、文件和未执行边界，不证明根因、生产目标、审批、在线监控或任何外部动作。"
        ),
    }
    args.output.resolve().parent.mkdir(parents=True, exist_ok=True)
    args.output.resolve().write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"verified": verified, "artifacts": len(artifacts)}, ensure_ascii=False))
    if not verified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
