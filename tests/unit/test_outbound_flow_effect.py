from __future__ import annotations

import copy
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pytest

from services.api.app.application.benchmark_workspace_catalog import (
    BenchmarkWorkspaceCatalog,
)
from services.api.app.application.outbound_flow_effect import (
    EXPECTED_DISPLAY_PATH,
    EXPECTED_FILE_NAME,
    EXPECTED_FILE_REF,
    SOURCE_LOGICAL_ID,
    OutboundFlowValidationError,
    OutboundSourceInput,
    analyze_outbound_source,
    build_outbound_flow,
    verify_outbound_flow_artifact,
)
from services.api.app.application.scenario_effects import (
    SCENARIO_EFFECT_SPECS,
    ScenarioEffectEngine,
    ScenarioEffectError,
)


ROOT = Path(__file__).resolve().parents[2]
FORTE_ROOT = ROOT / "demo-enterprise-data" / "forte"
SOURCE_PATH = FORTE_ROOT / "Operations-008" / "input" / EXPECTED_FILE_NAME


def _source(content: bytes | None = None, **changes: object) -> OutboundSourceInput:
    payload = SOURCE_PATH.read_bytes() if content is None else content
    values: dict[str, object] = {
        "logical_id": SOURCE_LOGICAL_ID,
        "file_name": EXPECTED_FILE_NAME,
        "display_path": EXPECTED_DISPLAY_PATH,
        "file_ref": EXPECTED_FILE_REF,
        "content": payload,
        "declared_size": len(payload),
        "allowlist_verified": True,
    }
    values.update(changes)
    return OutboundSourceInput(**values)  # type: ignore[arg-type]


def _replace_text(old: str, new: str, content: bytes | None = None) -> bytes:
    text = (SOURCE_PATH.read_bytes() if content is None else content).decode("utf-8")
    assert text.count(old) == 1, old
    return text.replace(old, new).encode("utf-8")


def _tamper_docx(content: bytes, old: str, new: str) -> bytes:
    source = io.BytesIO(content)
    target = io.BytesIO()
    with zipfile.ZipFile(source) as input_zip, zipfile.ZipFile(
        target, "w", zipfile.ZIP_DEFLATED
    ) as output_zip:
        for name in input_zip.namelist():
            payload = input_zip.read(name)
            if name == "word/document.xml":
                text = payload.decode("utf-8")
                assert old in text
                payload = text.replace(old, new, 1).encode("utf-8")
            output_zip.writestr(name, payload)
    return target.getvalue()


def _parameters(outcome) -> dict[str, str]:
    return {item.name: item.value for item in outcome.parameters}


def test_baseline_is_derived_from_source_and_builds_a_traversable_graph() -> None:
    source = _source()
    build = build_outbound_flow(source)
    outcome = build.outcome

    assert outcome.status == "approval_required"
    assert outcome.source_rule_group_count == len({rule.group for rule in outcome.rules}) == 15
    assert outcome.atomic_requirement_count == len(outcome.rules) == 34
    assert outcome.covered_count == 34
    assert outcome.unsupported_count == outcome.conflict_count == 0
    assert outcome.node_count == len(outcome.nodes) == 31
    assert outcome.edge_count == len(outcome.edges) == 36
    assert outcome.guard_count == len(outcome.guards) == 7
    assert outcome.terminal_count == outcome.reachable_terminal_count == 7
    assert all(outcome.graph_integrity.model_dump().values())
    assert all(rule.source_file_ref == EXPECTED_FILE_REF for rule in outcome.rules)
    assert all(rule.locator.startswith("专业性说明.md:L") for rule in outcome.rules)
    assert all(rule.excerpt for rule in outcome.rules)
    assert all(check.passed for check in build.checks)

    edges = {(edge.from_node_id, edge.to_node_id): edge for edge in outcome.edges}
    assert ("out-node-decision-connection", "out-node-decision-identity") in edges
    assert ("out-node-decision-identity", "out-node-recording-notice") in edges
    assert ("out-node-recording-notice", "out-node-introduce-purpose") in edges
    assert ("out-node-introduce-purpose", "out-node-payment-guidance") in edges
    assert "未来" in edges[("out-node-record-ptp", "out-node-future-sms")].label
    assert edges[("out-node-record-ptp", "out-node-future-sms")].future_action is True


def test_committed_browser_fixture_matches_the_public_builder_manifest() -> None:
    manifest_path = (
        ROOT
        / "docs"
        / "evidence"
        / "manifests"
        / "tc10-public-outbound-flow-outcome-20260829.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    build = build_outbound_flow(_source())

    assert manifest["schema_version"] == "tc10-public-outbound-flow.v1"
    assert manifest["source"] == {
        "logical_id": SOURCE_LOGICAL_ID,
        "file_name": EXPECTED_FILE_NAME,
        "display_path": EXPECTED_DISPLAY_PATH,
        "file_ref": EXPECTED_FILE_REF,
    }
    assert manifest["outbound_flow_outcome"] == build.outcome.model_dump(mode="json")
    assert manifest["checks"][:-1] == [
        {
            "check_id": item.check_id,
            "label": item.label,
            "passed": item.passed,
            "detail": item.detail,
        }
        for item in build.checks
    ]
    assert manifest["checks"][-1]["check_id"] == "check-outbound-original-source-read-only-v2"
    dynamic_manifest = json.loads(
        (
            manifest_path.parent
            / "tc10-public-outbound-flow-outcome-dynamic-20260829.json"
        ).read_text(encoding="utf-8")
    )
    dynamic_content = _replace_text(
        "每日 22:00 至次日 08:00 严禁拨打",
        "每日 21:00 至次日 09:00 严禁拨打",
    )
    dynamic_content = _replace_text(
        "每日拨打不得超过 3 次，1小时内不得超过 1 次",
        "每日拨打不得超过 5 次，2小时内不得超过 2 次",
        dynamic_content,
    )
    dynamic = build_outbound_flow(_source(dynamic_content))
    assert dynamic_manifest["outbound_flow_outcome"] == dynamic.outcome.model_dump(mode="json")


@pytest.mark.parametrize(
    ("old", "new", "parameter_name", "expected"),
    [
        (
            "每日 22:00 至次日 08:00 严禁拨打",
            "每日 21:00 至次日 09:00 严禁拨打",
            "prohibited_start",
            "21:00",
        ),
        (
            "每日拨打不得超过 3 次，1小时内不得超过 1 次",
            "每日拨打不得超过 5 次，2小时内不得超过 2 次",
            "daily_call_max",
            "5",
        ),
        ("至少保存 2 年", "至少保存 3 年", "recording_retention", "3"),
        ("间隔至少 1 小时后重拨", "间隔至少 2 小时后重拨", "redial_min_interval", "2"),
    ],
)
def test_source_parameters_change_without_production_constants(
    old: str, new: str, parameter_name: str, expected: str
) -> None:
    baseline = analyze_outbound_source(_source())
    changed = analyze_outbound_source(_source(_replace_text(old, new)))

    assert _parameters(changed)[parameter_name] == expected
    assert [item.node_id for item in changed.nodes] == [item.node_id for item in baseline.nodes]
    assert [item.edge_id for item in changed.edges] == [item.edge_id for item in baseline.edges]
    assert changed.atomic_requirement_count == baseline.atomic_requirement_count
    assert changed.status == "approval_required"


def test_consistent_recording_first_source_changes_graph_order() -> None:
    content = _replace_text(
        "接通后必须先确认是否本人接听。",
        "接通后必须先告知录音再确认本人是否接听。",
    )
    content = _replace_text(
        "接通后第一步，询问是否本人。确认是本人才进入催收话术；",
        "接通后第一步，告知录音，再询问是否本人。确认是本人才进入催收话术；",
        content,
    )
    content = _replace_text(
        "确认本人后，先自我介绍、告知录音、说明来电目的，",
        "告知录音后再确认本人，先自我介绍、说明来电目的，",
        content,
    )
    outcome = analyze_outbound_source(_source(content))
    edges = {(edge.from_node_id, edge.to_node_id) for edge in outcome.edges}

    assert _parameters(outcome)["identity_recording_order"] == "recording_before_identity"
    assert ("out-node-decision-connection", "out-node-recording-notice") in edges
    assert ("out-node-recording-notice", "out-node-decision-identity") in edges
    assert outcome.graph_integrity.critical_order_valid is True


def test_inconsistent_identity_and_recording_order_fails_closed() -> None:
    content = _replace_text(
        "接通后必须先确认是否本人接听。",
        "接通后必须先告知录音再确认本人是否接听。",
    )
    with pytest.raises(OutboundFlowValidationError, match="相互冲突") as error:
        analyze_outbound_source(_source(content))
    assert error.value.code == "outbound_identity_order_conflict"


def test_recognized_human_transfer_rule_extends_ledger_guard_and_graph() -> None:
    marker = "**重拨调度**："
    extra = (
        "**高龄重病转人工触发条件**：客户明确表示高龄或重病时，AI 必须立即转人工。\n\n"
    )
    content = _replace_text(marker, extra + marker)
    baseline = analyze_outbound_source(_source())
    changed = analyze_outbound_source(_source(content))

    assert changed.atomic_requirement_count == baseline.atomic_requirement_count + 1
    assert changed.guard_count == baseline.guard_count + 1
    assert changed.edge_count == baseline.edge_count + 1
    extra_rule = next(rule for rule in changed.rules if "高龄或重病" in rule.excerpt)
    assert extra_rule.coverage_state == "covered"
    assert extra_rule.mapped_guard_ids
    assert extra_rule.mapped_edge_ids


def test_unknown_normative_requirement_cannot_be_silently_ignored() -> None:
    content = _replace_text(
        "**重拨调度**：",
        "**新名单规则**：机器人必须写入一个来源未定义的外部名单。\n\n**重拨调度**：",
    )
    with pytest.raises(OutboundFlowValidationError, match="不能静默忽略") as error:
        analyze_outbound_source(_source(content))
    assert error.value.code == "outbound_unsupported_rule"


def test_extra_terminal_is_visible_as_invalid_instead_of_green() -> None:
    content = _replace_text("加入禁呼名单、案件升级。", "加入禁呼名单、案件升级、待审新终态。")
    build = build_outbound_flow(_source(content))

    assert build.outcome.status == "invalid"
    assert build.outcome.unsupported_count == 1
    assert build.outcome.reachable_terminal_count < build.outcome.terminal_count
    assert not all(check.passed for check in build.checks)


@pytest.mark.parametrize(
    ("field", "value", "code"),
    [
        ("logical_id", "operations-008-wrong", "outbound_source_identity"),
        ("file_name", "错误.md", "outbound_source_identity"),
        ("display_path", "其他目录/专业性说明.md", "outbound_source_identity"),
        ("file_ref", "forte-unknown", "outbound_source_identity"),
        ("allowlist_verified", False, "outbound_source_allowlist"),
        ("declared_size", 1, "outbound_source_size"),
    ],
)
def test_source_identity_contract_fails_closed(field: str, value: object, code: str) -> None:
    with pytest.raises(OutboundFlowValidationError) as error:
        analyze_outbound_source(replace(_source(), **{field: value}))
    assert error.value.code == code


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "outbound_source_empty"),
        (b"\xff\xfe\x00", "outbound_source_binary"),
        ("## 二、监管合规约束\n".encode(), "outbound_source_truncated"),
    ],
)
def test_empty_binary_or_truncated_source_fails_closed(content: bytes, code: str) -> None:
    with pytest.raises(OutboundFlowValidationError) as error:
        analyze_outbound_source(_source(content))
    assert error.value.code == code


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        ("每日拨打不得超过 3 次", "每日拨打不得超过 0 次", "outbound_daily_frequency"),
        ("至少保存 2 年", "至少保存 0 年", "outbound_recording_retention"),
        ("每日 22:00 至次日 08:00", "每日 25:00 至次日 08:00", "outbound_time_invalid"),
        ("安排重拨、停止外呼", "安排重拨、安排重拨、停止外呼", "outbound_terminal_duplicate"),
    ],
)
def test_illegal_numbers_and_duplicate_terminal_fail_closed(
    old: str, new: str, code: str
) -> None:
    with pytest.raises(OutboundFlowValidationError) as error:
        analyze_outbound_source(_source(_replace_text(old, new)))
    assert error.value.code == code


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("out-edge-connected-identity", "out-edge-connected-wrong"),
        ("PTP登记", "错误终态"),
        ("专业性说明.md:L22", "专业性说明.md:L999"),
        ("identity_before_recording", "recording_before_identity"),
    ],
)
def test_independent_verifier_turns_tampered_docx_red(old: str, new: str) -> None:
    source = _source()
    build = build_outbound_flow(source)
    checks = verify_outbound_flow_artifact(source, _tamper_docx(build.report_docx, old, new))

    assert any(not check.passed for check in checks)


@pytest.mark.parametrize("content", [b"not-a-docx", b"PK\x03\x04"])
def test_damaged_docx_never_passes(content: bytes) -> None:
    checks = verify_outbound_flow_artifact(_source(), content)
    assert checks
    assert any(not check.passed for check in checks)


class _WorkspaceOverride:
    def __init__(self, base: BenchmarkWorkspaceCatalog, workspace: dict) -> None:
        self.base = base
        self.workspace = workspace

    def public_workspace(self) -> dict:
        return copy.deepcopy(self.workspace)

    def public_file(self, file_ref: str) -> dict:
        return self.base.public_file(file_ref)

    def checked_input_bytes(self, file_ref: str) -> bytes:
        return self.base.checked_input_bytes(file_ref)

    def checked_input_bytes_many(self, file_refs: tuple[str, ...]) -> dict[str, bytes]:
        return {file_ref: self.checked_input_bytes(file_ref) for file_ref in file_refs}


@pytest.mark.parametrize("mode", ["missing", "extra"])
def test_engine_freeze_requires_exact_operations_folder(mode: str) -> None:
    catalog = BenchmarkWorkspaceCatalog(FORTE_ROOT)
    workspace = catalog.public_workspace()
    folder = next(item for item in workspace["folders"] if item["display_label"] == "运营管理")
    if mode == "missing":
        folder["files"] = []
    else:
        folder["files"].append({**folder["files"][0], "display_label": "未知规则.md"})
    spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == "TC-10")

    with pytest.raises(ScenarioEffectError, match="恰好包含一份"):
        ScenarioEffectEngine().freeze(spec.instruction, _WorkspaceOverride(catalog, workspace))
