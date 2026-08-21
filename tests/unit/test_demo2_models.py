import pytest
from pydantic import ValidationError

from packages.contracts import (
    RouteProfile,
    RouteSelectionReceipt,
    RouteSelectionRequest,
    WorkerProcessing,
    WorkItemSnapshot,
)


def test_route_selection_request_is_strict_and_bounded() -> None:
    request = RouteSelectionRequest(
        mode="adaptive_swarm",
        expected_version=1,
        idempotency_key="demo2-route-001",
    )
    assert request.scope == "this_run"

    with pytest.raises(ValidationError):
        RouteSelectionRequest(
            mode="adaptive_swarm",
            expected_version=1,
            idempotency_key="demo2-route-001",
            worker_count=5,
        )

    with pytest.raises(ValidationError):
        RouteSelectionRequest(
            mode="unknown",
            expected_version=1,
            idempotency_key="demo2-route-001",
        )


def test_demo2_impact_fields_are_strict_but_old_snapshots_remain_compatible() -> None:
    profile = RouteProfile.model_validate(
        {
            "mode": "single_agent",
            "label": "Single Agent",
            "summary": "串行准备",
            "forecast": {
                "source_type": "fixture_policy_forecast",
                "estimated_tool_calls": 12,
                "estimated_runtime_seconds": 600,
                "max_workers": 1,
            },
            "tradeoff": "协调更少",
        }
    )
    assert profile.impact_preview is None

    item = WorkItemSnapshot.model_validate(
        {
            "work_item_id": "legacy-item",
            "owner_id": "user_1",
            "title": "旧工作项",
            "objective": "验证旧快照兼容",
            "business_status": "attention",
            "priority": 80,
            "facts": {
                "value_band": "high",
                "breadth": 2,
                "parallelism": 1,
                "deadline_pressure": "medium",
                "risk_band": "medium",
                "budget_band": "approved",
                "source_labels": ["演示来源"],
            },
            "allowed_modes": ["single_agent"],
            "route_profiles": [profile.model_dump(mode="json")],
            "recommendation": {
                "mode": "single_agent",
                "summary": "旧推荐",
                "reasons": [{"factor": "breadth", "label": "资料广度", "detail": "两类资料"}],
                "forecast": profile.forecast.model_dump(mode="json"),
                "policy_version": "legacy-v1",
            },
        }
    )
    assert item.selection_receipt is None
    assert item.selection_receipts == []

    payload = profile.model_dump(mode="json")
    payload["impact_preview"] = {
        "summary": "预演",
        "changes": [
            {"change_kind": "change", "aspect": "work_allocation", "label": "分配", "after": "串行"},
            {"change_kind": "change", "aspect": "coordination", "label": "协调", "after": "单上下文"},
            {"change_kind": "preserve", "aspect": "execution_boundary", "label": "执行", "after": "仍未启动"},
            {"change_kind": "no_external_action", "aspect": "external_action", "label": "外部动作", "after": "不会发生"},
        ],
        "unexpected": True,
    }
    with pytest.raises(ValidationError):
        RouteProfile.model_validate(payload)


def test_demo2_impact_boundaries_and_receipt_versions_are_enforced() -> None:
    profile_payload = {
        "mode": "single_agent",
        "label": "Single Agent",
        "summary": "串行准备",
        "forecast": {
            "source_type": "fixture_policy_forecast",
            "estimated_tool_calls": 12,
            "estimated_runtime_seconds": 600,
            "max_workers": 1,
        },
        "tradeoff": "协调更少",
        "impact_preview": {
            "summary": "边界缺失",
            "changes": [
                {"change_kind": "change", "aspect": "work_allocation", "label": "分配", "after": "串行"},
                {"change_kind": "change", "aspect": "coordination", "label": "协调", "after": "顺序处理"},
                {"change_kind": "change", "aspect": "human_control", "label": "确认", "after": "结果确认"},
                {"change_kind": "preserve", "aspect": "execution_boundary", "label": "执行", "after": "仍未启动"},
            ],
        },
    }
    with pytest.raises(ValidationError):
        RouteProfile.model_validate(profile_payload)

    with pytest.raises(ValidationError):
        RouteSelectionReceipt.model_validate(
            {
                "receipt_id": "invalid-receipt",
                "from_cockpit_version": 2,
                "to_cockpit_version": 2,
                "from_item_version": 2,
                "to_item_version": 3,
                "selected_mode": "single_agent",
                "selection_source": "user_override",
                "override_scope": "this_run",
                "forecast": profile_payload["forecast"],
                "changes": [
                    {"change_kind": "change", "aspect": "route_decision", "label": "方式", "after": "单 Agent"},
                    {"change_kind": "preserve", "aspect": "execution_boundary", "label": "执行", "after": "仍未启动"},
                    {"change_kind": "no_external_action", "aspect": "external_action", "label": "外部动作", "after": "不会发生"},
                    {"change_kind": "change", "aspect": "work_allocation", "label": "分配", "after": "串行"},
                ],
                "summary": "无效版本",
            }
        )


def test_demo2_worker_processing_cannot_overstate_model_use() -> None:
    deterministic = WorkerProcessing(
        path="deterministic",
        kind="deterministic",
        label="确定性处理",
        model_called=False,
        elapsed_ms=3,
        output_used="deterministic",
    )
    assert deterministic.model is None

    model = WorkerProcessing(
        path="language_model",
        kind="language_model",
        label="模型 Worker",
        model_called=True,
        model="deepseek-v4-pro",
        elapsed_ms=25,
        output_used="model",
    )
    assert model.model_called is True

    fallback = WorkerProcessing(
        path="language_model",
        kind="language_model",
        label="模型调用后回退",
        model_called=True,
        model="deepseek-v4-pro",
        elapsed_ms=40,
        output_used="template_fallback",
        fallback_reason="ValidationError",
    )
    assert fallback.output_used == "template_fallback"

    invalid_payloads = [
        {**deterministic.model_dump(), "model_called": True, "model": "deepseek-v4-pro"},
        {**model.model_dump(), "model_called": False},
        {**fallback.model_dump(), "fallback_reason": None},
    ]
    for payload in invalid_payloads:
        with pytest.raises(ValidationError):
            WorkerProcessing.model_validate(payload)
