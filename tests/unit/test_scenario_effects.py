from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
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


def test_tc02_refactors_the_complete_real_project_and_survives_independent_unpack(
    catalog: BenchmarkWorkspaceCatalog, tmp_path: Path
) -> None:
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-02")
    workspace = catalog.public_workspace()
    index = {
        (folder["display_label"], item["display_label"]): item["file_ref"]
        for folder in workspace["folders"]
        for item in folder["files"]
    }
    source_bytes = {
        label: catalog.checked_input_bytes(index[(group, label)])
        for group, label in spec.source_labels
    }
    source_digest_before = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in source_bytes.items()
    }

    execution = ScenarioEffectEngine().execute(spec.instruction, catalog)
    assert execution is not None and execution.status == "passed"
    projected_checks = [
        check for artifact in execution.artifacts for check in artifact.checks
    ]
    assert len(projected_checks) == 24
    assert len({check.check_id for check in projected_checks}) == 12
    assert execution.observation == (
        "生成 2 份真实成果文件，共享 12 项确定性检查，12/12 通过。"
    )
    assert "24 项" not in execution.observation
    archive = next(item for item in execution.artifacts if item.media_type == "application/zip")
    assert archive.validator_id == "validator-code-project-copy-v2"
    assert archive.self_test is not None

    with zipfile.ZipFile(io.BytesIO(archive.content)) as package:
        names = set(package.namelist())
        required = {
            f"search_agent_workflow/{name}" for name in source_bytes
        }
        required |= {
            "search_agent_workflow/react_agent.py",
            "search_agent_workflow/tests/test_react_agent.py",
            "search_agent_workflow/CHANGESET.patch",
            "search_agent_workflow/changes.json",
            "search_agent_workflow/改动说明.md",
            "search_agent_workflow/TC-02自测卡.md",
            "search_agent_workflow/TEST_RECEIPT.txt",
            "search_agent_workflow/test_receipt.json",
        }
        assert required <= names
        for name in ("workflow.py", "llm.py", "tools.py", "requirements.txt", "search_agent.log"):
            assert package.read(f"search_agent_workflow/{name}") == source_bytes[name]
        main_text = package.read("search_agent_workflow/main.py").decode("utf-8")
        react_text = package.read("search_agent_workflow/react_agent.py").decode("utf-8")
        changes = json.loads(package.read("search_agent_workflow/changes.json"))
        receipt = json.loads(package.read("search_agent_workflow/test_receipt.json"))
        package.extractall(tmp_path)

    assert "ReActSearchAgent" in main_text and "SearchWorkflow" not in main_text
    assert "range(1, self.config.max_iterations + 1)" in react_text
    assert changes["source_project"] == "algorithm-013/input/search_agent_workflow"
    assert changes["source_tree_modified"] is False
    assert receipt["status"] == "passed"
    assert receipt["tests"]["manifest_consistent"] is True
    assert set(receipt["tests"]["declared_ids"]) == set(receipt["tests"]["executed_ids"])

    isolated_env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TEMP": os.environ.get("TEMP", str(tmp_path)),
        "TMP": os.environ.get("TMP", str(tmp_path)),
        "PYTHONNOUSERSITE": "1",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "NO_PROXY": "*",
    }
    compiled = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "search_agent_workflow"],
        cwd=tmp_path,
        env=isolated_env,
        capture_output=True,
        text=True,
        check=False,
    )
    tested = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "search_agent_workflow/tests", "-v"],
        cwd=tmp_path,
        env=isolated_env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert compiled.returncode == 0, compiled.stderr
    assert tested.returncode == 0, tested.stdout + tested.stderr
    assert f"Ran {len(receipt['tests']['declared_ids'])} tests" in tested.stderr
    assert source_digest_before == {
        name: hashlib.sha256(catalog.checked_input_bytes(index[(group, name)])).hexdigest()
        for group, name in spec.source_labels
    }


def test_tc02_command_failure_marks_the_package_failed_and_gives_recovery(
    catalog: BenchmarkWorkspaceCatalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0

    def fail_tests(command: list[str], *, cwd: Path, timeout_seconds: int = 30):
        nonlocal calls
        calls += 1
        if calls == 1:
            return 0, "", 5
        return 1, "Ran 20 tests\nFAILED (failures=1)", 7

    monkeypatch.setattr(
        ScenarioEffectEngine, "_run_fixed_command", staticmethod(fail_tests)
    )
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-02")
    execution = ScenarioEffectEngine().execute(spec.instruction, catalog)

    assert execution is not None and execution.status == "failed"
    assert all(item.verifier_status == "failed" for item in execution.artifacts)
    assert "不要合并这个代码包" in execution.artifacts[0].review_guidance
    assert "重新启动一项 TC-02 任务" in execution.artifacts[0].review_guidance
    assert execution.artifacts[0].self_test is not None


def test_tc04_repairs_and_tests_the_complete_real_platform_copy(
    catalog: BenchmarkWorkspaceCatalog, tmp_path: Path
) -> None:
    source_root = FORTE_ROOT / "dev-015" / "input" / "source-code"
    source_files = {
        path.relative_to(source_root).as_posix(): path.read_bytes()
        for path in source_root.rglob("*")
        if path.is_file()
    }
    source_digest_before = {
        name: hashlib.sha256(content).hexdigest()
        for name, content in source_files.items()
    }
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-04")

    execution = ScenarioEffectEngine().execute(spec.instruction, catalog)

    assert execution is not None and execution.status == "passed"
    assert len(source_files) == 44
    assert len(execution.source_file_refs) == 44
    assert all(len(artifact.source_file_refs) == 44 for artifact in execution.artifacts)
    assert execution.observation == (
        "生成 2 份真实成果文件，共享 12 项确定性检查，12/12 通过。"
    )
    archive = next(item for item in execution.artifacts if item.media_type == "application/zip")
    report = next(item for item in execution.artifacts if item.media_type == "text/markdown")
    assert archive.self_test is not None
    assert archive.self_test.test_manifest_file == "evaluation-platform/test-manifest.json"
    assert archive.self_test.test_manifest_matches_collected is True
    assert [suite.test_count for suite in archive.self_test.test_suites] == [15, 16, 15, 23, 48]
    assert [suite.test_files for suite in archive.self_test.test_suites] == [
        ["tests/test_model_service.py", "tests/test_model_service_matrix.py"],
        ["tests/test_dataset_service.py", "tests/test_dataset_service_matrix.py"],
        ["tests/test_experiment_service.py", "tests/test_experiment_service_matrix.py"],
        ["tests/test_evaluation_engine.py", "tests/test_evaluation_engine_matrix.py"],
        ["tests/test_utils.py", "tests/test_utils_boundaries.py"],
    ]
    public_manifest = json.loads(
        (
            Path(__file__).resolve().parents[2]
            / "docs/evidence/manifests/tc04-public-test-manifest-20260828.json"
        ).read_text(encoding="utf-8")
    )
    assert public_manifest["test_count"] == 117
    assert public_manifest["categories"] == [
        suite.model_dump() for suite in archive.self_test.test_suites
    ]
    check_by_id = {check.check_id: check for check in archive.checks}
    assert check_by_id["check-eval-baseline-red"].passed
    assert check_by_id["check-eval-test-manifest"].passed
    assert check_by_id["check-eval-changed-source-coverage"].passed
    assert "117 项测试全部通过" in report.content.decode("utf-8")

    with zipfile.ZipFile(io.BytesIO(archive.content)) as package:
        names = set(package.namelist())
        expected_project_files = {
            f"evaluation-platform/{name}" for name in source_files
        }
        assert expected_project_files <= names
        assert "evaluation-platform/contracts.py" not in names
        for required in (
            "evaluation-platform/changes.patch",
            "evaluation-platform/changes.json",
            "evaluation-platform/test-manifest.json",
            "evaluation-platform/test-results.json",
            "evaluation-platform/baseline-test-results.json",
            "evaluation-platform/requirements-test.txt",
            "evaluation-platform/TC-04自测卡.md",
            "evaluation-platform/test-report.md",
        ):
            assert required in names
        manifest = json.loads(package.read("evaluation-platform/test-manifest.json"))
        result = json.loads(package.read("evaluation-platform/test-results.json"))
        baseline = json.loads(package.read("evaluation-platform/baseline-test-results.json"))
        changes = json.loads(package.read("evaluation-platform/changes.json"))
        patch_text = package.read("evaluation-platform/changes.patch").decode("utf-8")
        package.extractall(tmp_path)

    assert manifest["declared_test_ids"] == result["collected_test_ids"]
    assert sorted(
        test_id
        for suite in archive.self_test.test_suites
        for test_id in suite.test_ids
    ) == manifest["declared_test_ids"]
    assert len(manifest["declared_test_ids"]) == 117
    assert [item["test_count"] for item in manifest["categories"]] == [15, 16, 15, 23, 48]
    assert result["status"] == "passed"
    assert (result["passed"], result["failed"], result["errors"]) == (117, 0, 0)
    assert baseline["status"] == "failed"
    assert baseline["failed"] + baseline["errors"] == 5
    assert set(changes["modified_files"]) == {
        "app/services/model_service.py",
        "app/services/dataset_service.py",
        "app/engine/evaluation_engine.py",
    }
    assert all(
        percent >= 80.0
        for percent in changes["changed_source_coverage_percent"].values()
    )
    for changed_file in changes["modified_files"]:
        assert f"a/{changed_file}" in patch_text
        assert f"b/{changed_file}" in patch_text

    isolated_env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "TEMP": os.environ.get("TEMP", str(tmp_path)),
        "TMP": os.environ.get("TMP", str(tmp_path)),
        "PYTHONNOUSERSITE": "1",
        "HTTP_PROXY": "",
        "HTTPS_PROXY": "",
        "NO_PROXY": "*",
    }
    extracted = tmp_path / "evaluation-platform"
    compiled = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "app", "tests", "run_self_test.py"],
        cwd=extracted,
        env=isolated_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    tested = subprocess.run(
        [sys.executable, "run_self_test.py"],
        cwd=extracted,
        env=isolated_env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    rerun = json.loads((extracted / "test-results.json").read_text(encoding="utf-8"))
    assert compiled.returncode == 0, compiled.stderr
    assert tested.returncode == 0, tested.stdout + tested.stderr
    assert (rerun["collected"], rerun["passed"], rerun["errors"]) == (117, 117, 0)
    assert source_digest_before == {
        name: hashlib.sha256((source_root / name).read_bytes()).hexdigest()
        for name in source_files
    }


def test_tc04_freezes_all_project_and_context_bytes_before_worker_execution(
    catalog: BenchmarkWorkspaceCatalog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-04")
    monkeypatch.setattr(
        catalog,
        "checked_input_bytes",
        lambda _file_ref: (_ for _ in ()).throw(
            AssertionError("TC-04 must use one checked batch read")
        ),
    )
    frozen = ScenarioEffectEngine().freeze(spec.instruction, catalog)

    assert frozen is not None
    assert frozen.spec.scenario_id == "TC-04"
    assert len(frozen.source_file_refs) == 46
    assert len(frozen.catalog.input_bytes) == 46
    assert not frozen.catalog.previews
    first_workspace = frozen.catalog.public_workspace()
    first_workspace["title"] = "mutated test copy"
    assert frozen.catalog.public_workspace()["title"] == "FORTE 公开办公资料库"
    assert all(frozen.catalog.checked_input_bytes(file_ref) for file_ref in frozen.source_file_refs)


def test_tc04_command_failure_keeps_both_artifacts_red_and_blocks_merge(
    catalog: BenchmarkWorkspaceCatalog, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_commands(command: list[str], *, cwd: Path, timeout_seconds: int = 30):
        if "compileall" in command:
            return 0, "", 4
        return 1, "real project tests failed before producing a trusted result", 8

    monkeypatch.setattr(
        ScenarioEffectEngine, "_run_fixed_command", staticmethod(fail_commands)
    )
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-04")
    execution = ScenarioEffectEngine().execute(spec.instruction, catalog)

    assert execution is not None and execution.status == "failed"
    assert all(artifact.verifier_status == "failed" for artifact in execution.artifacts)
    assert all("当前包不得合并" in artifact.review_guidance for artifact in execution.artifacts)
    assert "所有确定性效果门通过" not in execution.result


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
    workspace = catalog.public_workspace()
    finance_refs = {
        item["display_label"]: item["file_ref"]
        for folder in workspace["folders"]
        if folder["display_label"] == "财务管理"
        for item in folder["files"]
    }
    current_ref = finance_refs["2026往来明细.xlsx"]
    period_refs = tuple(
        finance_refs[label]
        for label in (
            "2025往来明细-上半年.xlsx",
            "2025往来明细-下半年.xlsx",
            "2026往来明细.xlsx",
        )
    )

    assert len(unpaid) - 1 == 31
    assert len(unreceived) - 1 == 2
    assert "3,984,606.46" in conclusion
    assert "4,992,891.47" in conclusion
    assert "无僵尸账款" in conclusion

    unpaid_artifact = artifacts["未付统计.csv"]
    assert unpaid_artifact.title == "2026 期末未付明细"
    assert unpaid_artifact.covered_period == "2026 年期末"
    assert unpaid_artifact.record_count == 31
    assert unpaid_artifact.source_file_refs == (current_ref,)
    assert {check.check_id for check in unpaid_artifact.checks} == {
        "check-finance-current-source",
        "check-finance-unpaid-rows",
        "check-finance-unpaid-sort",
    }
    assert "不是三期合并表" in (unpaid_artifact.purpose or "")

    unreceived_artifact = artifacts["未收统计.csv"]
    assert unreceived_artifact.title == "2026 期末未收明细"
    assert unreceived_artifact.covered_period == "2026 年期末"
    assert unreceived_artifact.record_count == 2
    assert unreceived_artifact.source_file_refs == (current_ref,)
    assert {check.check_id for check in unreceived_artifact.checks} == {
        "check-finance-current-source",
        "check-finance-unreceived-rows",
        "check-finance-unreceived-sort",
    }
    assert "记录数" in (unreceived_artifact.purpose or "")

    cross_period_artifact = artifacts["跨期核对说明.md"]
    assert cross_period_artifact.title == "三期僵尸账款核对说明"
    assert cross_period_artifact.covered_period == (
        "2025 年上半年、2025 年下半年、2026 年"
    )
    assert cross_period_artifact.record_count is None
    assert cross_period_artifact.source_file_refs == period_refs
    assert {check.check_id for check in cross_period_artifact.checks} == {
        "check-finance-source",
        "check-finance-zombie",
    }
    assert "三期正数借方期末余额" in (cross_period_artifact.statistic_basis or "")


def test_outbound_flow_is_a_valid_docx_and_never_claims_execution(
    catalog: BenchmarkWorkspaceCatalog,
) -> None:
    spec, execution = _execute("TC-10", catalog)
    artifact = execution.artifacts[0]

    with zipfile.ZipFile(io.BytesIO(artifact.content)) as archive:
        assert {"[Content_Types].xml", "_rels/.rels", "word/document.xml"}.issubset(
            archive.namelist()
        )
        document = archive.read("word/document.xml").decode("utf-8")
    expected_terminals = (
        "PTP登记",
        "转人工跟进",
        "安排重拨",
        "停止外呼（达上限）",
        "加入禁呼名单",
        "案件升级",
    )
    assert document.count("START") == 1
    assert all(token in document for token in expected_terminals)
    assert "这份文档负责回答" in document
    assert "采用依据：《专业性说明.md》" in document
    assert "流程节点描述，不是执行回执" in document
    assert "没有拨号、没有写 CRM、没有发送短信" in document
    assert len(artifact.checks) == 13
    assert all(check.passed for check in artifact.checks)
    assert {check.check_id for check in artifact.checks} == {
        "check-outbound-source",
        "check-outbound-start",
        "check-outbound-time-gate",
        "check-outbound-connect",
        "check-outbound-retry",
        "check-outbound-recording",
        "check-outbound-identity",
        "check-outbound-third-party",
        "check-outbound-attitude",
        "check-outbound-invalid",
        "check-outbound-human",
        "check-outbound-terminals",
        "check-outbound-no-action",
    }
    assert artifact.source_file_refs == execution.source_file_refs
    assert spec.source_labels == (("运营管理", "专业性说明.md"),)
    assert artifact.covered_period == "信用卡 M1 逾期阶段"
    assert artifact.deliverable_type == "流程设计 DOCX"
    assert artifact.key_outputs == expected_terminals
    assert "专业性说明.md" in (artifact.statistic_basis or "")
    assert "不是拨号" in (artifact.purpose or "")
    assert "业务与合规负责人" in (artifact.review_guidance or "")
    assert "流程节点描述，不是执行回执" in (artifact.execution_summary or "")
    assert execution.prohibited_side_effects == ("不拨号", "不写 CRM", "不发送短信")


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
