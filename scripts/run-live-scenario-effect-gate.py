from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
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
                    encoding="utf-8",
                    errors="replace",
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
                    encoding="utf-8",
                    errors="replace",
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


def _tc04_zip_content_gate(content: bytes) -> dict[str, Any]:
    project_prefix = "evaluation-platform/"
    source_root = FORTE_ROOT / "dev-015" / "input" / "source-code"
    source_files = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*")
        if path.is_file()
    }
    changed_files = {
        "app/services/model_service.py",
        "app/services/dataset_service.py",
        "app/engine/evaluation_engine.py",
    }
    required_support_files = {
        "run_self_test.py",
        "requirements-test.txt",
        "test-manifest.json",
        "test-results.json",
        "baseline-test-results.json",
        "changes.patch",
        "changes.json",
        "修复说明.md",
        "TC-04自测卡.md",
        "test-report.md",
    }
    expected_project_members = {
        f"{project_prefix}{name}" for name in source_files
    }
    expected_support_members = {
        f"{project_prefix}{name}" for name in required_support_files
    }
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
            missing = sorted(
                (expected_project_members | expected_support_members) - names
            )
            if unsafe or missing:
                return {
                    "passed": False,
                    "valid_zip": True,
                    "unsafe_members": unsafe,
                    "missing_members": missing,
                }

            unchanged_source_files = {
                name: (
                    hashlib.sha256(archive.read(f"{project_prefix}{name}")).hexdigest()
                    == hashlib.sha256(path.read_bytes()).hexdigest()
                )
                for name, path in source_files.items()
                if name not in changed_files
            }
            changed_source_files = {
                name: (
                    hashlib.sha256(archive.read(f"{project_prefix}{name}")).hexdigest()
                    != hashlib.sha256(source_files[name].read_bytes()).hexdigest()
                )
                for name in changed_files
            }
            manifest = json.loads(
                archive.read(f"{project_prefix}test-manifest.json")
            )
            declared_result = json.loads(
                archive.read(f"{project_prefix}test-results.json")
            )
            baseline_result = json.loads(
                archive.read(f"{project_prefix}baseline-test-results.json")
            )
            changes = json.loads(archive.read(f"{project_prefix}changes.json"))

            with tempfile.TemporaryDirectory(prefix="tc04-live-download-") as directory:
                root = Path(directory)
                archive.extractall(root)
                project_root = root / "evaluation-platform"
                env = {
                    "PATH": os.environ.get("PATH", ""),
                    "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                    "WINDIR": os.environ.get("WINDIR", ""),
                    "TEMP": os.environ.get("TEMP", directory),
                    "TMP": os.environ.get("TMP", directory),
                    "PYTHONNOUSERSITE": "1",
                    "HTTP_PROXY": "",
                    "HTTPS_PROXY": "",
                    "ALL_PROXY": "",
                    "NO_PROXY": "*",
                }
                compile_started = time.monotonic()
                compiled = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "compileall",
                        "-q",
                        "app",
                        "tests",
                        "run_self_test.py",
                    ],
                    cwd=project_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=120,
                )
                compile_ms = int((time.monotonic() - compile_started) * 1000)
                test_started = time.monotonic()
                tested = subprocess.run(
                    [sys.executable, "run_self_test.py"],
                    cwd=project_root,
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=120,
                )
                test_ms = int((time.monotonic() - test_started) * 1000)
                rerun_result = json.loads(
                    (project_root / "test-results.json").read_text(encoding="utf-8")
                )

        declared_ids = sorted(manifest.get("declared_test_ids", []))
        archived_ids = sorted(declared_result.get("collected_test_ids", []))
        rerun_ids = sorted(rerun_result.get("collected_test_ids", []))
        manifest_consistent = (
            len(declared_ids) == 117
            and declared_ids == archived_ids == rerun_ids
            and declared_result.get("manifest_consistent") is True
            and rerun_result.get("manifest_consistent") is True
        )
        baseline_red_count = int(baseline_result.get("failed", 0)) + int(
            baseline_result.get("errors", 0)
        )
        changed_coverage = changes.get("changed_source_coverage_percent", {})
        changed_coverage_ok = (
            set(changed_coverage) == changed_files
            and all(float(value) >= 80.0 for value in changed_coverage.values())
        )
        final_results_match = all(
            result.get("status") == "passed"
            and result.get("collected") == 117
            and result.get("passed") == 117
            and result.get("failed") == 0
            and result.get("errors") == 0
            for result in (declared_result, rerun_result)
        )
        source_copy_ok = (
            len(source_files) == 44
            and all(unchanged_source_files.values())
            and all(changed_source_files.values())
            and set(changes.get("modified_files", [])) == changed_files
            and changes.get("source_file_count") == 44
            and changes.get("source_input_modified") is False
        )
        passed = (
            compiled.returncode == 0
            and tested.returncode == 0
            and source_copy_ok
            and manifest_consistent
            and final_results_match
            and baseline_red_count == 5
            and changed_coverage_ok
        )
        return {
            "passed": passed,
            "valid_zip": True,
            "file_count": len(names),
            "source_file_count": len(source_files),
            "missing_members": [],
            "unsafe_members": [],
            "source_copy": {
                "unchanged_file_count": sum(unchanged_source_files.values()),
                "expected_unchanged_file_count": len(source_files) - len(changed_files),
                "changed_files": sorted(
                    name for name, changed in changed_source_files.items() if changed
                ),
                "passed": source_copy_ok,
            },
            "compile": {"exit_code": compiled.returncode, "elapsed_ms": compile_ms},
            "tests": {
                "exit_code": tested.returncode,
                "elapsed_ms": test_ms,
                "collected": rerun_result.get("collected"),
                "passed": rerun_result.get("passed"),
                "failed": rerun_result.get("failed"),
                "errors": rerun_result.get("errors"),
                "manifest_consistent": manifest_consistent,
            },
            "baseline_red_count": baseline_red_count,
            "changed_source_coverage_percent": changed_coverage,
            "changed_source_coverage_gate_passed": changed_coverage_ok,
            "network_boundary": (
                "复跑进程阻断非 loopback socket.connect，HTTP 测试使用 MockTransport；"
                "这不是 OS 级断网或通用代码沙箱。"
            ),
        }
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        return {
            "passed": False,
            "valid_zip": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        }


def _tc12_zip_content_gate(content: bytes) -> dict[str, Any]:
    project_prefix = "dashboard-toolkit/"
    source_root = FORTE_ROOT / "qa-003" / "input" / "dashboard-toolkit"
    source_files = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*")
        if path.is_file()
    }
    changed_files = {
        "vitest.config.js",
        "src/utils/metricsCalculator.js",
        "src/utils/dataTransformer.js",
        "src/utils/filterEngine.js",
    }
    required_support_files = {
        "tests/metricsCalculator.test.js",
        "tests/dataTransformer.test.js",
        "tests/filterEngine.test.js",
        "changes.patch",
        "changes.json",
        "test-manifest.json",
        "run-self-test.mjs",
        "TC-12测试报告.md",
        "TC-12改动说明.md",
        "TC-12自测卡.md",
        "evidence/stage-a-original-result.json",
        "evidence/stage-b-config-only-result.json",
        "evidence/stage-c-export-only-result.json",
        "evidence/stage-d-final-result.json",
        "evidence/coverage-summary.json",
        "evidence/independent-unpack-rerun.json",
    }
    expected_members = {
        f"{project_prefix}{name}"
        for name in set(source_files) | required_support_files
    }
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
            missing = sorted(expected_members - names)
            if unsafe or missing:
                return {
                    "passed": False,
                    "valid_zip": True,
                    "unsafe_members": unsafe,
                    "missing_members": missing,
                }
            manifest = json.loads(
                archive.read(f"{project_prefix}test-manifest.json")
            )
            stages = {
                stage: json.loads(
                    archive.read(
                        f"{project_prefix}evidence/{stage}-result.json"
                    )
                )
                for stage in (
                    "stage-a-original",
                    "stage-b-config-only",
                    "stage-c-export-only",
                    "stage-d-final",
                )
            }
            changes = json.loads(archive.read(f"{project_prefix}changes.json"))
            independent = json.loads(
                archive.read(
                    f"{project_prefix}evidence/independent-unpack-rerun.json"
                )
            )
            unchanged_source_files = {
                name: hashlib.sha256(
                    archive.read(f"{project_prefix}{name}")
                ).hexdigest()
                == hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in source_files.items()
                if name not in changed_files
            }
            changed_source_files = {
                name: hashlib.sha256(
                    archive.read(f"{project_prefix}{name}")
                ).hexdigest()
                != hashlib.sha256(source_files[name].read_bytes()).hexdigest()
                for name in changed_files
            }
            with tempfile.TemporaryDirectory(prefix="tc12-live-download-") as directory:
                root = Path(directory)
                archive.extractall(root)
                project_root = root / "dashboard-toolkit"
                node = shutil.which("node")
                if node is None:
                    raise RuntimeError("Node is unavailable")
                vitest_entry = (
                    REPO_ROOT
                    / "apps"
                    / "web"
                    / "node_modules"
                    / "vitest"
                    / "vitest.mjs"
                )
                started = time.monotonic()
                tested = subprocess.run(
                    [node, str(project_root / "run-self-test.mjs"), str(vitest_entry)],
                    cwd=root,
                    env={
                        "PATH": os.environ.get("PATH", ""),
                        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
                        "WINDIR": os.environ.get("WINDIR", ""),
                        "TEMP": os.environ.get("TEMP", directory),
                        "TMP": os.environ.get("TMP", directory),
                        "HTTP_PROXY": "",
                        "HTTPS_PROXY": "",
                        "ALL_PROXY": "",
                        "NO_PROXY": "*",
                    },
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=120,
                    check=False,
                )
                elapsed_ms = int((time.monotonic() - started) * 1_000)
                rerun = json.loads(
                    (project_root / "self-test-results.json").read_text(
                        encoding="utf-8"
                    )
                )

        declared_ids = sorted(manifest.get("declared_test_ids", []))
        final_ids = sorted(stages["stage-d-final"].get("collected_test_ids", []))
        rerun_ids = sorted(rerun.get("collected_test_ids", []))
        coverage_files = rerun.get("coverage_files", [])
        coverage_ok = len(coverage_files) == 3 and all(
            float(item.get("statements", {}).get("pct", 0)) >= 85
            and float(item.get("lines", {}).get("pct", 0)) >= 85
            and float(item.get("branches", {}).get("pct", 0)) >= 75
            for item in coverage_files
        )
        stage_gate = (
            stages["stage-a-original"].get("exit_code") != 0
            and stages["stage-a-original"].get("num_total_tests") == 0
            and stages["stage-b-config-only"].get("num_failed_tests") == 7
            and stages["stage-c-export-only"].get("num_failed_tests") == 6
            and stages["stage-d-final"].get("exit_code") == 0
            and stages["stage-d-final"].get("num_passed_tests") == 71
            and stages["stage-d-final"].get("num_failed_tests") == 0
        )
        manifest_consistent = (
            len(declared_ids) == 71
            and declared_ids == final_ids == rerun_ids
            and rerun.get("manifest_consistent") is True
        )
        source_copy_ok = (
            len(source_files) == 11
            and all(unchanged_source_files.values())
            and all(changed_source_files.values())
            and set(changes.get("changed_files", [])) == changed_files
        )
        passed = (
            tested.returncode == 0
            and rerun.get("status") == "passed"
            and rerun.get("coverage_ok") is True
            and independent.get("status") == "passed"
            and stage_gate
            and manifest_consistent
            and coverage_ok
            and source_copy_ok
        )
        return {
            "passed": passed,
            "valid_zip": True,
            "file_count": len(names),
            "source_file_count": len(source_files),
            "missing_members": [],
            "unsafe_members": [],
            "source_copy": {
                "unchanged_file_count": sum(unchanged_source_files.values()),
                "expected_unchanged_file_count": len(source_files) - len(changed_files),
                "changed_files": sorted(
                    name for name, changed in changed_source_files.items() if changed
                ),
                "passed": source_copy_ok,
            },
            "stages": {
                "stage_a_exit_code": stages["stage-a-original"].get("exit_code"),
                "stage_b_failed": stages["stage-b-config-only"].get(
                    "num_failed_tests"
                ),
                "stage_c_failed": stages["stage-c-export-only"].get(
                    "num_failed_tests"
                ),
                "stage_d_passed": stages["stage-d-final"].get(
                    "num_passed_tests"
                ),
            },
            "tests": {
                "exit_code": tested.returncode,
                "elapsed_ms": elapsed_ms,
                "collected": len(rerun_ids),
                "passed": rerun.get("passed"),
                "failed": rerun.get("failed"),
                "manifest_consistent": manifest_consistent,
            },
            "coverage_files": coverage_files,
            "coverage_gate_passed": coverage_ok,
            "network_boundary": (
                "本次固定测试未观察到网络调用且未注入凭据或代理；"
                "没有进程或 OS 级 socket 隔离。"
            ),
        }
    except (
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        subprocess.SubprocessError,
    ) as exc:
        return {
            "passed": False,
            "valid_zip": False,
            "error": type(exc).__name__,
            "detail": str(exc),
        }


def _tc10_docx_content_gate(content: bytes) -> dict[str, Any]:
    required_tokens = (
        "这是流程设计，不是拨号、CRM/短信执行，也不是法律意见",
        "批准来源仅笼统提及监管机构，没有制度版本、批准主体或当前有效性证明",
        "最终合规审批未发生",
        "PTP登记",
        "转人工跟进",
        "安排重拨",
        "停止外呼（达上限）",
        "加入禁呼名单",
        "案件升级",
    )
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        tables = [
            [
                ["".join(cell.itertext()).strip() for cell in row.findall("./w:tc", namespace)]
                for row in table.findall("./w:tr", namespace)
            ]
            for table in root.findall(".//w:tbl", namespace)
        ]
        text = "\n".join(root.itertext())
        integrity = {
            row[0]: row[1]
            for row in tables[5][1:]
            if len(row) >= 2 and row[0]
        }
        counts = {
            "rules": int(integrity["atomic_requirement_count"]),
            "nodes": int(integrity["node_count"]),
            "edges": int(integrity["edge_count"]),
            "guards": int(integrity["guard_count"]),
            "terminals": int(integrity["terminal_count"]),
            "reachable_terminals": int(integrity["reachable_terminal_count"]),
        }
    except (
        IndexError,
        KeyError,
        OSError,
        ValueError,
        zipfile.BadZipFile,
        ElementTree.ParseError,
    ) as exc:
        return {
            "passed": False,
            "valid_docx": False,
            "paragraph_count": 0,
            "table_count": 0,
            "missing_tokens": list(required_tokens),
            "error": type(exc).__name__,
        }
    expected_headers = (
        ["rule_id", "group", "locator", "excerpt", "parameters", "expected_relation", "expected_action", "coverage_state", "mapped_elements"],
        ["node_id", "label", "kind", "source_rule_ids", "future_action"],
        ["edge_id", "from_node_id", "to_node_id", "label", "guard_ids", "source_rule_ids", "future_action"],
        ["guard_id", "label", "parameters", "source_rule_ids"],
        ["terminal_id", "node_id", "label", "source_rule_ids", "source_listed"],
        ["fact", "value"],
    )
    headers_match = len(tables) == 6 and all(
        table and table[0] == header for table, header in zip(tables, expected_headers, strict=True)
    )
    row_counts_match = len(tables) == 6 and [len(table) - 1 for table in tables[:5]] == [
        counts["rules"],
        counts["nodes"],
        counts["edges"],
        counts["guards"],
        counts["terminals"],
    ]
    ids_unique = len(tables) == 6 and all(
        len({row[0] for row in table[1:]}) == len(table) - 1 for table in tables[:5]
    )
    rule_rows = tables[0][1:]
    edge_rows = tables[2][1:]
    rules_located_and_covered = all(
        row[2].startswith("专业性说明.md:L") and row[7] == "covered" and row[8]
        for row in rule_rows
    )
    edge_pairs = {(row[1], row[2]) for row in edge_rows}
    source_order_present = {
        ("out-node-decision-identity", "out-node-recording-notice"),
        ("out-node-recording-notice", "out-node-introduce-purpose"),
        ("out-node-introduce-purpose", "out-node-payment-guidance"),
    }.issubset(edge_pairs)
    integrity_passed = all(
        integrity.get(name) == "true"
        for name in (
            "unique_start",
            "unique_ids",
            "no_dangling_edges",
            "all_nodes_reachable",
            "every_nonterminal_has_outgoing",
            "every_node_can_reach_terminal",
            "all_terminals_reachable",
            "critical_order_valid",
            "third_party_boundary_valid",
            "all_rules_mapped",
        )
    ) and integrity.get("status") == "approval_required" and integrity.get("external_action") == "none"
    paragraph_count = len(root.findall(".//w:p", namespace))
    missing = [token for token in required_tokens if token not in text]
    return {
        "passed": (
            not missing
            and headers_match
            and row_counts_match
            and ids_unique
            and rules_located_and_covered
            and source_order_present
            and integrity_passed
            and counts["terminals"] == counts["reachable_terminals"]
        ),
        "valid_docx": True,
        "paragraph_count": paragraph_count,
        "table_count": len(tables),
        "counts": counts,
        "headers_match": headers_match,
        "row_counts_match": row_counts_match,
        "ids_unique": ids_unique,
        "rules_located_and_covered": rules_located_and_covered,
        "source_order_present": source_order_present,
        "integrity_passed": integrity_passed,
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
        "scenario_effect_failed",
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
        elif (
            response.status_code == 200
            and artifact.get("scenario_id") == "TC-04"
            and artifact.get("media_type") == "application/zip"
        ):
            content_gate = _tc04_zip_content_gate(response.content)
        elif (
            response.status_code == 200
            and artifact.get("scenario_id") == "TC-12"
            and artifact.get("media_type") == "application/zip"
        ):
            content_gate = _tc12_zip_content_gate(response.content)
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
    existing_run_id: str | None = None,
) -> dict[str, Any]:
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == scenario_id)
    started_at = datetime.now(timezone.utc)
    if existing_run_id is None:
        idempotency_key = (
            f"scenario-effect-live-{scenario_id.lower()}-{uuid.uuid4().hex}"
        )
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
    else:
        run_id = existing_run_id
        response = client.get(f"{api_base}/v1/harness/runs/{run_id}")
        response.raise_for_status()
        snapshot = response.json()
        if snapshot.get("instruction") != spec.instruction:
            raise RuntimeError(
                f"Run {run_id} 的用户指令与 {scenario_id} 固定效果门不一致"
            )
        created_at = snapshot.get("created_at")
        if created_at:
            started_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    deadline = time.monotonic() + timeout_seconds
    run_started_monotonic = time.monotonic()
    previous_marker: tuple[Any, ...] | None = None
    timed_out = False
    run_get_latencies_ms: list[int] = []
    active_run_get_latencies_ms: list[int] = []
    active_health_latencies_ms: list[int] = []
    sse_probe: dict[str, Any] | None = None
    while True:
        snapshot_started = time.monotonic()
        snapshot_response = client.get(f"{api_base}/v1/harness/runs/{run_id}")
        snapshot_elapsed_ms = int((time.monotonic() - snapshot_started) * 1_000)
        run_get_latencies_ms.append(snapshot_elapsed_ms)
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
        started_events = [
            item
            for item in snapshot.get("events", [])
            if item.get("event_name") == "deterministic_office_tool_started"
            and item.get("details", {}).get("scenario_id") == scenario_id
        ]
        effect_active = bool(started_events) and not receipts and not any(
            item.get("event_name") == "scenario_effect_failed"
            and item.get("details", {}).get("scenario_id") == scenario_id
            for item in snapshot.get("events", [])
        )
        if effect_active:
            active_run_get_latencies_ms.append(snapshot_elapsed_ms)
            health_started = time.monotonic()
            health_response = client.get(f"{api_base}/v1/health")
            health_elapsed_ms = int((time.monotonic() - health_started) * 1_000)
            health_response.raise_for_status()
            active_health_latencies_ms.append(health_elapsed_ms)
            if sse_probe is None:
                started_sequence = int(started_events[-1]["sequence"])
                stream_started = time.monotonic()
                observed_event: str | None = None
                with client.stream(
                    "GET",
                    f"{api_base}/v1/harness/runs/{run_id}/events",
                    params={"after": max(0, started_sequence - 1)},
                ) as stream_response:
                    stream_response.raise_for_status()
                    for line in stream_response.iter_lines():
                        if line.startswith("event: "):
                            observed_event = line.removeprefix("event: ").strip()
                            break
                sse_probe = {
                    "event_name": observed_event,
                    "elapsed_ms": int((time.monotonic() - stream_started) * 1_000),
                    "after_sequence": max(0, started_sequence - 1),
                }
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
    request_latency_limit_ms = 5_000
    responsiveness_gate_passed = scenario_id != "TC-04" or (
        bool(active_run_get_latencies_ms)
        and bool(active_health_latencies_ms)
        and max(run_get_latencies_ms, default=request_latency_limit_ms + 1)
        <= request_latency_limit_ms
        and max(active_health_latencies_ms, default=request_latency_limit_ms + 1)
        <= request_latency_limit_ms
        and sse_probe is not None
        and sse_probe.get("event_name") == "deterministic_office_tool_started"
        and int(sse_probe.get("elapsed_ms", request_latency_limit_ms + 1))
        <= request_latency_limit_ms
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
        and responsiveness_gate_passed
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
        "api_responsiveness": {
            "client_total_timeout_seconds": 180,
            "request_latency_gate_ms": request_latency_limit_ms,
            "run_get_sample_count": len(run_get_latencies_ms),
            "run_get_max_ms": max(run_get_latencies_ms, default=None),
            "effect_active_run_get_sample_count": len(active_run_get_latencies_ms),
            "effect_active_run_get_max_ms": max(
                active_run_get_latencies_ms, default=None
            ),
            "effect_active_health_sample_count": len(active_health_latencies_ms),
            "effect_active_health_max_ms": max(
                active_health_latencies_ms, default=None
            ),
            "sse_probe": sse_probe,
            "scenario_elapsed_ms": int(
                (time.monotonic() - run_started_monotonic) * 1_000
            ),
            "passed": responsiveness_gate_passed,
            "boundary": (
                "总任务可持续约一分钟；这里验证的是单次 Run GET、health 与 SSE 请求"
                "未被同步构建阻塞，不证明线程内子进程可跨进程续跑。"
            ),
        },
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
                "outbound_flow_outcome": item.get("outbound_flow_outcome"),
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
    parser.add_argument(
        "--run-id",
        help="复用一个已经创建的 Run；仅允许与单个 --scenarios 一起使用。",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    unknown = sorted(set(args.scenarios) - {item.scenario_id for item in SCENARIO_EFFECT_SPECS})
    if unknown:
        raise SystemExit(f"未知场景: {', '.join(unknown)}")
    if args.run_id and len(args.scenarios) != 1:
        raise SystemExit("--run-id 只能与单个 --scenarios 一起使用")

    before = _input_tree_digest()
    results: list[dict[str, Any]] = []
    with httpx.Client(
        headers={"X-User-Id": args.owner},
        timeout=httpx.Timeout(180.0, connect=10.0),
        trust_env=False,
    ) as client:
        health = client.get(f"{args.api_base}/v1/health")
        health.raise_for_status()
        health_payload = health.json()
        if health_payload.get("model") != "deepseek-v4-pro":
            raise SystemExit("当前服务未配置 deepseek-v4-pro，拒绝生成伪 live evidence")
        for scenario_id in args.scenarios:
            results.append(
                _run_one(
                    client,
                    api_base=args.api_base,
                    scenario_id=scenario_id,
                    timeout_seconds=args.timeout_seconds,
                    poll_seconds=args.poll_seconds,
                    existing_run_id=args.run_id,
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
