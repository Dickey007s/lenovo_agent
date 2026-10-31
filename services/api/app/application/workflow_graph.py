"""Server-side projection of a run into a small, clickable workflow graph.

The graph is derived only from facts the server already owns: the validated
plan, branch status, worker contributions, topology admission and the office
action.  Nothing here is produced by a model, and it never changes a run.

Each node carries a risk assessment (L0-L5, AL0-AL5 and the eight dimensions of
the design manual) so the front end can show a short card on hover and the full
explanation on demand.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.application.action_dimensions import (
    RiskAssessment,
    assess_analysis_unit,
    assess_delivery,
    assess_intake,
    assess_office_action,
)

NodeStatus = Literal["pending", "running", "done", "waiting_human", "failed", "stopped"]
NodeKind = Literal["plan", "work_unit", "deliver", "action"]
Actor = Literal["agent", "human", "system"]

TOOL_LABELS = {
    "file.read": "读取文件",
    "table.inspect": "查看表格",
    "artifact.write": "生成交付文件",
    "evidence.verify": "核对证据",
    "action.preview": "对外动作预览",
}

_TERMINAL = {"completed", "failed", "stopped", "budget_exhausted", "user_stopped"}
_HUMAN_WAIT = {"waiting_input", "ready_to_execute", "awaiting_confirmation"}


class WorkflowNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    label: str = Field(min_length=1, max_length=80)
    kind: NodeKind
    status: NodeStatus
    status_label: str
    actor: Actor
    actor_label: str
    summary: str = Field(default="", max_length=400)
    facts: list[str] = Field(default_factory=list, max_length=8)
    sources: list[str] = Field(default_factory=list, max_length=12)
    depends_on: list[str] = Field(default_factory=list, max_length=12)
    branch_id: str | None = None
    assessment: RiskAssessment


class WorkflowEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["running", "waiting_human", "done", "failed", "stopped"]
    label: str
    can_interrupt: bool = False
    # Main agent plus delegated read-only workers; 0 for fixed-rule actions.
    agent_count: int = Field(default=1, ge=0, le=40)
    delegated_count: int = Field(default=0, ge=0, le=40)


class WorkflowGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["workflow-graph.v1"] = "workflow-graph.v1"
    mode: Literal["control_loop", "office_action"]
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    state: WorkflowState


def _short(text: str, limit: int) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _run_state(status: str, control_state: str) -> tuple[str, str]:
    if status == "completed":
        return "done", "已完成"
    if status in {"failed", "budget_exhausted"}:
        return "failed", "未完成" if status == "budget_exhausted" else "失败"
    if status in {"stopped", "user_stopped"} or control_state == "stopped":
        return "stopped", "已中断"
    if status in _HUMAN_WAIT:
        return "waiting_human", "等你处理"
    if control_state in {"paused", "pause_requested"}:
        return "waiting_human", "已暂停"
    return "running", "处理中"


_BRANCH_STATUS: dict[str, tuple[NodeStatus, str]] = {
    "running": ("running", "处理中"),
    "pending": ("pending", "未开始"),
    "blocked": ("pending", "等待前序"),
    "completed": ("done", "已完成"),
    "waiting_input": ("waiting_human", "等你处理"),
    "stopped": ("stopped", "已中断"),
    "failed": ("failed", "失败"),
}


def build_control_loop_workflow(
    *,
    status: str,
    control_state: str,
    plan: Any | None,
    branches: Iterable[Any],
    worker_runs: Iterable[Any],
    topology_mode: str | None,
    ref_to_label: dict[str, str],
    artifact_count: int,
    open_decision_branch_ids: set[str],
    allowed_file_count: int,
) -> WorkflowGraph:
    state_status, state_label = _run_state(status, control_state)
    terminal_failure = state_status in {"failed", "stopped"}
    by_unit = {branch.unit_id: branch for branch in branches}
    workers = list(worker_runs)
    adaptive = topology_mode == "adaptive_readonly_workers"
    delegated = len({item.worker_run_id for item in workers}) if adaptive else 0

    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []

    plan_status: NodeStatus
    if plan is not None:
        plan_status, plan_label = "done", "已完成"
    elif terminal_failure:
        plan_status, plan_label = ("failed", "失败") if state_status == "failed" else ("stopped", "已中断")
    else:
        plan_status, plan_label = "running", "处理中"
    nodes.append(
        WorkflowNode(
            node_id="plan",
            label="理解任务 · 制定计划",
            kind="plan",
            status=plan_status,
            status_label=plan_label,
            actor="agent",
            actor_label="主 Agent",
            summary=_short(plan.summary, 160) if plan is not None else "正在理解任务并选择要读的资料。",
            facts=[f"计划包含 {len(plan.units)} 项工作"] if plan is not None else [],
            assessment=assess_intake(file_count=allowed_file_count),
        )
    )

    unit_ids: list[str] = []
    leaves: set[str] = set()
    if plan is not None:
        leaves = {unit.unit_id for unit in plan.units}
        for unit in plan.units:
            leaves -= set(unit.depends_on)
        for unit in plan.units:
            branch = by_unit.get(unit.unit_id)
            if branch is None:
                node_status: NodeStatus = "stopped" if terminal_failure else "pending"
                node_label = "已中断" if terminal_failure else "未开始"
            else:
                node_status, node_label = _BRANCH_STATUS.get(branch.status, ("pending", "未开始"))
                if branch.branch_id in open_decision_branch_ids and node_status != "done":
                    node_status, node_label = "waiting_human", "等你处理"
                if getattr(branch, "requires_human_gate", False) and node_status == "waiting_human":
                    node_label = "等你确认"
            sources = [ref_to_label.get(ref, "公开办公文件") for ref in unit.input_file_refs][:12]
            facts = [f"工具：{TOOL_LABELS.get(unit.tool, unit.tool)}", f"依据：{len(unit.input_file_refs)} 份文件"]
            if branch is not None and branch.missing_file_refs:
                facts.append(f"{len(branch.missing_file_refs)} 份文件尚未核对")
            if node_label == "等待前序":
                facts.append("前序工作完成后才会开始")
            agent_label = "只读 Worker" if adaptive else "主 Agent"
            nodes.append(
                WorkflowNode(
                    node_id=unit.unit_id,
                    label=_short(unit.title, 40),
                    kind="work_unit",
                    status=node_status,
                    status_label=node_label,
                    actor="human" if node_status == "waiting_human" else "agent",
                    actor_label="需要你" if node_status == "waiting_human" else agent_label,
                    summary=_short(unit.objective, 200),
                    facts=facts,
                    sources=sources,
                    depends_on=list(unit.depends_on),
                    branch_id=branch.branch_id if branch is not None else None,
                    assessment=assess_analysis_unit(
                        tool=unit.tool,
                        side_effect=unit.side_effect,
                        requires_human_gate=unit.requires_human_gate,
                        file_count=len(unit.input_file_refs),
                        depends_on_count=len(unit.depends_on),
                        artifact_name=unit.artifact_name,
                    ),
                )
            )
            unit_ids.append(unit.unit_id)
            for dependency in unit.depends_on or ["plan"]:
                edges.append(WorkflowEdge(source=dependency, target=unit.unit_id))

    all_done = bool(unit_ids) and all(
        node.status == "done" for node in nodes if node.kind == "work_unit"
    )
    if state_status == "done":
        deliver_status, deliver_label = "done", "已完成"
    elif terminal_failure:
        deliver_status, deliver_label = ("failed", "未完成") if state_status == "failed" else ("stopped", "已中断")
    elif all_done and state_status == "running":
        deliver_status, deliver_label = "running", "处理中"
    elif all_done and state_status == "waiting_human":
        deliver_status, deliver_label = "waiting_human", "等你处理"
    else:
        deliver_status, deliver_label = "pending", "未开始"
    nodes.append(
        WorkflowNode(
            node_id="deliver",
            label="汇总核对 · 交付",
            kind="deliver",
            status=deliver_status,
            status_label=deliver_label,
            actor="human" if deliver_status == "waiting_human" else "agent",
            actor_label="需要你" if deliver_status == "waiting_human" else "主 Agent",
            summary="把各项工作的结果汇总，核对依据后交给你确认。",
            facts=[f"已形成 {artifact_count} 个交付版本"] if artifact_count else [],
            depends_on=sorted(leaves) if leaves else [],
            assessment=assess_delivery(artifact_count=artifact_count),
        )
    )
    for source in (sorted(leaves) if leaves else ["plan"]):
        edges.append(WorkflowEdge(source=source, target="deliver"))

    return WorkflowGraph(
        mode="control_loop",
        nodes=nodes,
        edges=edges,
        state=WorkflowState(
            status=state_status,  # type: ignore[arg-type]
            label=state_label,
            can_interrupt=state_status in {"running", "waiting_human"} and control_state == "running",
            agent_count=1 + delegated,
            delegated_count=delegated,
        ),
    )


_ACTION_STATUS: dict[str, tuple[NodeStatus, str, Actor]] = {
    "executed": ("done", "已办理", "system"),
    "decided": ("done", "已记录判断", "system"),
    "draft_ready": ("waiting_human", "草稿待你核对", "human"),
    "awaiting_confirmation": ("waiting_human", "等你确认", "human"),
    "awaiting_decision": ("waiting_human", "等你判断", "human"),
    "needs_input": ("waiting_human", "缺信息，等你补充", "human"),
    "deferred": ("waiting_human", "已暂缓", "human"),
    "stale": ("waiting_human", "内容已变化，需重新核对", "human"),
    "denied": ("failed", "已拒绝，转人工", "system"),
    "cancelled": ("stopped", "已取消", "system"),
    "undone": ("stopped", "已撤销", "system"),
}


def build_office_action_workflow(action: Any, *, source_label: str | None = None) -> WorkflowGraph:
    node_status, node_label, actor = _ACTION_STATUS.get(action.status, ("pending", "未开始", "system"))
    data = action.input
    assessment = assess_office_action(
        data.operation,
        target_label=action.target_label if data.target else "",
        due_date=data.due_date.isoformat() if data.due_date else None,
        source_label=source_label or action.source_label,
        risk_level=action.risk_level,
        autonomy_level=action.autonomy_level,
        restricted_reason=action.reason if action.risk_level == "L5" else None,
    )
    facts = [f"协作方式：{action.mode}", action.reversibility]
    if action.missing_fields:
        facts.append("还缺：" + "、".join(action.missing_fields))
    node = WorkflowNode(
        node_id="action",
        label=_short(data.title, 40),
        kind="action",
        status=node_status,
        status_label=node_label,
        actor=actor,
        actor_label="固定规则" if actor == "system" else "需要你",
        summary=_short(action.reason, 300),
        facts=[_short(item, 120) for item in facts if item][:6],
        sources=[action.source_label] if action.source_label else [],
        assessment=assessment,
    )
    state_status = {"done": "done", "waiting_human": "waiting_human", "failed": "failed", "stopped": "stopped"}.get(
        node_status, "running"
    )
    return WorkflowGraph(
        mode="office_action",
        nodes=[node],
        edges=[],
        state=WorkflowState(
            status=state_status,  # type: ignore[arg-type]
            label=node_label,
            can_interrupt=False,
            agent_count=0,
            delegated_count=0,
        ),
    )
