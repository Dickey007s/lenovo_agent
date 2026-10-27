from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from packages.contracts.harness_models import (
    AgentControlLoopEffectReceipt,
    AgentControlLoopWorkspaceArtifact,
)
from services.api.app.application.benchmark_workspace_catalog import BenchmarkWorkspaceCatalog
from services.api.app.application.harness_runtime import HarnessFinding, HarnessTaskResult
from services.api.app.application.model_input_coverage import model_input_coverage
from services.api.app.application.narrative_reconciliation import (
    build_verified_effect_context,
    reconcile_narrative,
)
from services.api.app.application.scenario_effects import SCENARIO_EFFECT_SPECS, ScenarioEffectEngine


@pytest.fixture(scope="module")
def office_contexts():
    catalog = BenchmarkWorkspaceCatalog(Path(__file__).resolve().parents[2] / "demo-enterprise-data/forte")
    contexts = {}
    for scenario_id in ("TC-01", "TC-05", "TC-11"):
        spec = next(item for item in SCENARIO_EFFECT_SPECS if item.scenario_id == scenario_id)
        execution = ScenarioEffectEngine().execute(spec.instruction, catalog)
        assert execution.status == "passed"
        now = datetime.now(timezone.utc)
        artifacts = [AgentControlLoopWorkspaceArtifact(
            artifact_id=f"workspace-artifact-{index:012x}", capability_id=spec.capability_id,
            scenario_id=scenario_id, title=item.title, file_name=item.file_name,
            media_type=item.media_type, size=len(item.content), round_number=1,
            source_file_refs=list(item.source_file_refs), validator_id=item.validator_id,
            verifier_status=item.verifier_status, checks=list(item.checks), summary=item.summary,
            record_count=item.record_count, covered_period=item.covered_period,
            finance_review_outcome=item.finance_review_outcome,
            business_gate_outcome=item.business_gate_outcome,
            download_path=f"/artifacts/{index}", created_at=now,
        ) for index, item in enumerate(execution.artifacts)]
        receipt = AgentControlLoopEffectReceipt(
            receipt_id="effect-receipt-000000000001", capability_id=spec.capability_id,
            scenario_id=scenario_id, status="passed", state=execution.state,
            action=execution.action, observation=execution.observation,
            cost=execution.cost, result=execution.result,
            source_file_refs=list(execution.source_file_refs),
            artifact_ids=[item.artifact_id for item in artifacts],
            finance_review_outcome=artifacts[0].finance_review_outcome,
            business_gate_outcome=artifacts[0].business_gate_outcome, created_at=now,
        )
        context = build_verified_effect_context(receipt, artifacts)
        assert context is not None
        contexts[scenario_id] = (context, receipt, artifacts)
    return contexts


def _reconcile(context, summary, detail="说明仍需人工复核。", finding_count=1):
    result = HarnessTaskResult(
        summary=summary, findings=[HarnessFinding(
            title=f"候选说明 {index}", detail=detail, file_refs=["forte-source"],
        ) for index in range(finding_count)], follow_ups=[], review_required=True,
    )
    return reconcile_narrative(
        run_id="harness:office-facts", round_number=1, result=result,
        context_used=context, current_context=context,
    )


@pytest.mark.parametrize(("scenario", "summary", "expected"), [
    ("TC-01", "日期范围内共识别出11名新员工。", "9"),
    ("TC-05", "2026年期末未付合计约4,064,000元。", "3984606.46"),
    ("TC-05", "未收合计约5,002,891元。", "4992891.47"),
    ("TC-05", "僵尸账款候选包括绵阳长城发展融资担保有限公司。", "0 条固定口径候选"),
    ("TC-11", "P0 功能提测率 100%，当前不满足上线条件。", "71.4"),
    ("TC-11", "上线配置清单共14项功能。", "13"),
])
def test_historical_false_claims_are_rejected(office_contexts, scenario, summary, expected):
    context, _, _ = office_contexts[scenario]
    receipt = _reconcile(context, summary)
    assert receipt.status == "contradictory"
    assert receipt.model_disposition == "rejected"
    assert receipt.authority == "deterministic_outcome"
    assert any(item.expected == expected for item in receipt.conflicts)


@pytest.mark.parametrize(("scenario", "summary"), [
    ("TC-01", "已匹配9名员工，规则解释仍待复核。"),
    ("TC-05", "未付31条，合计3984606.46元；未收合计4992891.47元。"),
    ("TC-11", "P0功能提测率为71.4%。PRD要求P0功能提测率必须达到100%。"),
    ("TC-11", "PRD 要求 P0 功能提测率 100%，但配置清单仅5个P0功能已提测，实际提测率为71.4%。"),
    ("TC-11", "P0功能提测率100%是准入门槛，当前P0功能提测率为71.4%。"),
])
def test_matching_numbers_do_not_certify_free_prose(office_contexts, scenario, summary):
    context, _, _ = office_contexts[scenario]
    receipt = _reconcile(context, summary)
    assert receipt.conflicts == []
    assert receipt.model_disposition == "supplemental"
    assert receipt.authority == "deterministic_outcome"


def test_metric_values_follow_changed_facts_not_sample_constants(office_contexts):
    context, _, _ = office_contexts["TC-01"]
    changed = {**context, "facts": {**context["facts"], "employee_count": 12}}
    receipt = _reconcile(changed, "已匹配9名员工。")
    assert receipt.conflicts[0].expected == "12"


def test_check_full_field_not_just_500_character_audit_excerpt(office_contexts):
    context, _, _ = office_contexts["TC-01"]
    receipt = _reconcile(context, "已完成准备。", "尚需复核。" * 110 + "共识别出11名新员工。")
    assert receipt.model_disposition == "rejected"
    assert len(receipt.conflicts[0].narrative_excerpt) <= 500


def test_many_conflicts_do_not_break_receipt_schema(office_contexts):
    context, _, _ = office_contexts["TC-01"]
    receipt = _reconcile(context, "已完成准备。", "共识别出11名新员工。", finding_count=96)
    assert receipt.model_disposition == "rejected"
    assert len(receipt.conflicts) == 20


def test_failed_effect_does_not_supply_authority(office_contexts):
    _, receipt, artifacts = office_contexts["TC-05"]
    assert build_verified_effect_context(receipt.model_copy(update={"status": "failed"}), artifacts) is None


def test_onboarding_requires_verified_artifact_bound_to_receipt(office_contexts):
    _, receipt, artifacts = office_contexts["TC-01"]
    assert artifacts[0].record_count == 9
    assert build_verified_effect_context(receipt, []) is None
    assert build_verified_effect_context(receipt, [artifacts[0].model_copy(update={"verifier_status": "failed"})]) is None
    assert build_verified_effect_context(receipt.model_copy(update={"artifact_ids": []}), artifacts) is None


def test_payload_coverage_distinguishes_text_tables_and_metadata():
    files = [
        {"file_ref": "log", "text": "a" * 12000, "truncated": True},
        {"file_ref": "table", "rows": [{"x": 1}] * 60, "total_rows": 212},
        {"file_ref": "full", "rows": [], "text": "entire supplied text", "truncated": False},
        {"file_ref": "unknown"},
    ]
    coverage = model_input_coverage(files)
    assert coverage[0].bounded and coverage[0].total_count is None
    assert coverage[1].bounded and coverage[1].total_count == 212
    assert not coverage[2].bounded and coverage[2].provided_count == 20
    assert coverage[3].bounded and coverage[3].unit == "metadata"
