from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from packages.contracts.harness_models import (
    AgentControlLoopEffectReceipt,
    AgentControlLoopUXPrioritizationOutcome,
)
from services.api.app.application.harness_runtime import (
    HarnessFinding,
    HarnessTaskResult,
)
from services.api.app.application.narrative_reconciliation import (
    build_verified_effect_context,
    reconcile_narrative,
)


ROOT = Path(__file__).resolve().parents[2]
OUTCOME_MANIFEST = (
    ROOT
    / "docs"
    / "evidence"
    / "manifests"
    / "tc15-public-ux-prioritization-outcome-20260829.json"
)
BASELINE_MANIFEST = (
    ROOT
    / "docs"
    / "evidence"
    / "manifests"
    / "tc15-narrative-false-green-baseline-20260829.json"
)


def _context() -> dict:
    manifest = json.loads(OUTCOME_MANIFEST.read_text(encoding="utf-8"))
    outcome = AgentControlLoopUXPrioritizationOutcome.model_validate(
        manifest["ux_prioritization_outcome"]
    )
    receipt = AgentControlLoopEffectReceipt(
        receipt_id="effect-receipt-123456789abc",
        capability_id="office-ux-pain-prioritization",
        scenario_id="TC-15",
        status="passed",
        state="三份批准来源已经冻结并完成全量解析。",
        action="生成逐组排序与逐行台账。",
        observation="两份成果通过独立验证。",
        cost="本地确定性计算，未增加模型调用。",
        result="完整日志排序成果已生成。",
        source_file_refs=[item["file_ref"] for item in manifest["sources"]],
        artifact_ids=["workspace-artifact-123456789abc"],
        prohibited_side_effects=["不修改原始输入"],
        ux_prioritization_outcome=outcome,
        created_at=datetime(2026, 8, 29, tzinfo=timezone.utc),
    )
    context = build_verified_effect_context(receipt)
    assert context is not None
    return context


def _result(summary: str, detail: str, *, follow_ups: list[str] | None = None) -> HarnessTaskResult:
    return HarnessTaskResult(
        summary=summary,
        findings=[
            HarnessFinding(
                title="公开日志离线排序说明",
                detail=detail,
                file_refs=["forte-3913d2ccb62b9b02"],
            )
        ],
        follow_ups=follow_ups or [],
        review_required=True,
    )


def test_historical_60_of_212_and_p0_to_p1_false_green_is_rejected() -> None:
    baseline = json.loads(BASELINE_MANIFEST.read_text(encoding="utf-8"))
    result = HarnessTaskResult.model_validate(baseline["model_result"])
    context = _context()

    reconciliation = reconcile_narrative(
        run_id=baseline["source_run_id"],
        round_number=1,
        result=result,
        context_used=context,
        current_context=context,
    )

    assert reconciliation.status == "contradictory"
    assert reconciliation.authority == "deterministic_outcome"
    assert reconciliation.model_disposition == "rejected"
    kinds = {item.kind for item in reconciliation.conflicts}
    assert set(baseline["expected_reconciliation"]["required_conflict_kinds"]) <= kinds
    assert any(item.observed == "模型把当前分析限定为 60 行" for item in reconciliation.conflicts)
    assert any(item.expected == "P0" and item.observed == "P1" for item in reconciliation.conflicts)


def test_accurate_full_outcome_claims_are_consistent_and_adoptable() -> None:
    context = _context()
    result = _result(
        "服务端已全量复算212/212行，形成87个问题组合；P0=25、P1=40、P2=14、P3=6、P4=2。",
        "排序仍需 UX 负责人复核，具体优化方案尚无批准来源。",
    )

    reconciliation = reconcile_narrative(
        run_id="harness:consistent",
        round_number=1,
        result=result,
        context_used=context,
        current_context=context,
    )

    assert reconciliation.status == "consistent"
    assert reconciliation.model_disposition == "adopted"
    assert reconciliation.comparable_claim_count >= 7
    assert reconciliation.conflicts == []


def test_non_comparable_narrative_is_supplemental_not_current_conclusion() -> None:
    context = _context()
    result = _result(
        "已读取公开交互日志并形成补充说明。",
        "具体排序和方案仍以服务端成果及 UX 负责人复核为准。",
    )

    reconciliation = reconcile_narrative(
        run_id="harness:partial",
        round_number=1,
        result=result,
        context_used=context,
        current_context=context,
    )

    assert reconciliation.status == "partial"
    assert reconciliation.model_disposition == "supplemental"
    assert reconciliation.comparable_claim_count == 0


def test_unapproved_concrete_solution_and_repeated_completed_work_are_rejected() -> None:
    context = _context()
    result = _result(
        "服务端已全量复算212/212行并形成87个问题组合。",
        "建议新增未保存内容二次确认弹窗并立即发布。",
        follow_ups=["重新统计全部212行并据此排序。"],
    )

    reconciliation = reconcile_narrative(
        run_id="harness:unsupported-solution",
        round_number=1,
        result=result,
        context_used=context,
        current_context=context,
    )

    assert reconciliation.status == "contradictory"
    kinds = {item.kind for item in reconciliation.conflicts}
    assert "unsupported_solution_claim" in kinds
    assert "redundant_completed_work" in kinds


def test_changed_outcome_revision_rejects_stale_narrative() -> None:
    context = _context()
    current = {**context, "outcome_revision": "outcome-rev-1111111111111111"}
    reconciliation = reconcile_narrative(
        run_id="harness:stale",
        round_number=1,
        result=_result("已形成说明。", "仍需人工复核。"),
        context_used=context,
        current_context=current,
    )

    assert reconciliation.status == "stale"
    assert reconciliation.model_disposition == "rejected"
    assert reconciliation.conflicts[0].kind == "outcome_revision_mismatch"


def test_model_only_task_remains_review_required_without_false_verification() -> None:
    reconciliation = reconcile_narrative(
        run_id="harness:model-only",
        round_number=1,
        result=_result("只读研究说明。", "没有结构化确定性 outcome。"),
        context_used=None,
        current_context=None,
    )

    assert reconciliation.status == "not_applicable"
    assert reconciliation.authority == "model_only"
    assert reconciliation.model_disposition == "adopted"
    assert "仍需人工复核" in reconciliation.message
