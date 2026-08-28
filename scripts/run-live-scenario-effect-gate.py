from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx

from services.api.app.application.scenario_effects import SCENARIO_EFFECT_SPECS


REPO_ROOT = Path(__file__).resolve().parents[1]
FORTE_ROOT = REPO_ROOT / "demo-enterprise-data" / "forte"
DEFAULT_SCENARIOS = ("TC-01", "TC-05", "TC-10", "TC-13", "TC-14", "TC-15")
SETTLED_STATUSES = {"waiting_input", "ready_to_execute", "completed", "stopped", "failed"}


def _tc02_zip_content_gate(content: bytes) -> dict[str, Any]:
    project_prefix = "search_agent_workflow/"
    required = {
        f"{project_prefix}{name}"
        for name in (
            "config.py",
            "llm.py",
            "main.py",
            "requirements.txt",
            "search_agent.log",
            "tools.py",
            "workflow.py",
            "react_agent.py",
            "tests/test_react_agent.py",
            "CHANGESET.patch",
            "changes.json",
            "改动说明.md",
            "TC-02自测卡.md",
            "TEST_RECEIPT.txt",
            "test_receipt.json",
        )
    }
    source_root = FORTE_ROOT / "algorithm-013" / "input" / "search_agent_workflow"
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = archive.infolist()
            unsafe = [
                item.filename
                for item in members
                if Path(item.filename).is_absolute()
                or ".." in Path(item.filename).parts
                or stat.S_ISLNK(item.external_attr >> 16)
            ]
            names = {item.filename for item in members if not item.is_dir()}
            missing = sorted(required - names)
            if unsafe or missing:
                return {
                    "passed": False,
                    "valid_zip": True,
                    "unsafe_members": unsafe,
                    "missing_members": missing,
                }
            unchanged = {
                name: hashlib.sha256(archive.read(f"{project_prefix}{name}")).hexdigest()
                == hashlib.sha256((source_root / name).read_bytes()).hexdigest()
                for name in ("workflow.py", "llm.py", "tools.py", "requirements.txt", "search_agent.log")
            }
            main_text = archive.read(f"{project_prefix}main.py").decode("utf-8")
            react_text = archive.read(f"{project_prefix}react_agent.py").decode("utf-8")
            receipt = json.loads(archive.read(f"{project_prefix}test_receipt.json"))
            with tempfile.TemporaryDirectory(prefix="tc02-live-download-") as directory:
                root = Path(directory)
                archive.extractall(root)
                env = {
                    "PATH": os.environ.get("PATH", ""),
                    "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                    "TEMP": os.environ.get("TEMP", directory),
                    "TMP": os.environ.get("TMP", directory),
                    "PYTHONNOUSERSITE": "1",
                    "HTTP_PROXY": "",
                    "HTTPS_PROXY": "",
                    "NO_PROXY": "*",
                }
                compile_started = time.monotonic()
                compiled = subprocess.run(
                    [sys.executable, "-m", "compileall", "-q", "search_agent_workflow"],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                compile_ms = int((time.monotonic() - compile_started) * 1000)
                test_started = time.monotonic()
                tested = subprocess.run(
                    [sys.executable, "-m", "unittest", "discover", "-s", "search_agent_workflow/tests", "-v"],
                    cwd=root,
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=30,
                )
                test_ms = int((time.monotonic() - test_started) * 1000)
        test_output = tested.stdout + "\n" + tested.stderr
        executed_ids = re.findall(r"^(test_[a-z0-9_]+) \(", test_output, flags=re.MULTILINE)
        declared_ids = receipt.get("tests", {}).get("declared_ids", [])
        manifest_consistent = set(executed_ids) == set(declared_ids) and len(executed_ids) == len(declared_ids)
        passed = (
            compiled.returncode == 0
            and tested.returncode == 0
            and manifest_consistent
            and all(unchanged.values())
            and "ReActSearchAgent" in main_text
            and "SearchWorkflow" not in main_text
            and "range(1, self.config.max_iterations + 1)" in react_text
            and receipt.get("status") == "passed"
        )
        return {
            "passed": passed,
            "valid_zip": True,
            "file_count": len(names),
            "missing_members": [],
            "unsafe_members": [],
            "unchanged_source_contracts": unchanged,
            "compile": {"exit_code": compiled.returncode, "elapsed_ms": compile_ms},
            "tests": {
                "exit_code": tested.returncode,
                "elapsed_ms": test_ms,
                "count": len(executed_ids),
                "declared_ids": declared_ids,
                "executed_ids": executed_ids,
                "manifest_consistent": manifest_consistent,
            },
            "main_uses_react": "ReActSearchAgent" in main_text and "SearchWorkflow" not in main_text,
            "network_boundary": "本次固定测试未调用网络或生产搜索；没有 OS 级 socket 隔离。",
        }
    except (KeyError, OSError, ValueError, json.JSONDecodeError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
        return {
            "passed": False,
            "valid_zip": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        }


def _tc10_docx_content_gate(content: bytes) -> dict[str, Any]:
    required_tokens = (
        "START -> 外呼时段合规判断",
        "外呼时段合规 -> 发起外呼拨号",
        "未接通 -> 今日已拨次数与一小时频次判断",
        "达到每日3次或1小时1次上限 -> 停止外呼（达上限）",
        "接通 -> 录音告知（本次通话将被录音）",
        "录音告知 -> 身份确认",
        "本人 -> 开场告知与还款引导",
        "第三方要求不再联系 -> 加入禁呼名单",
        "接通后立即挂断或无法沟通 -> 今日已拨次数与一小时频次判断",
        "情绪激动超过30秒 -> 转人工跟进",
        "PTP登记",
        "转人工跟进",
        "安排重拨",
        "停止外呼（达上限）",
        "加入禁呼名单",
        "案件升级",
        "采用依据：《专业性说明.md》",
        "实际没有拨号、没有写 CRM、没有发送短信",
    )
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
        text = "".join(root.itertext())
    except (KeyError, OSError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        return {
            "passed": False,
            "valid_docx": False,
            "paragraph_count": 0,
            "missing_tokens": list(required_tokens),
            "error": type(exc).__name__,
        }
    paragraph_count = len(root.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"))
    missing = [token for token in required_tokens if token not in text]
    unique_start = text.count("START -> 外呼时段合规判断") == 1
    return {
        "passed": unique_start and not missing,
        "valid_docx": True,
        "paragraph_count": paragraph_count,
        "unique_start": unique_start,
        "required_token_count": len(required_tokens),
        "missing_tokens": missing,
    }


def _input_tree_digest() -> str:
    digest = hashlib.sha256()
    paths = sorted(
        path
        for path in FORTE_ROOT.rglob("*")
        if path.is_file() and "input" in path.relative_to(FORTE_ROOT).parts
    )
    for path in paths:
        digest.update(path.relative_to(FORTE_ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def _model_calls(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for round_item in snapshot.get("rounds", []):
        for role, key in (("planner", "model_receipt"), ("analyst", "analysis_receipt")):
            receipt = round_item.get(key)
            if not receipt:
                continue
            calls.append(
                {
                    "round": round_item.get("round_number"),
                    "role": role,
                    "called": bool(receipt.get("called")),
                    "model": receipt.get("model"),
                    "elapsed_ms": receipt.get("elapsed_ms"),
                    "output_used": bool(receipt.get("output_used")),
                }
            )
    return calls


def _event_projection(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {
        "planning_started",
        "planning_completed",
        "analysis_started",
        "analysis_completed",
        "analysis_structure_rejected",
        "analysis_validation_rejected",
        "deterministic_office_tool_started",
        "run_workspace_artifact_written",
        "deterministic_verification_completed",
        "scenario_effect_bounded",
        "task_completed",
        "evidence_gate_waiting_input",
        "harness_failed",
    }
    return [
        {
            "sequence": item.get("sequence"),
            "event_name": item.get("event_name"),
            "status": item.get("status"),
        }
        for item in snapshot.get("events", [])
        if item.get("event_name") in allowed
    ]


def _download_artifacts(
    client: httpx.Client,
    *,
    api_base: str,
    run_id: str,
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    downloads: list[dict[str, Any]] = []
    for artifact in artifacts:
        response = client.get(
            f"{api_base}/v1/harness/runs/{run_id}/artifacts/{artifact['artifact_id']}"
        )
        content_gate = None
        if response.status_code == 200 and artifact.get("scenario_id") == "TC-10":
            content_gate = _tc10_docx_content_gate(response.content)
        elif (
            response.status_code == 200
            and artifact.get("scenario_id") == "TC-02"
            and artifact.get("media_type") == "application/zip"
        ):
            content_gate = _tc02_zip_content_gate(response.content)
        downloads.append(
            {
                "artifact_id": artifact["artifact_id"],
                "file_name": artifact["file_name"],
                "status_code": response.status_code,
                "content_type": response.headers.get("content-type", "").split(";", 1)[0],
                "declared_size": artifact["size"],
                "downloaded_size": len(response.content),
                "sha256": hashlib.sha256(response.content).hexdigest(),
                "size_matches": response.status_code == 200
                and len(response.content) == artifact["size"],
                "content_gate": content_gate,
            }
        )
    return downloads


def _run_one(
    client: httpx.Client,
    *,
    api_base: str,
    scenario_id: str,
    timeout_seconds: int,
    poll_seconds: float,
) -> dict[str, Any]:
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == scenario_id)
    started_at = datetime.now(timezone.utc)
    idempotency_key = f"scenario-effect-live-{scenario_id.lower()}-{uuid.uuid4().hex}"
    response = client.post(
        f"{api_base}/v1/harness/runs",
        json={
            "idempotency_key": idempotency_key,
            "instruction": spec.instruction,
            "loop": {
                "max_rounds": 12,
                "max_files_per_round": 16,
                "max_model_calls": 30,
                "deadline_seconds": 7200,
            },
        },
    )
    response.raise_for_status()
    snapshot = response.json()["run"]
    run_id = snapshot["run_id"]
    deadline = time.monotonic() + timeout_seconds
    previous_marker: tuple[Any, ...] | None = None
    timed_out = False
    while True:
        snapshot_response = client.get(f"{api_base}/v1/harness/runs/{run_id}")
        snapshot_response.raise_for_status()
        snapshot = snapshot_response.json()
        marker = (
            snapshot.get("status"),
            snapshot.get("current_round"),
            snapshot.get("budget", {}).get("model_calls_used"),
            len(snapshot.get("workspace_artifacts", [])),
            len(snapshot.get("effect_receipts", [])),
        )
        if marker != previous_marker:
            print(
                f"{scenario_id} {run_id}: status={marker[0]} round={marker[1]} "
                f"calls={marker[2]} artifacts={marker[3]} receipts={marker[4]}",
                flush=True,
            )
            previous_marker = marker
        receipts = [
            item
            for item in snapshot.get("effect_receipts", [])
            if item.get("scenario_id") == scenario_id
        ]
        if snapshot.get("status") in SETTLED_STATUSES and receipts:
            break
        if snapshot.get("status") in {"failed", "stopped"}:
            break
        if snapshot.get("status") == "waiting_input" and not receipts:
            break
        if time.monotonic() >= deadline:
            timed_out = True
            break
        time.sleep(poll_seconds)

    artifacts = [
        item
        for item in snapshot.get("workspace_artifacts", [])
        if item.get("scenario_id") == scenario_id
    ]
    receipts = [
        item
        for item in snapshot.get("effect_receipts", [])
        if item.get("scenario_id") == scenario_id
    ]
    downloads = _download_artifacts(
        client,
        api_base=api_base,
        run_id=run_id,
        artifacts=artifacts,
    )
    checks = [check for artifact in artifacts for check in artifact.get("checks", [])]
    calls = _model_calls(snapshot)
    planner_calls = [item for item in calls if item["role"] == "planner"]
    analyst_calls = [item for item in calls if item["role"] == "analyst"]
    receipt_passed = any(item.get("status") == "passed" for item in receipts)
    expected_files = set(spec.expected_artifacts)
    actual_files = {item.get("file_name") for item in artifacts}
    model_execution_gate = (
        any(item["called"] and item["model"] == "deepseek-v4-pro" for item in planner_calls)
        and any(item["called"] and item["model"] == "deepseek-v4-pro" for item in analyst_calls)
    )
    model_output_adopted = (
        any(item["output_used"] for item in planner_calls)
        and any(item["output_used"] for item in analyst_calls)
    )
    effect_gate_passed = (
        not timed_out
        and receipt_passed
        and expected_files == actual_files
        and bool(checks)
        and all(bool(item.get("passed")) for item in checks)
        and bool(downloads)
        and all(item["size_matches"] for item in downloads)
        and all(
            item["content_gate"] is None or item["content_gate"]["passed"]
            for item in downloads
        )
        and model_execution_gate
        and all(item.get("external_action") == "none" for item in receipts)
        and all(item.get("original_inputs_modified") is False for item in artifacts)
    )
    return {
        "scenario_id": scenario_id,
        "capability_id": spec.capability_id,
        "title": spec.title,
        "instruction": spec.instruction,
        "run_id": run_id,
        "started_at": started_at.isoformat(),
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "run_status": snapshot.get("status"),
        "snapshot_version": snapshot.get("version"),
        "current_round": snapshot.get("current_round"),
        "budget": snapshot.get("budget"),
        "model_calls": calls,
        "model_execution_gate_passed": model_execution_gate,
        "model_output_adopted": model_output_adopted,
        "effect_receipts": receipts,
        "artifacts": [
            {
                "artifact_id": item.get("artifact_id"),
                "file_name": item.get("file_name"),
                "media_type": item.get("media_type"),
                "size": item.get("size"),
                "validator_id": item.get("validator_id"),
                "verifier_status": item.get("verifier_status"),
                "checks": item.get("checks", []),
                "review_required": item.get("review_required"),
                "deliverable_type": item.get("deliverable_type"),
                "key_outputs": item.get("key_outputs", []),
                "key_outputs_label": item.get("key_outputs_label"),
                "review_guidance": item.get("review_guidance"),
                "execution_summary": item.get("execution_summary"),
                "self_test": item.get("self_test"),
                "external_action": item.get("external_action"),
                "original_inputs_modified": item.get("original_inputs_modified"),
            }
            for item in artifacts
        ],
        "artifact_downloads": downloads,
        "expected_artifacts": list(spec.expected_artifacts),
        "events": _event_projection(snapshot),
        "waiting_branches": [
            {
                "branch_id": item.get("branch_id"),
                "title": item.get("title"),
                "status": item.get("status"),
                "missing_file_count": len(item.get("missing_file_refs", [])),
            }
            for item in snapshot.get("branches", [])
            if item.get("status") == "waiting_input"
        ],
        "validation_errors": snapshot.get("validation_errors", []),
        "timed_out": timed_out,
        "effect_gate_passed": effect_gate_passed,
        "failure_reason": None
        if effect_gate_passed
        else (
            "真实 Planner/Analyst、确定性成果、下载或副作用边界中至少一项未通过。"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run live deepseek-v4-pro effect gates")
    parser.add_argument("--api-base", default="http://127.0.0.1:8010")
    parser.add_argument("--owner", default="scenario-effect-gate-20260827")
    parser.add_argument("--scenarios", nargs="+", default=list(DEFAULT_SCENARIOS))
    parser.add_argument("--timeout-seconds", type=int, default=1_200)
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    unknown = sorted(set(args.scenarios) - {item.scenario_id for item in SCENARIO_EFFECT_SPECS})
    if unknown:
        raise SystemExit(f"未知场景: {', '.join(unknown)}")

    health = httpx.get(f"{args.api_base}/v1/health", timeout=10.0)
    health.raise_for_status()
    health_payload = health.json()
    if health_payload.get("model") != "deepseek-v4-pro":
        raise SystemExit("当前服务未配置 deepseek-v4-pro，拒绝生成伪 live evidence")
    before = _input_tree_digest()
    results: list[dict[str, Any]] = []
    with httpx.Client(
        headers={"X-User-Id": args.owner},
        timeout=httpx.Timeout(30.0, connect=10.0),
    ) as client:
        for scenario_id in args.scenarios:
            results.append(
                _run_one(
                    client,
                    api_base=args.api_base,
                    scenario_id=scenario_id,
                    timeout_seconds=args.timeout_seconds,
                    poll_seconds=args.poll_seconds,
                )
            )
    after = _input_tree_digest()
    if before != after:
        raise RuntimeError("Live Scenario Effect Gate 修改了 FORTE 原始输入")
    manifest = {
        "schema_version": "scenario-effect-gate-live.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api_base": args.api_base,
        "service": {
            "model": health_payload.get("model"),
            "checkpoint": health_payload.get("checkpoint"),
            "task_store": health_payload.get("task_store"),
        },
        "dataset": {
            "name": "FORTE public demo inputs",
            "source_commit": "345c1ec1487139db9dd319787fa9405ba85d1869",
            "input_tree_sha256": before,
            "original_inputs_modified": False,
        },
        "summary": {
            "requested": len(results),
            "passed": sum(bool(item["effect_gate_passed"]) for item in results),
            "failed": sum(not bool(item["effect_gate_passed"]) for item in results),
            "model_output_adopted": sum(
                bool(item["model_output_adopted"]) for item in results
            ),
            "run_completed": sum(
                item["run_status"] == "completed" for item in results
            ),
        },
        "scenarios": results,
        "claim_boundary": (
            "该证据仅证明固定服务配置下真实模型调用、运行工作区文件和确定性检查；"
            "不证明真实用户理解、生产安全沙箱或外部动作能力。"
        ),
    }
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["summary"], ensure_ascii=False), flush=True)
    if manifest["summary"]["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
