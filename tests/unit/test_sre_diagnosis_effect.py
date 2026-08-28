from __future__ import annotations

import csv
import io
import json
import socket
from pathlib import Path

import pytest

from services.api.app.application.sre_diagnosis_effect import (
    EXPECTED_DISPLAY_PATH,
    EXPECTED_FILE_NAME,
    EXPECTED_FILE_REF,
    SOURCE_LOGICAL_ID,
    SREDiagnosisValidationError,
    SRESourceInput,
    analyze_sre_source,
    build_sre_diagnosis,
    verify_sre_artifacts,
)


ROOT = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT / "demo-enterprise-data" / "forte" / "sre-010" / "input" / "log.txt"


def _source(content: bytes | None = None, **overrides: object) -> SRESourceInput:
    payload = LOG_PATH.read_bytes() if content is None else content
    values = {
        "logical_id": SOURCE_LOGICAL_ID,
        "file_name": EXPECTED_FILE_NAME,
        "display_path": EXPECTED_DISPLAY_PATH,
        "file_ref": EXPECTED_FILE_REF,
        "content": payload,
        "declared_size": len(payload),
        "allowlist_verified": True,
    }
    values.update(overrides)
    return SRESourceInput(**values)  # type: ignore[arg-type]


def _replace(old: str, new: str) -> bytes:
    text = LOG_PATH.read_text(encoding="utf-8")
    assert text.count(old) == 1
    return text.replace(old, new).encode("utf-8")


def test_canonical_sre_source_derives_conflicts_hypotheses_and_unexecuted_proposals() -> None:
    build = build_sre_diagnosis(_source())
    outcome = build.outcome

    assert outcome.status == "incident_review_required"
    assert outcome.source_line_count == 232
    assert outcome.cluster_facts["indices"] == [
        "order-2024-11",
        "item-search-2024-11",
        "user-activity-2024-11",
    ]
    assert outcome.node_facts["listed_count"] == 11
    assert outcome.node_facts["listed_master_count"] == 3
    assert outcome.node_facts["listed_data_count"] == 8
    assert outcome.metric_facts["query_qps_multiplier"] == 8
    assert outcome.metric_facts["write_qps_multiplier"] == 8
    assert outcome.metric_facts["search_slow_count"] == 5
    assert outcome.metric_facts["index_slow_count"] == 1
    assert outcome.metric_facts["transport_timeout_count"] == 3
    assert outcome.metric_facts["transport_recovered_count"] == 3
    assert outcome.metric_facts["circuit_reset_count"] == 1
    assert outcome.metric_facts["shard_lock_retry_success_count"] == 1
    assert outcome.metric_facts["snapshot_failure_count"] == 1
    assert outcome.metric_facts["snapshot_cleanup_count"] == 1
    assert {item.conflict_id for item in outcome.source_conflicts} == {
        "sre-conflict-node-count",
        "sre-conflict-unassigned-count",
        "sre-conflict-disk-threshold",
    }
    assert outcome.resolved_target_count == 0
    assert all(item.approval_required and not item.executed for item in outcome.action_proposals)
    assert all(item.target_status == "unresolved" for item in outcome.action_proposals)
    assert all("10.1.1.1:9200" not in (item.command_template or "") for item in outcome.action_proposals)
    assert len(build.checks) == 12
    assert all(check.passed for check in build.checks)
    assert build.report_markdown.startswith(b"# ES")
    assert build.ledger_csv.startswith(b"\xef\xbb\xbf")


def test_qps_and_baseline_change_update_report_and_verifier_without_fixed_answer() -> None:
    payload = _replace(
        "峰值 4800/s（正常基线 600/s，激增 8 倍）",
        "峰值 5600/s（正常基线 700/s，激增 8 倍）",
    )
    build = build_sre_diagnosis(_source(payload))
    assert build.outcome.metric_facts["query_qps"] == 5600
    assert build.outcome.metric_facts["query_qps_baseline"] == 700
    assert b"5600" in build.report_markdown
    assert all(check.passed for check in build.checks)


def test_inconsistent_qps_multiplier_fails_closed() -> None:
    payload = _replace(
        "峰值 4800/s（正常基线 600/s，激增 8 倍）",
        "峰值 4800/s（正常基线 600/s，激增 7 倍）",
    )
    with pytest.raises(SREDiagnosisValidationError, match="倍数不一致"):
        analyze_sre_source(_source(payload))


def test_each_source_conflict_disappears_only_when_its_source_facts_are_reconciled() -> None:
    node_fixed = analyze_sre_source(_source(_replace("节点总数: 10", "节点总数: 11")))
    assert "sre-conflict-node-count" not in {item.conflict_id for item in node_fixed.source_conflicts}
    assert "sre-conflict-unassigned-count" in {item.conflict_id for item in node_fixed.source_conflicts}

    shard_fixed = analyze_sre_source(
        _source(
            _replace(
                "96   48    0     0    48       0",
                "72   48    0     0    24       0",
            )
        )
    )
    assert "sre-conflict-unassigned-count" not in {
        item.conflict_id for item in shard_fixed.source_conflicts
    }
    assert "sre-conflict-node-count" in {item.conflict_id for item in shard_fixed.source_conflicts}


def test_removing_gc_event_evidence_lowers_hypothesis_confidence() -> None:
    text = LOG_PATH.read_text(encoding="utf-8")
    mutated = "\n".join(
        line.replace("o.e.m.j.JvmGcMonitorService", "o.e.x.UnclassifiedMonitor")
        for line in text.splitlines()
    ).encode("utf-8")
    outcome = analyze_sre_source(_source(mutated))
    hypothesis = next(
        item for item in outcome.hypotheses if item.hypothesis_id.endswith("capacity-query-amplification")
    )
    assert outcome.metric_facts["gc_event_count"] == 0
    assert hypothesis.confidence == "low"
    assert outcome.unclassified_count > 0


def test_unknown_anomaly_is_retained_for_manual_review() -> None:
    text = LOG_PATH.read_text(encoding="utf-8")
    payload = text.replace(
        '  "allocate_explanation":',
        "新型故障信号: mystery-condition=1\n  \"allocate_explanation\":",
    ).encode("utf-8")
    outcome = analyze_sre_source(_source(payload))
    assert any(
        item.status == "unclassified" and "mystery-condition" in item.excerpt
        for item in outcome.observations
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("logical_id", "wrong"),
        ("file_name", "other.txt"),
        ("display_path", "其他/log.txt"),
        ("file_ref", "forte-wrong"),
        ("allowlist_verified", False),
    ],
)
def test_source_identity_boundary_fails_closed(field: str, value: object) -> None:
    with pytest.raises(SREDiagnosisValidationError):
        analyze_sre_source(_source(**{field: value}))


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x00\x01binary",
        "不完整日志".encode(),
        _replace("节点总数: 10", "节点总数: NaN"),
        _replace("[日志片段 9: 运维人员在 00:38 执行的 API 诊断结果]", "[日志片段 8: 重复]")
    ],
)
def test_empty_binary_truncated_invalid_number_or_missing_section_fails_closed(payload: bytes) -> None:
    with pytest.raises(SREDiagnosisValidationError):
        analyze_sre_source(_source(payload))


def test_generated_markdown_and_csv_are_reparsed_and_tampering_turns_checks_red() -> None:
    source = _source()
    build = build_sre_diagnosis(source)
    damaged_report = build.report_markdown.replace(
        b"sre-conflict-node-count", b"sre-conflict-hidden", 1
    )
    report_checks = verify_sre_artifacts(
        source,
        report_markdown=damaged_report,
        ledger_csv=build.ledger_csv,
    )
    assert any(not check.passed for check in report_checks)

    rows = list(csv.reader(io.StringIO(build.ledger_csv.decode("utf-8-sig"))))
    rows[1][3] = "tampered observation"
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerows(rows)
    ledger_checks = verify_sre_artifacts(
        source,
        report_markdown=build.report_markdown,
        ledger_csv=output.getvalue().encode("utf-8-sig"),
    )
    assert any(not check.passed for check in ledger_checks)


def test_adapter_source_contains_no_network_or_command_execution_api() -> None:
    module = (
        ROOT / "services" / "api" / "app" / "application" / "sre_diagnosis_effect.py"
    ).read_text(encoding="utf-8")
    forbidden = (
        "import requests",
        "import httpx",
        "import socket",
        "import subprocess",
        "Invoke-WebRequest",
        "os.system(",
        "subprocess.run(",
    )
    assert all(token not in module for token in forbidden)


def test_adapter_runtime_never_opens_a_network_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts: list[str] = []

    def deny_connect(*_args: object, **_kwargs: object) -> None:
        attempts.append("connect")
        raise AssertionError("TC-14 deterministic adapter attempted a network connection")

    monkeypatch.setattr(socket.socket, "connect", deny_connect)
    monkeypatch.setattr(socket, "create_connection", deny_connect)

    build = build_sre_diagnosis(_source())

    assert all(check.passed for check in build.checks)
    assert attempts == []


def test_public_manifests_are_generated_from_the_same_source_derived_outcome() -> None:
    canonical = json.loads(
        (
            ROOT
            / "docs"
            / "evidence"
            / "manifests"
            / "tc14-public-sre-diagnosis-outcome-20260829.json"
        ).read_text(encoding="utf-8")
    )
    dynamic = json.loads(
        (
            ROOT
            / "docs"
            / "evidence"
            / "manifests"
            / "tc14-public-sre-diagnosis-outcome-dynamic-20260829.json"
        ).read_text(encoding="utf-8")
    )
    expected = build_sre_diagnosis(_source())
    assert canonical["sre_diagnosis_outcome"] == expected.outcome.model_dump(mode="json")
    assert canonical["checks"] == [
        {
            "check_id": item.check_id,
            "label": item.label,
            "passed": item.passed,
            "detail": item.detail,
        }
        for item in expected.checks
    ]
    assert dynamic["sre_diagnosis_outcome"]["metric_facts"]["query_qps"] == 5600
    assert dynamic["sre_diagnosis_outcome"]["node_facts"]["declared_count"] == 11
    assert dynamic["sre_diagnosis_outcome"]["conflict_count"] == 2
