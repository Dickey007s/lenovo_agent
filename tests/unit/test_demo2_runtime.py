from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.routing import APIRoute

from services.api.app.application.harness_runtime import HarnessPlan, HarnessPlanUnit
from services.api.app.application.readonly_workers import (
    ReadonlyWorkerContribution,
    ReadonlyWorkerRequest,
    execute_readonly_workers,
    merge_adopted_contributions,
)
from services.api.app.application.topology_admission import admit_topology
from packages.contracts.harness_models import AgentControlLoopNarrativeReconciliation
from services.api.app.main import create_app


def _plan(*, risky: bool = False) -> HarnessPlan:
    return HarnessPlan(
        summary="两个独立的只读核对工作包",
        selection_reason="来自服务端已校验的计划。",
        units=[
            HarnessPlanUnit(
                unit_id="u1",
                title="核对一",
                objective="核对第一份资料",
                input_file_refs=["forte-1111111111111111"],
                tool="file.read",
                side_effect="run_workspace_write" if risky else "none",
            ),
            HarnessPlanUnit(
                unit_id="u2",
                title="核对二",
                objective="核对第二份资料",
                input_file_refs=["forte-2222222222222222"],
                tool="file.read",
            ),
        ],
    )


def test_admission_uses_validated_facts_and_never_admits_risky_workers() -> None:
    admitted = admit_topology(_plan(), remaining_model_calls=8, remaining_time_seconds=120)
    assert admitted.mode == "adaptive_readonly_workers"
    assert admitted.independent_branch_count == 2
    assert admitted.external_action == "none"
    assert admitted.user_confirmation_required is True

    fixed = admit_topology(_plan(risky=True), remaining_model_calls=8, remaining_time_seconds=120)
    assert fixed.mode == "fixed_workflow"
    assert fixed.user_confirmation_required is False
    assert any("人工门" in reason or "副作用" in reason for reason in fixed.reasons)

    low_budget = admit_topology(_plan(), remaining_model_calls=1, remaining_time_seconds=120)
    assert low_budget.mode == "fixed_workflow"

    oversized = HarnessPlan(
        summary="四个只读工作包",
        selection_reason="服务端验证",
        units=[
            HarnessPlanUnit(
                unit_id=f"u{index}",
                title=f"工作包 {index}",
                objective="独立核对资料",
                input_file_refs=[f"forte-{index:016x}"],
                tool="file.read",
            )
            for index in range(4)
        ],
    )
    assert admit_topology(oversized, remaining_model_calls=20, remaining_time_seconds=120).mode == "fixed_workflow"


def test_single_controller_is_selected_when_only_one_independent_branch_exists() -> None:
    plan = _plan()
    plan.units[1].depends_on = ["u1"]
    admitted = admit_topology(plan, remaining_model_calls=8, remaining_time_seconds=120)
    assert admitted.mode == "single_controller"
    assert admitted.independent_branch_count == 1


def test_demo2_uses_unified_harness_routes_not_a_demo_selector() -> None:
    paths: set[str] = set()
    for included in create_app().routes:
        router = getattr(included, "original_router", included)
        routes = getattr(router, "routes", [router])
        paths.update(route.path for route in routes if isinstance(route, APIRoute))
    assert "/v1/harness/runs/{run_id}/workers" in paths
    assert "/v1/harness/runs/{run_id}/continue" in paths
    assert not any(path.startswith("/v1/demo2") for path in paths)


@pytest.mark.asyncio
async def test_workers_are_branch_isolated_and_partial_merge_is_preserved() -> None:
    requests = [
        ReadonlyWorkerRequest(
            worker_run_id="worker-1",
            branch_id="branch-1",
            goal="核对第一份资料",
            source_file_refs=("forte-1111111111111111",),
            expected_version=2,
        ),
        ReadonlyWorkerRequest(
            worker_run_id="worker-2",
            branch_id="branch-2",
            goal="核对第二份资料",
            source_file_refs=("forte-2222222222222222",),
            expected_version=2,
        ),
    ]
    seen: list[tuple[str, tuple[str, ...]]] = []

    async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        seen.append((request.branch_id, request.source_file_refs))
        if request.branch_id == "branch-2":
            raise RuntimeError("source location unavailable")
        return ReadonlyWorkerContribution(
            worker_run_id=request.worker_run_id,
            branch_id=request.branch_id,
            outcome="adopted",
            summary="已形成可核对贡献",
            source_file_refs=request.source_file_refs,
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
            elapsed_ms=5,
        )

    results = await execute_readonly_workers(requests, handler)
    assert seen == [("branch-1", ("forte-1111111111111111",)), ("branch-2", ("forte-2222222222222222",))]
    merged = merge_adopted_contributions(results)
    assert merged.adopted_worker_run_ids == ("worker-1",)
    assert merged.failed_worker_run_ids == ("worker-2",)
    assert merged.waiting_branch_ids == ("branch-2",)


@pytest.mark.asyncio
async def test_worker_limit_is_hard_and_exception_does_not_fail_group() -> None:
    requests = [
        ReadonlyWorkerRequest(
            worker_run_id=f"worker-{index}",
            branch_id=f"branch-{index}",
            goal="独立核对",
            source_file_refs=(f"forte-{index:016x}",),
            expected_version=1,
        )
        for index in range(4)
    ]

    async def handler(request: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        await asyncio.sleep(0)
        return ReadonlyWorkerContribution(
            worker_run_id=request.worker_run_id,
            branch_id=request.branch_id,
            outcome="adopted",
            summary="通过",
            source_file_refs=request.source_file_refs,
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
        )

    with pytest.raises(ValueError, match="hard cap"):
        await execute_readonly_workers(requests, handler, max_workers=3)


@pytest.mark.asyncio
async def test_worker_source_scope_violation_is_rejected_and_branch_waits() -> None:
    request = ReadonlyWorkerRequest(
        worker_run_id="worker-scope",
        branch_id="branch-scope",
        goal="核对资料",
        source_file_refs=("forte-1111111111111111",),
        expected_version=1,
    )

    async def handler(_: ReadonlyWorkerRequest) -> ReadonlyWorkerContribution:
        return ReadonlyWorkerContribution(
            worker_run_id="worker-scope",
            branch_id="branch-scope",
            outcome="adopted",
            summary="越权候选",
            source_file_refs=("forte-9999999999999999",),
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
        )

    result = (await execute_readonly_workers([request], handler))[0]
    assert result.outcome == "rejected"
    assert result.output_used is False
    merged = merge_adopted_contributions([result])
    assert merged.adopted_worker_run_ids == ()
    assert merged.waiting_branch_ids == ("branch-scope",)


def test_worker_merge_is_a_normal_artifact_and_keeps_reconciliation_receipt() -> None:
    reconciliation = AgentControlLoopNarrativeReconciliation(
        reconciliation_id="narrative-reconciliation-0123456789ab",
        round_number=1,
        status="not_applicable",
        authority="model_only",
        model_disposition="adopted",
        model_returned=True,
        message="没有确定性成果，保留模型回执供审阅。",
        checked_at=datetime.now(timezone.utc),
    )
    results = [
        ReadonlyWorkerContribution(
            worker_run_id="worker-success-1",
            branch_id="branch-success-1",
            outcome="adopted",
            summary="已通过 Anchor 核对",
            source_file_refs=("forte-1111111111111111",),
            evidence_anchors=("line:1",),
            model_called=True,
            output_used=True,
            narrative_reconciliation=reconciliation,
        ),
        ReadonlyWorkerContribution(
            worker_run_id="worker-success-2",
            branch_id="branch-success-2",
            outcome="adopted",
            summary="已通过 Anchor 核对",
            source_file_refs=("forte-2222222222222222",),
            evidence_anchors=("line:2",),
            model_called=True,
            output_used=True,
            narrative_reconciliation=reconciliation,
        ),
        ReadonlyWorkerContribution(
            worker_run_id="worker-ambiguous",
            branch_id="branch-ambiguous",
            outcome="ambiguous",
            summary="原文位置不唯一",
            source_file_refs=("forte-3333333333333333",),
            model_called=True,
            output_used=False,
            narrative_reconciliation=reconciliation,
        ),
    ]
    merged = merge_adopted_contributions(results, version=3)
    assert merged.artifact_id.startswith("artifact-")
    assert merged.version == 3
    assert merged.adopted_worker_run_ids == ("worker-success-1", "worker-success-2")
    assert merged.waiting_branch_ids == ("branch-ambiguous",)
    assert all(item.narrative_reconciliation is not None for item in results)
