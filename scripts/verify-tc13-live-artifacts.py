from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


EXPECTED_FILES = {"客户画像及销售策略.md", "客户画像逐样本台账.csv"}
SOURCE_PATHS = [
    "sales-020/input/客户画像调研问卷.csv",
    "sales-020/input/客户分类画像与差异化销售策略生成规则.md",
]
EXPECTED_LEDGER_HEADERS = [
    "原始行号",
    "来源位置",
    "样本ID",
    "企业所在行业",
    "企业规模",
    "填写人职位",
    "原始专业",
    "原始安全",
    "原始预算",
    "原始易用",
    "清洗专业",
    "清洗安全",
    "清洗预算",
    "清洗易用",
    "转换记录",
    "命中画像",
    "是否应用优先级",
    "最终画像",
    "排除原因",
    "duplicate_of",
    "规则Refs",
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


def _ledger_facts(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = list(reader)
    if reader.fieldnames != EXPECTED_LEDGER_HEADERS:
        raise ValueError(f"unexpected TC-13 ledger headers: {reader.fieldnames}")
    sample_ids = [row["样本ID"] for row in rows]
    duplicate_rows = [row for row in rows if row["duplicate_of"]]
    classified_rows = [row for row in rows if row["最终画像"]]
    unclassified_rows = [row for row in rows if row["排除原因"] == "unclassified"]
    witness_rows = [row for row in rows if row["是否应用优先级"] == "是"]
    clean_scores_are_valid = all(
        value.isdigit() and 0 <= int(value) <= 10
        for row in rows
        for value in (
            row["清洗专业"],
            row["清洗安全"],
            row["清洗预算"],
            row["清洗易用"],
        )
    )
    return {
        "row_count": len(rows),
        "unique_sample_id_count": len(set(sample_ids)),
        "duplicate_count": len(duplicate_rows),
        "duplicate_pairs": sorted(
            (row["样本ID"], row["duplicate_of"]) for row in duplicate_rows
        ),
        "classified_count": len(classified_rows),
        "unclassified_count": len(unclassified_rows),
        "excluded_count": len(duplicate_rows) + len(unclassified_rows),
        "profile_counts": dict(
            sorted(Counter(row["最终画像"] for row in classified_rows).items())
        ),
        "priority_witness_count": len(witness_rows),
        "source_locators": sorted(row["来源位置"] for row in rows),
        "all_locators_are_source_rows": all(
            re.fullmatch(
                r"客户画像调研问卷\.csv:row=(?:[2-9]|[1-9][0-9]+)",
                row["来源位置"],
            )
            is not None
            for row in rows
        ),
        "all_clean_scores_are_0_to_10_integers": clean_scores_are_valid,
        "all_rows_have_rule_refs": all(bool(row["规则Refs"]) for row in rows),
    }


def _markdown_integer(text: str, label: str) -> int | None:
    match = re.search(rf"^- {re.escape(label)}：([0-9]+)$", text, re.MULTILINE)
    return int(match.group(1)) if match else None


def _markdown_facts(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8")
    required_sections = [
        "## 运行摘要",
        "## 规则账本",
        "## 客户画像",
        "## 销售策略",
        "## 客户分析",
        "## 口径假设与边界",
    ]
    return {
        "counts": {
            "source_row_count": _markdown_integer(text, "原始问卷行"),
            "unique_payload_count": _markdown_integer(text, "唯一业务载荷"),
            "duplicate_count": _markdown_integer(text, "精确重复"),
            "classified_count": _markdown_integer(text, "已分类"),
            "unclassified_count": _markdown_integer(text, "无法归类"),
            "excluded_count": _markdown_integer(text, "合计排除"),
            "priority_witness_count": _markdown_integer(text, "多标签优先级 witness"),
        },
        "required_sections_present_once": all(text.count(item) == 1 for item in required_sections),
        "contains_duplicate_policy_assumption": "exact_non_id_payload" in text,
        "contains_strategy_evidence_boundary": "no_approved_strategy_source" in text,
        "contains_public_sample_boundary": "不是真实客户研究、销售效果证明或 CRM 执行" in text,
        "contains_no_customer_action_boundary": (
            "没有联系客户、写 CRM、创建商机或触发营销动作" in text
        ),
        "contains_no_approved_sales_priority": "没有批准的销售优先级来源" in text,
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
        if task["task_id"] == "sales-020"
        for item in task["input_files"]
    }
    entries: list[dict[str, Any]] = []
    for relative_path in SOURCE_PATHS:
        data = (repo_root / "demo-enterprise-data/forte" / relative_path).read_bytes()
        item = declared[relative_path]
        entries.append(
            {
                "path": relative_path,
                "size": len(data),
                "declared_size": item["size"],
                "sha256": _sha256(data),
                "declared_sha256": item["sha256"],
                "matches_pinned_manifest": (
                    len(data) == item["size"] and _sha256(data) == item["sha256"]
                ),
            }
        )
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="下载并独立解析 TC-13 真实 Run 工件。")
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
        if item.get("scenario_id") == "TC-13"
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
        parsed = _ledger_facts(data) if path.suffix == ".csv" else _markdown_facts(data)
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
            if item.get("scenario_id") == "TC-13"
        ),
        {},
    )
    outcome = receipt.get("customer_segmentation_outcome") or {}
    unique_checks = {
        check.get("check_id"): check
        for artifact in artifacts
        for check in artifact.get("checks", [])
        if check.get("check_id")
    }
    ledger = next(
        item for item in artifact_entries if item["file_name"] == "客户画像逐样本台账.csv"
    )
    report = next(
        item for item in artifact_entries if item["file_name"] == "客户画像及销售策略.md"
    )
    ledger_facts = ledger["parsed"]
    markdown_facts = report["parsed"]
    facts_match_outcome = bool(
        ledger_facts["row_count"] == outcome.get("source_row_count")
        and ledger_facts["unique_sample_id_count"] == outcome.get("source_row_count")
        and ledger_facts["duplicate_count"] == outcome.get("duplicate_count")
        and ledger_facts["classified_count"] == outcome.get("classified_count")
        and ledger_facts["unclassified_count"] == outcome.get("unclassified_count")
        and ledger_facts["excluded_count"] == outcome.get("excluded_count")
        and ledger_facts["profile_counts"] == outcome.get("profile_counts")
        and ledger_facts["priority_witness_count"]
        == outcome.get("priority_witness_count")
        and markdown_facts["counts"].get("source_row_count")
        == outcome.get("source_row_count")
        and markdown_facts["counts"].get("unique_payload_count")
        == outcome.get("unique_payload_count")
        and markdown_facts["counts"].get("duplicate_count")
        == outcome.get("duplicate_count")
        and markdown_facts["counts"].get("classified_count")
        == outcome.get("classified_count")
        and markdown_facts["counts"].get("unclassified_count")
        == outcome.get("unclassified_count")
        and markdown_facts["counts"].get("excluded_count")
        == outcome.get("excluded_count")
        and markdown_facts["counts"].get("priority_witness_count")
        == outcome.get("priority_witness_count")
    )
    source_integrity = _source_integrity(args.repo_root.resolve())
    after_hashes = {item["file_name"]: item["sha256"] for item in artifact_entries}
    before_hashes: dict[str, str] = {}
    if args.before_manifest:
        before = json.loads(args.before_manifest.read_text(encoding="utf-8"))
        before_hashes = {
            item["file_name"]: item["sha256"] for item in before.get("artifacts", [])
        }
    restart_hashes_match = not before_hashes or before_hashes == after_hashes
    rounds = snapshot.get("rounds", [])
    first_round = rounds[0] if rounds else {}

    verified = bool(
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
        and all(
            item["size_matches_snapshot"] and item["verifier_status"] == "passed"
            for item in artifact_entries
        )
        and len(unique_checks) == 8
        and all(check.get("passed") is True for check in unique_checks.values())
        and outcome.get("status") == "sales_review_required"
        and outcome.get("human_review_required") is True
        and outcome.get("strategy_evidence_status") == "no_approved_strategy_source"
        and outcome.get("original_inputs_modified") is False
        and outcome.get("external_action") == "none"
        and facts_match_outcome
        and ledger_facts["duplicate_pairs"] == [("111", "101")]
        and ledger_facts["all_locators_are_source_rows"]
        and ledger_facts["all_clean_scores_are_0_to_10_integers"]
        and ledger_facts["all_rows_have_rule_refs"]
        and markdown_facts["required_sections_present_once"]
        and markdown_facts["contains_duplicate_policy_assumption"]
        and markdown_facts["contains_strategy_evidence_boundary"]
        and markdown_facts["contains_public_sample_boundary"]
        and markdown_facts["contains_no_customer_action_boundary"]
        and markdown_facts["contains_no_approved_sales_priority"]
        and all(item["matches_pinned_manifest"] for item in source_integrity)
        and restart_hashes_match
    )
    manifest = {
        "schema_version": "tc13-live-artifact-evidence.v1",
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
            "customer_segmentation_outcome": outcome,
            "event_names": [event.get("event_name") for event in snapshot.get("events", [])],
        },
        "source_integrity": source_integrity,
        "artifacts": sorted(artifact_entries, key=lambda item: item["file_name"]),
        "artifact_facts_match_outcome": facts_match_outcome,
        "restart_verification": {
            "before_manifest": str(args.before_manifest) if args.before_manifest else None,
            "hashes_match": restart_hashes_match,
        },
        "verified": verified,
        "claim_boundary": (
            "This independently reparses the two downloaded artifacts and fixed Sales-020 "
            "inputs. It proves the current public-sample cleaning and deterministic label "
            "projection, not CRM execution, sales effectiveness, customer research, an "
            "approved strategy, a general segmentation engine or multi-instance execution."
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
