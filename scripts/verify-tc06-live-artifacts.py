from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
import zipfile
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


EXPECTED_FILES = {
    "外卖商户BD岗位辅助筛选报告.docx",
    "文本评测岗位辅助筛选报告.docx",
    "候选人岗位条件逐项台账.csv",
}
STATUS_LABELS = {
    "有来源支持": "met",
    "明确不满足": "not_met",
    "资料不足": "unverifiable",
    "需人工例外判断": "human_exception_required",
}
EXPECTED_ROLE_CONDITION_COUNTS = {
    "merchant_bd": 14,
    "text_evaluation": 8,
}
EXPECTED_CANDIDATES = {"周伦", "孙博文", "李雨桐", "王琳达", "赵晨曦"}
WORD_NAMESPACE = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
}


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


def _docx_facts(data: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        if "word/document.xml" not in names:
            raise ValueError("DOCX 缺少 word/document.xml")
        root = ElementTree.fromstring(archive.read("word/document.xml"))
    paragraphs = [
        "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NAMESPACE))
        for paragraph in root.findall(".//w:p", WORD_NAMESPACE)
    ]
    text = "\n".join(item for item in paragraphs if item)
    return {
        "paragraph_count": len([item for item in paragraphs if item]),
        "table_count": len(root.findall(".//w:tbl", WORD_NAMESPACE)),
        "text_length": len(text),
        "contains_human_decision_boundary": "不是录用或淘汰决定" in text,
        "contains_no_fairness_claim_boundary": "不能声称无偏" in text,
        "contains_no_external_action_boundary": "没有背景调查、身份核验、外部通知或自动人事动作" in text,
        "contains_five_candidate_summary": "五名候选人汇总" in text,
        "candidate_names_present": sorted(name for name in EXPECTED_CANDIDATES if name in text),
    }

def _privacy_findings(text: str) -> list[str]:
    patterns = {
        "email": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
        "mobile": r"(?<!\d)1[3-9]\d{9}(?!\d)",
        "address_value": r"(?:家庭住址|住址|地址)\s*[：:]\s*(?!\[已隐藏)[^,\n]{2,}",
        "demographic_value": r"(?:性别|年龄|出生日期|民族|婚姻状况|籍贯|政治面貌)\s*[：:]\s*(?!\[已隐藏)[^,\n]{1,}",
    }
    return sorted(label for label, pattern in patterns.items() if re.search(pattern, text))


def _csv_facts(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8-sig")
    rows = list(csv.DictReader(text.splitlines()))
    keys = [(row["岗位ID"], row["候选人ID"], row["条件ID"]) for row in rows]
    status_counts = Counter(STATUS_LABELS.get(row["状态"], f"unknown:{row['状态']}") for row in rows)
    role_counts = Counter(row["岗位ID"] for row in rows)
    role_candidates = {
        role_id: sorted({row["候选人"] for row in rows if row["岗位ID"] == role_id})
        for role_id in EXPECTED_ROLE_CONDITION_COUNTS
    }
    role_condition_counts = {
        role_id: len({row["条件ID"] for row in rows if row["岗位ID"] == role_id})
        for role_id in EXPECTED_ROLE_CONDITION_COUNTS
    }
    recommendation_counts = Counter(
        (row["岗位ID"], row["候选人ID"], row["总体建议"]) for row in rows
    )
    return {
        "row_count": len(rows),
        "unique_key_count": len(set(keys)),
        "status_counts": dict(sorted(status_counts.items())),
        "role_row_counts": dict(sorted(role_counts.items())),
        "role_condition_counts": role_condition_counts,
        "role_candidates": role_candidates,
        "candidate_role_recommendation_count": len(recommendation_counts),
        "all_rows_have_both_source_refs": all(
            row.get("JD来源Ref") and row.get("简历来源Ref") for row in rows
        ),
        "all_rows_have_both_locators": all(
            row.get("JD位置") and row.get("简历位置") for row in rows
        ),
        "all_rows_have_action_and_exit": all(
            row.get("责任人") and row.get("面试或补证动作") and row.get("退出条件")
            for row in rows
        ),
        "privacy_findings": _privacy_findings(text),
    }


def _artifact_entry(path: Path, *, metadata: dict[str, Any]) -> dict[str, Any]:
    data = path.read_bytes()
    parsed = _csv_facts(data) if path.suffix.lower() == ".csv" else _docx_facts(data)
    return {
        "artifact_id": metadata.get("artifact_id"),
        "file_name": path.name,
        "size": len(data),
        "declared_size": metadata.get("size"),
        "sha256": _sha256(data),
        "size_matches_snapshot": len(data) == metadata.get("size"),
        "verifier_status": metadata.get("verifier_status"),
        "source_file_ref_count": len(metadata.get("source_file_refs", [])),
        "parsed": parsed,
    }


def _all_artifact_gates_pass(entries: list[dict[str, Any]]) -> bool:
    if {entry["file_name"] for entry in entries} != EXPECTED_FILES:
        return False
    if not all(
        entry["size_matches_snapshot"] and entry["verifier_status"] == "passed"
        for entry in entries
    ):
        return False
    csv_entry = next(entry for entry in entries if entry["file_name"].endswith(".csv"))
    csv_facts = csv_entry["parsed"]
    if csv_facts["row_count"] != 110 or csv_facts["unique_key_count"] != 110:
        return False
    if csv_facts["status_counts"] != {
        "human_exception_required": 1,
        "met": 32,
        "not_met": 6,
        "unverifiable": 71,
    }:
        return False
    if csv_facts["role_condition_counts"] != EXPECTED_ROLE_CONDITION_COUNTS:
        return False
    if any(set(names) != EXPECTED_CANDIDATES for names in csv_facts["role_candidates"].values()):
        return False
    if csv_facts["candidate_role_recommendation_count"] != 10:
        return False
    if csv_facts["privacy_findings"]:
        return False
    if not all(
        csv_facts[key]
        for key in (
            "all_rows_have_both_source_refs",
            "all_rows_have_both_locators",
            "all_rows_have_action_and_exit",
        )
    ):
        return False
    return all(
        entry["parsed"]["contains_human_decision_boundary"]
        and entry["parsed"]["contains_no_fairness_claim_boundary"]
        and entry["parsed"]["contains_no_external_action_boundary"]
        and entry["parsed"]["contains_five_candidate_summary"]
        and set(entry["parsed"]["candidate_names_present"]) == EXPECTED_CANDIDATES
        for entry in entries
        if entry["file_name"].endswith(".docx")
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并独立解析 TC-06 真实 Run 工件。")
    parser.add_argument("--api-base", default="http://127.0.0.1:8010")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--idempotency-key", required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before-manifest", type=Path)
    args = parser.parse_args()

    health = _get_json(f"{args.api_base}/v1/health", owner=args.owner)
    snapshot = _get_json(
        f"{args.api_base}/v1/harness/runs/{args.run_id}", owner=args.owner
    )
    artifacts = [
        item for item in snapshot.get("workspace_artifacts", []) if item.get("scenario_id") == "TC-06"
    ]
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    for artifact in artifacts:
        data = _download(
            f"{args.api_base}/v1/harness/runs/{args.run_id}/artifacts/{artifact['artifact_id']}",
            owner=args.owner,
        )
        path = args.artifact_dir / artifact["file_name"]
        path.write_bytes(data)
        entries.append(_artifact_entry(path, metadata=artifact))

    rounds = snapshot.get("rounds", [])
    first_round = rounds[0] if rounds else {}
    receipt = next(
        (item for item in snapshot.get("effect_receipts", []) if item.get("scenario_id") == "TC-06"),
        {},
    )
    outcome = receipt.get("candidate_review_outcome") or {}
    unique_checks = {
        check.get("check_id"): check
        for artifact in artifacts
        for check in artifact.get("checks", [])
        if check.get("check_id")
    }
    before_hashes: dict[str, str] = {}
    if args.before_manifest:
        before = json.loads(args.before_manifest.read_text(encoding="utf-8"))
        before_hashes = {
            item["file_name"]: item["sha256"] for item in before.get("artifacts", [])
        }
    after_hashes = {item["file_name"]: item["sha256"] for item in entries}
    restart_hashes_match = not before_hashes or before_hashes == after_hashes
    event_names = [event.get("event_name") for event in snapshot.get("events", [])]

    manifest = {
        "schema_version": "tc06-live-artifact-evidence.v1",
        "captured_at": datetime.now(UTC).isoformat(),
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
            "evidence_gap_count": len(first_round.get("evidence_gaps", [])),
            "planner_receipt": first_round.get("model_receipt"),
            "analyst_receipt": first_round.get("analysis_receipt"),
            "deterministic_effect_status": receipt.get("status"),
            "external_action": receipt.get("external_action"),
            "original_inputs_modified": any(
                item.get("original_inputs_modified") is not False for item in artifacts
            ),
            "unique_check_count": len(unique_checks),
            "passed_unique_check_count": sum(
                1 for check in unique_checks.values() if check.get("passed") is True
            ),
            "candidate_review_counts": {
                key: outcome.get(key)
                for key in (
                    "role_count",
                    "candidate_count",
                    "assessment_count",
                    "met_count",
                    "not_met_count",
                    "unverifiable_count",
                    "human_exception_count",
                )
            },
            "event_names": event_names,
        },
        "artifacts": sorted(entries, key=lambda item: item["file_name"]),
        "restart_verification": {
            "before_manifest": str(args.before_manifest) if args.before_manifest else None,
            "hashes_match": restart_hashes_match,
        },
    }
    manifest["verified"] = bool(
        health.get("model") == "deepseek-v4-pro"
        and health.get("checkpoint") == "postgres"
        and health.get("task_store") == "postgres"
        and snapshot.get("status") == "waiting_input"
        and first_round.get("model_receipt", {}).get("called") is True
        and first_round.get("model_receipt", {}).get("output_used") is True
        and first_round.get("analysis_receipt", {}).get("called") is True
        and first_round.get("analysis_receipt", {}).get("output_used") is True
        and receipt.get("status") == "passed"
        and receipt.get("external_action") == "none"
        and all(item.get("original_inputs_modified") is False for item in artifacts)
        and len(unique_checks) == 11
        and all(check.get("passed") is True for check in unique_checks.values())
        and outcome.get("assessment_count") == 110
        and _all_artifact_gates_pass(entries)
        and restart_hashes_match
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"verified": manifest["verified"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if manifest["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
