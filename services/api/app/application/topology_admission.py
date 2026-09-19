"""Deterministic topology admission for the bounded Demo 2 slice.

This module only decides an execution shape from server-validated plan facts.
It never assigns a score, predicts a cost/SLA, or lets a model request workers.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.api.app.application.harness_runtime import HarnessPlan


TopologyMode = Literal[
    "single_controller", "fixed_workflow", "adaptive_readonly_workers"
]


class TopologyAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    admission_version: Literal["topology-admission.v1"] = "topology-admission.v1"
    mode: TopologyMode
    work_unit_breadth: int = Field(ge=1)
    independent_branch_count: int = Field(ge=0)
    dependency_parallelism: int = Field(ge=0)
    source_span: int = Field(ge=1)
    remaining_model_calls: int = Field(ge=0)
    remaining_time_seconds: int = Field(ge=0)
    external_action: Literal["none"] = "none"
    reasons: list[str] = Field(min_length=1, max_length=8)
    user_confirmation_required: bool = True


def admit_topology(
    plan: "HarnessPlan",
    *,
    remaining_model_calls: int,
    remaining_time_seconds: int,
    source_facts: dict[str, dict[str, object]] | None = None,
) -> TopologyAdmission:
    """Choose the smallest safe topology using only validated server facts."""

    breadth = len(plan.units)
    independent = sum(1 for unit in plan.units if not unit.depends_on)
    refs = {ref for unit in plan.units for ref in unit.input_file_refs}
    dependent = sum(1 for unit in plan.units if unit.depends_on)
    risky = any(unit.side_effect != "none" or unit.requires_human_gate for unit in plan.units)
    structure_keys = {
        (
            str((source_facts or {}).get(ref, {}).get("display_group", "")),
            str((source_facts or {}).get(ref, {}).get("mime", "")),
            str((source_facts or {}).get(ref, {}).get("kind", "")),
            jsonable_columns((source_facts or {}).get(ref, {}).get("columns")),
        )
        for ref in refs
    }
    source_groups = {
        str((source_facts or {}).get(ref, {}).get("display_group", ""))
        for ref in refs
    }
    # A source structure is only a positive signal when the server has a
    # non-empty frozen group fact for every referenced file.  Independent
    # units from one directory/function stay on the conservative workflow;
    # adaptive workers are reserved for genuinely cross-function material.
    complete_source_groups = bool(source_facts) and all(
        ref in source_facts and str(source_facts[ref].get("display_group", ""))
        for ref in refs
    )
    same_display_group = complete_source_groups and len(source_groups) == 1
    same_structured_source_set = len(refs) >= 3 and len(structure_keys) == 1 and bool(source_facts)
    reasons: list[str] = [f"已校验 {breadth} 个工作单元，涉及 {len(refs)} 份来源材料。"]

    if independent < 2:
        mode: TopologyMode = "single_controller"
        reasons.append("独立分支少于 2 条，保持单 Controller 以避免伪造并行度。")
    elif risky:
        mode = "fixed_workflow"
        reasons.append("计划包含人工门或副作用意图，先使用固定流程，不启动只读 Worker。")
    elif independent > 3:
        mode = "fixed_workflow"
        reasons.append("独立分支超过 3 条受限 Worker 上限，保持固定流程并分批核对。")
    elif same_structured_source_set:
        mode = "fixed_workflow"
        reasons.append("多个独立工作包来自同结构同职能资料，先用固定流程避免把同源拆成伪并行。")
    elif complete_source_groups and same_display_group:
        mode = "fixed_workflow"
        reasons.append("多个独立工作包来自同一目录/职能，先用固定流程避免把同源拆成伪并行。")
    elif source_facts and not complete_source_groups:
        mode = "fixed_workflow"
        reasons.append("来源结构事实不完整或未能证明跨职能，保持固定流程。")
    elif remaining_model_calls < independent + 1:
        mode = "fixed_workflow"
        reasons.append("剩余模型调用不足以覆盖独立分支及合入校验，保持固定流程。")
    elif remaining_time_seconds < 20:
        mode = "fixed_workflow"
        reasons.append("剩余 Agent 执行时间不足，保持固定流程。")
    else:
        mode = "adaptive_readonly_workers"
        reasons.append("存在至少 2 条真正独立分支、预算充足且 external_action=none。")
    return TopologyAdmission(
        mode=mode,
        work_unit_breadth=breadth,
        independent_branch_count=independent,
        dependency_parallelism=max(0, independent - dependent),
        source_span=len(refs),
        remaining_model_calls=max(0, remaining_model_calls),
        remaining_time_seconds=max(0, remaining_time_seconds),
        reasons=reasons,
        # Only the high-cost adaptive route needs an explicit human
        # confirmation.  Single-controller and fixed-workflow routes are
        # already the conservative default and must not create a phantom gate.
        user_confirmation_required=mode == "adaptive_readonly_workers",
    )


# Descriptive alias used by callers that treat admission as a policy engine.
evaluate_topology_admission = admit_topology


def jsonable_columns(value: object) -> tuple[str, ...]:
    """Normalize server preview schema into a deterministic admission fact."""
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)
