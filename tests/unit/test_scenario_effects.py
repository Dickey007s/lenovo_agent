from __future__ import annotations

import csv
import io
import os
import zipfile
from pathlib import Path

import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.run_workspace_artifact_store import (
    RunWorkspaceArtifactError,
    RunWorkspaceArtifactStore,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
    scenario_effect_catalog_manifest,
)


FORTE_ROOT = Path(__file__).resolve().parents[2] / "demo-enterprise-data" / "forte"
IMPLEMENTED = {"TC-01", "TC-05", "TC-10", "TC-13", "TC-14", "TC-15"}
IMPLEMENTED |= {"TC-02", "TC-04", "TC-06", "TC-07", "TC-11", "TC-12"}
BLOCKED_EXTERNAL = {"TC-03", "TC-08", "TC-09"}


@pytest.fixture(scope="module")
def catalog() -> BenchmarkWorkspaceCatalog:
    return BenchmarkWorkspaceCatalog(FORTE_ROOT)


def _execute(scenario_id: str, catalog: BenchmarkWorkspaceCatalog):
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == scenario_id)
    execution = ScenarioEffectEngine().execute(spec.instruction, catalog)
    assert execution is not None
    return spec, execution


def test_machine_manifest_covers_all_fifteen_effect_contracts() -> None:
    manifest = scenario_effect_catalog_manifest()
    scenarios = manifest["scenarios"]

    assert manifest["schema_version"] == "scenario-effect-gate.v1"
    assert manifest["dataset"]["source_commit"] == (
        "345c1ec1487139db9dd319787fa9405ba85d1869"
    )
    assert [item["scenario_id"] for item in scenarios] == [
        f"TC-{index:02d}" for index in range(1, 16)
    ]
    for item in scenarios:
        assert item["instruction"]
        assert item["input_facts"]
        assert item["expected_artifacts"]
        assert item["deterministic_validator"]
        assert item["frontend_effect"]
        assert item["snapshot_event_receipt"]
        assert item["prohibited_side_effects"]
        assert item["expected_lifecycle"]


@pytest.mark.parametrize("scenario_id", sorted(IMPLEMENTED))
def test_all_twelve_local_scenarios_write_real_verified_artifacts(
    scenario_id: str, catalog: BenchmarkWorkspaceCatalog
) -> None:
    spec, execution = _execute(scenario_id, catalog)

    assert execution.status == "passed"
    assert [item.file_name for item in execution.artifacts] == list(
        spec.expected_artifacts
    )
    assert execution.source_file_refs
    assert execution.prohibited_side_effects == spec.prohibited_side_effects
    assert "0 次额外模型调用" in execution.cost
    assert all(item.content for item in execution.artifacts)
    assert all(item.verifier_status == "passed" for item in execution.artifacts)
    assert all(item.checks for item in execution.artifacts)
    assert all(
        check.passed
        for artifact in execution.artifacts
        for check in artifact.checks
    )


@pytest.mark.parametrize("scenario_id", ["TC-02", "TC-04", "TC-12"])
def test_code_scenarios_return_real_archives_and_command_receipts(
    scenario_id: str, catalog: BenchmarkWorkspaceCatalog
) -> None:
    _, execution = _execute(scenario_id, catalog)
    archive = next(item for item in execution.artifacts if item.file_name.endswith(".zip"))
    receipt = next(item for item in execution.artifacts if item.file_name.endswith(".md"))

    with zipfile.ZipFile(io.BytesIO(archive.content)) as package:
        names = package.namelist()
    assert names
    assert any("test" in name.lower() for name in names)
    rendered = receipt.content.decode("utf-8")
    assert "退出码 0" in rendered or "零失败" in rendered
    assert "FORTE 原始源码：未修改" in rendered


def test_candidate_legal_and_release_outputs_keep_human_gates_and_fixed_facts(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    _, candidates = _execute("TC-06", catalog)
    assert len(candidates.artifacts) == 2
    for artifact in candidates.artifacts:
        with zipfile.ZipFile(io.BytesIO(artifact.content)) as package:
            document = package.read("word/document.xml").decode("utf-8")
        assert "不作自动录用决定" in document
        assert all(name in document for name in ("周伦", "孙博文", "李雨桐", "王琳达", "赵晨曦"))
        assert "@" not in document

    _, legal = _execute("TC-07", catalog)
    with zipfile.ZipFile(io.BytesIO(legal.artifacts[0].content)) as package:
        legal_document = package.read("word/document.xml").decode("utf-8")
    assert legal_document.count("综合风险等级：高风险") == 2
    assert legal_document.count("综合风险等级：中风险") == 4
    assert "R05" not in legal_document

    _, release = _execute("TC-11", catalog)
    with zipfile.ZipFile(io.BytesIO(release.artifacts[0].content)) as package:
        release_document = package.read("word/document.xml").decode("utf-8")
    assert "上线结论：不满足上线条件，不得上线" in release_document
    for value in ("71.4%", "93.4%", "86.4%", "85.7%", "89.7%"):
        assert value in release_document


def test_onboarding_csv_applies_date_privacy_and_column_rules(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    _, execution = _execute("TC-01", catalog)
    artifact = execution.artifacts[0]
    rows = list(csv.reader(io.StringIO(artifact.content.decode("utf-8-sig"))))

    assert rows[0] == [
        "姓名",
        "入职日期",
        "岗位系列",
        "特殊备注",
        "电脑",
        "显示器",
        "其余物资",
        "软件权限空间",
        "独立工位",
    ]
    assert len(rows) == 10
    assert "紧急联系人" not in rows[0]
    assert rows[1][0] == "王子涵"
    assert rows[-1][1].startswith("4月20日")


def test_finance_outputs_match_known_fixed_input_totals(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    _, execution = _execute("TC-05", catalog)
    artifacts = {item.file_name: item for item in execution.artifacts}
    unpaid = list(
        csv.reader(
            io.StringIO(artifacts["未付统计.csv"].content.decode("utf-8-sig"))
        )
    )
    unreceived = list(
        csv.reader(
            io.StringIO(artifacts["未收统计.csv"].content.decode("utf-8-sig"))
        )
    )
    conclusion = artifacts["跨期核对说明.md"].content.decode("utf-8")

    assert len(unpaid) - 1 == 31
    assert len(unreceived) - 1 == 2
    assert "3,984,606.46" in conclusion
    assert "4,992,891.47" in conclusion
    assert "无僵尸账款" in conclusion


def test_outbound_flow_is_a_valid_docx_and_never_claims_execution(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    _, execution = _execute("TC-10", catalog)
    artifact = execution.artifacts[0]

    with zipfile.ZipFile(io.BytesIO(artifact.content)) as archive:
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}.issubset(
            archive.namelist()
        )
        document = archive.read("word/document.xml").decode("utf-8")
    assert "START" in document
    assert "六类终态" in document
    assert "不拨号、不写 CRM、不发送短信" in document
    assert len(artifact.checks) == 13


def test_customer_sre_and_ux_outputs_retain_deterministic_business_facts(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    _, customers = _execute("TC-13", catalog)
    customer_report = customers.artifacts[0].content.decode("utf-8")
    assert "8 条客户记录" in customers.artifacts[0].summary
    assert all(label in customer_report for label in ("安全型", "技术型", "敏捷型"))

    _, sre = _execute("TC-14", catalog)
    sre_report = sre.artifacts[0].content.decode("utf-8")
    assert "约 8 倍" in sre_report
    assert "仅建议，未执行" in sre_report

    _, ux = _execute("TC-15", catalog)
    ux_rows = list(
        csv.reader(io.StringIO(ux.artifacts[0].content.decode("utf-8-sig")))
    )
    assert len(ux_rows) - 1 == 66
    assert ux_rows[0] == [
        "页面名称",
        "交互元素",
        "痛点类型",
        "优先级",
        "痛点分析",
        "优化建议",
    ]
    assert ux_rows[1][3] == "P0"


@pytest.mark.parametrize("scenario_id", sorted(BLOCKED_EXTERNAL))
def test_external_scenarios_are_honestly_blocked(
    scenario_id: str, catalog: BenchmarkWorkspaceCatalog
) -> None:
    _, execution = _execute(scenario_id, catalog)

    assert execution.status == "blocked_external_boundary"
    assert execution.artifacts == ()
    assert execution.source_file_refs == ()
    assert "未获授权" in execution.observation
    assert "0 个外部动作" in execution.cost


def test_run_workspace_store_is_append_only_and_rechecks_integrity(tmp_path: Path) -> None:
    store = RunWorkspaceArtifactStore(tmp_path / "run-workspaces")
    identity = {
        "owner_id": "alice",
        "run_id": "run-effect-gate",
        "artifact_id": "workspace-artifact-0123456789ab",
        "file_name": "核对结果.csv",
    }
    first = store.write(**identity, content=b"a,b\n1,2\n")
    replay = store.write(**identity, content=b"a,b\n1,2\n")

    assert replay == first
    assert store.read(**identity, expected_sha256=first.sha256) == b"a,b\n1,2\n"
    with pytest.raises(RunWorkspaceArtifactError, match="不能被覆盖"):
        store.write(**identity, content=b"a,b\n9,9\n")
    with pytest.raises(RunWorkspaceArtifactError, match="文件名不合法"):
        store.write(
            owner_id="alice",
            run_id="run-effect-gate",
            artifact_id="workspace-artifact-0123456789ab",
            file_name="../escape.csv",
            content=b"no",
        )

    target = next((tmp_path / "run-workspaces").rglob("核对结果.csv"))
    target.write_bytes(b"tampered")
    with pytest.raises(RunWorkspaceArtifactError, match="完整性校验失败"):
        store.read(**identity, expected_sha256=first.sha256)


def test_fixed_local_validator_environment_does_not_inherit_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LLM_API_KEY", "must-not-reach-child")
    monkeypatch.setenv("DATABASE_DSN", "must-not-reach-child")
    monkeypatch.setenv("TEST_ACCESS_TOKEN", "must-not-reach-child")
    monkeypatch.setenv("PYTHONPATH", "must-not-reach-child")

    env = ScenarioEffectEngine._fixed_command_env()

    assert "LLM_API_KEY" not in env
    assert "DATABASE_DSN" not in env
    assert "TEST_ACCESS_TOKEN" not in env
    assert "PYTHONPATH" not in env
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["NO_PROXY"] == "*"
    assert env["HTTP_PROXY"] == ""
    assert env["HTTPS_PROXY"] == ""
    if "PATH" in os.environ:
        assert env["PATH"] == os.environ["PATH"]
