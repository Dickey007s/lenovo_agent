from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.release_readiness_effect import (
    ReleaseReadinessValidationError,
    build_release_readiness,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
)


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"


@pytest.fixture(scope="module")
def catalog() -> BenchmarkWorkspaceCatalog:
    return BenchmarkWorkspaceCatalog(FORTE_ROOT)


def _spec():
    return next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-11")


def _previews(catalog: BenchmarkWorkspaceCatalog) -> dict[str, dict]:
    return copy.deepcopy(ScenarioEffectEngine._previews(catalog, _spec()))


def _row(previews: dict[str, dict], file_name: str, code: str) -> dict:
    return next(
        row
        for row in previews[file_name]["rows"]
        if row["values"] and row["values"][0] == code
    )


def _record(build, code: str):
    return next(item for item in build.outcome.records if item.record_id == code)


def test_tc11_derives_gates_ledger_and_two_parseable_artifacts_from_sources(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    previews = _previews(catalog)
    build = build_release_readiness(previews)

    assert build.outcome.status == "failed"
    assert build.outcome.decision == "不得上线"
    assert build.outcome.failed_gate_count == 4
    assert [
        (gate.numerator, gate.denominator, gate.actual, gate.passed)
        for gate in build.outcome.gates
    ] == [
        (5.0, 7.0, 71.4, False),
        (4.0, 5.0, 80.0, False),
        (2.0, 5.0, 40.0, False),
        (4.0, 1.0, 4.0, False),
    ]
    assert [metric.value for metric in build.outcome.auxiliary_metrics] == [
        93.4,
        86.4,
        85.7,
        89.7,
    ]
    assert build.risk_counts == {"severe": 4, "major": 2, "minor": 2}
    assert build.missing_feature_codes == ("F13", "F09", "F15", "F11", "F18")
    assert len(build.outcome.records) == 18
    assert all(item.source_locations for item in build.outcome.records)
    assert all(item.owner and item.exit_condition for item in build.outcome.records)

    ledger = list(csv.DictReader(io.StringIO(build.ledger_csv.decode("utf-8-sig"))))
    assert len(ledger) == 18
    assert {item["最终等级"] for item in ledger} == {"无", "次要", "主要", "严重"}
    assert sum(item["最终等级"] == "严重" for item in ledger) == 4
    assert sum(item["最终等级"] == "主要" for item in ledger) == 2
    assert sum(item["最终等级"] == "次要" for item in ledger) == 2
    with zipfile.ZipFile(io.BytesIO(build.report_docx)) as package:
        document = package.read("word/document.xml").decode("utf-8")
    assert document.count("<w:tbl>") >= 6
    assert "上线结论：不得上线" in document
    assert "18 项逐功能矩阵" in document
    assert "5 项未提测功能" in document
    assert "没有执行上线、没有修改配置" in document


def test_tc11_original_four_source_bytes_are_unchanged(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    spec = _spec()
    workspace = catalog.public_workspace()
    index = {
        (folder["display_label"], item["display_label"]): item["file_ref"]
        for folder in workspace["folders"]
        for item in folder["files"]
    }
    refs = [index[item] for item in spec.source_labels]
    before = {
        file_ref: hashlib.sha256(catalog.checked_input_bytes(file_ref)).hexdigest()
        for file_ref in refs
    }

    execution = ScenarioEffectEngine().execute(spec.instruction, catalog)

    assert execution is not None
    assert execution.status == "passed"
    assert [item.file_name for item in execution.artifacts] == [
        "上线合规与风险报告.docx",
        "上线功能风险逐项台账.csv",
    ]
    assert all(item.business_gate_outcome is not None for item in execution.artifacts)
    assert "业务 Gate 未通过" in execution.result
    after = {
        file_ref: hashlib.sha256(catalog.checked_input_bytes(file_ref)).hexdigest()
        for file_ref in refs
    }
    assert after == before


def test_tc11_frontend_fixture_matches_the_server_public_business_manifest(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "evidence"
            / "manifests"
            / "tc11-business-gate-outcome-20260828.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest == build_release_readiness(_previews(catalog)).outcome.model_dump(
        mode="json"
    )


def test_tc11_risk_mutations_change_results_without_expected_name_constants(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    f17_previews = _previews(catalog)
    f17 = _row(f17_previews, "线上兼容环境测试报告.xlsx", "F17")
    anomaly_indexes = [
        index
        for index, value in enumerate(f17["values"][4:], start=4)
        if value in {"部分通过", "兼容问题"}
    ]
    for index in anomaly_indexes[2:]:
        f17["values"][index] = "通过"
    assert _record(build_release_readiness(f17_previews), "F17").final_risk_level == "minor"

    f05_previews = _previews(catalog)
    f05 = _row(f05_previews, "功能测试报告.xlsx", "F05")
    f05["values"][10] = "界面缺陷"
    assert _record(build_release_readiness(f05_previews), "F05").final_risk_level == "minor"

    f02_previews = _previews(catalog)
    f02_test = _row(f02_previews, "功能测试报告.xlsx", "F02")
    f02_test["values"][8] = f02_test["values"][7]
    f02_test["values"][9] = "通过"
    f02_test["values"][10] = "—"
    f02_test["values"][11] = "—"
    f02_compat = _row(f02_previews, "线上兼容环境测试报告.xlsx", "F02")
    f02_compat["values"][4:] = ["通过"] * 8
    assert _record(build_release_readiness(f02_previews), "F02").final_risk_level == "none"


@pytest.mark.parametrize(
    ("mutation", "error_code"),
    [
        ("duplicate-id", "duplicate-id"),
        ("unknown-id", "unknown-feature"),
        ("name-conflict", "feature-name-conflict"),
        ("priority-conflict", "feature-priority-conflict"),
        ("config-status", "config-status-invalid"),
        ("test-conclusion", "test-conclusion-invalid"),
        ("test-nonnumeric", "test-count-invalid"),
        ("test-negative", "test-count-invalid"),
        ("test-passed-over-total", "test-count-order"),
        ("compat-status", "compatibility-status-invalid"),
        ("duplicate-environment", "compatibility-environment-duplicate"),
    ],
)
def test_tc11_rejects_malformed_source_rows(
    catalog: BenchmarkWorkspaceCatalog,
    mutation: str,
    error_code: str,
) -> None:
    previews = _previews(catalog)
    if mutation == "duplicate-id":
        row = _row(previews, "上线配置清单.xlsx", "F17")
        row["values"][:5] = _row(previews, "上线配置清单.xlsx", "F01")["values"][:5]
    elif mutation == "unknown-id":
        _row(previews, "上线配置清单.xlsx", "F17")["values"][0] = "F99"
    elif mutation == "name-conflict":
        _row(previews, "上线配置清单.xlsx", "F01")["values"][1] = "错误名称"
    elif mutation == "priority-conflict":
        _row(previews, "上线配置清单.xlsx", "F01")["values"][3] = "P1"
    elif mutation == "config-status":
        _row(previews, "上线配置清单.xlsx", "F01")["values"][7] = "准备好了"
    elif mutation == "test-conclusion":
        _row(previews, "功能测试报告.xlsx", "F01")["values"][9] = "大概通过"
    elif mutation == "test-nonnumeric":
        _row(previews, "功能测试报告.xlsx", "F01")["values"][7] = "十二"
    elif mutation == "test-negative":
        _row(previews, "功能测试报告.xlsx", "F01")["values"][8] = "-1"
    elif mutation == "test-passed-over-total":
        _row(previews, "功能测试报告.xlsx", "F01")["values"][8] = "13"
    elif mutation == "compat-status":
        _row(previews, "线上兼容环境测试报告.xlsx", "F01")["values"][4] = "未知"
    elif mutation == "duplicate-environment":
        headers = previews["线上兼容环境测试报告.xlsx"]["rows"]
        headers[0]["values"][-1] = headers[0]["values"][-2]
        headers[1]["values"][-1] = headers[1]["values"][-2]
    with pytest.raises(ReleaseReadinessValidationError) as exc_info:
        build_release_readiness(previews)
    assert exc_info.value.code == error_code


def test_tc11_zero_denominator_is_an_explicit_failure(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    previews = _previews(catalog)
    p1_codes = {"F03", "F04", "F05", "F08", "F16"}
    text = previews["PRD_v2.5.md"]["text"]
    for code in p1_codes:
        text = text.replace(f"| {code} |", f"| {code} |", 1)
        line = next(line for line in text.splitlines() if line.startswith(f"| {code} |"))
        text = text.replace(line, line.replace("| P1 |", "| P2 |"), 1)
    previews["PRD_v2.5.md"]["text"] = text
    for file_name in (
        "上线配置清单.xlsx",
        "功能测试报告.xlsx",
        "线上兼容环境测试报告.xlsx",
    ):
        for code in p1_codes:
            _row(previews, file_name, code)["values"][3] = "P2"

    with pytest.raises(ReleaseReadinessValidationError) as exc_info:
        build_release_readiness(previews)
    assert exc_info.value.code == "zero-denominator"


def test_tc11_source_failure_returns_failed_artifact_not_business_green(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    class InvalidCatalog:
        def public_workspace(self):
            return catalog.public_workspace()

        def public_file(self, file_ref: str):
            preview = copy.deepcopy(catalog.public_file(file_ref))
            if preview.get("display_label") == "功能测试报告.xlsx":
                next(
                    row
                    for row in preview["rows"]
                    if row["values"] and row["values"][0] == "F01"
                )["values"][8] = "13"
            return preview

        def checked_input_bytes(self, file_ref: str):
            return catalog.checked_input_bytes(file_ref)

    execution = ScenarioEffectEngine().execute(_spec().instruction, InvalidCatalog())
    assert execution is not None
    assert execution.status == "failed"
    assert len(execution.artifacts) == 1
    artifact = execution.artifacts[0]
    assert artifact.file_name == "TC-11输入校验失败.md"
    assert artifact.verifier_status == "failed"
    assert artifact.business_gate_outcome is not None
    assert artifact.business_gate_outcome.status == "invalid"
    assert "不得用于上线判断" in (artifact.review_guidance or "")
    assert "所有确定性效果门通过" not in execution.result


def test_tc11_forced_verifier_failure_never_reports_reliable_generation(
    catalog: BenchmarkWorkspaceCatalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = ScenarioEffectEngine._check

    def forced_failure(check_id: str, label: str, passed: bool, detail: str):
        return original(
            check_id,
            label,
            False if check_id == "check-release-ledger-csv" else passed,
            detail,
        )

    monkeypatch.setattr(ScenarioEffectEngine, "_check", staticmethod(forced_failure))
    execution = ScenarioEffectEngine().execute(_spec().instruction, catalog)
    assert execution is not None
    assert execution.status == "failed"
    assert all(item.verifier_status == "failed" for item in execution.artifacts)
    assert "成果不得标为验证通过" in execution.result
    assert "所有确定性效果门通过" not in execution.result
