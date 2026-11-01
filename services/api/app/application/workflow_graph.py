"""Server-side projection of a run into a small, clickable workflow graph.

The graph is derived only from facts the server already owns: the validated
plan, branch status, worker contributions, topology admission and the office
action.  Nothing here is produced by a model, and it never changes a run.

Each node carries a risk assessment (L0-L5, AL0-AL5 and the eight dimensions of
the design manual) so the front end can show a short card on hover and the full
explanation on demand.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field

from services.api.app.application.action_dimensions import (
    RiskAssessment,
    assess_analysis_unit,
    assess_delivery,
    assess_human_gate,
    assess_intake,
    assess_office_action,
)

NodeStatus = Literal["pending", "running", "done", "waiting_human", "failed", "stopped"]
NodeKind = Literal["plan", "work_unit", "human_gate", "deliver", "action"]
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
    # human_gate nodes: which finding / request / missing requirement this is
    ref_id: str | None = None
    ref_kind: Literal["judgment", "source_choice", "missing", "start"] | None = None
    # human_gate nodes: left open by an earlier run of the same task and carried into this one
    carried: bool = False
    # Which run of the task added this node (the task keeps one tree; later runs extend it).
    run_sequence: int = Field(default=1, ge=1)
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


class WorkflowWave(BaseModel):
    """One batch of sub-agents released together (swarm view only)."""

    model_config = ConfigDict(extra="forbid")

    index: int = Field(ge=1)
    label: str
    status: NodeStatus
    node_ids: list[str] = Field(max_length=40)


class WorkflowGraph(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: Literal["workflow-graph.v1"] = "workflow-graph.v1"
    mode: Literal["control_loop", "office_action"]
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    state: WorkflowState
    swarm: bool = False
    waves: list[WorkflowWave] = Field(default_factory=list, max_length=12)


class HumanItem(BaseModel):
    """Something a person has to do before the run can be delivered."""

    model_config = ConfigDict(extra="forbid")

    item_id: str
    kind: Literal["judgment", "source_choice", "missing"]
    title: str
    reason: str
    parent_unit_ids: list[str] = Field(default_factory=list)
    # Left open by an earlier run of the same task; still waiting for the person.
    carried: bool = False
    # Carried items: the node of the task tree that already represents this item.
    node_id: str | None = None


def _same_topic(left: str, right: str, size: int = 6) -> bool:
    """True when two short Chinese titles share a run of at least ``size`` characters."""

    return SequenceMatcher(None, left, right).find_longest_match(0, len(left), 0, len(right)).size >= size


_GATE_LABEL = {"judgment": "待你判断", "source_choice": "待核对依据", "missing": "待补资料", "start": "待确认启动"}
_GATE_ORDER = ("judgment", "source_choice", "missing")


def collect_human_items(
    *,
    findings: Iterable[Any],
    decision_requests: Iterable[Any],
    decision_records: Iterable[Any],
    uncovered: Iterable[Any],
    branch_unit: dict[str, str],
) -> list[HumanItem]:
    """Open human work, from the same receipts the task board uses (no new judgement)."""

    requests = list(decision_requests)
    requested = {item.finding_id for item in requests}
    pending = {item.finding_id for item in requests if item.state in ("open", "deferred")}
    decided = {item.finding_id for item in decision_records if item.action != "defer"}
    items: list[HumanItem] = []
    seen: set[str] = set()

    def parents(branch_ids: Iterable[str], plan_unit_id: str | None) -> list[str]:
        found = [branch_unit[b] for b in branch_ids if b in branch_unit]
        if not found and plan_unit_id:
            found = [plan_unit_id]
        return list(dict.fromkeys(found))

    for index, finding in enumerate(findings):
        review = getattr(finding, "review", None)
        if review is None or not review.requires_human_decision:
            continue
        fid = finding.finding_id or ""
        if not (fid in pending or (fid not in requested and fid not in decided)):
            continue
        seen.add(fid)
        items.append(
            HumanItem(
                item_id=fid or f"finding-{index}",
                kind="judgment",
                title=_short(review.question or finding.title, 80),
                reason=_short(review.why_human, 300),
                parent_unit_ids=parents(finding.affected_branch_ids, finding.plan_unit_id),
            )
        )
    for request in requests:
        if request.state not in ("open", "deferred") or request.finding_id in seen:
            continue
        seen.add(request.finding_id)
        source_choice = bool(request.resolution_id)
        items.append(
            HumanItem(
                item_id=request.decision_request_id,
                kind="source_choice" if source_choice else "judgment",
                title="核对引用位置" if source_choice else "待决事项",
                reason=_short(request.reason, 300),
                parent_unit_ids=parents(
                    [request.branch_id] if request.branch_id else [], request.plan_unit_id
                ),
            )
        )
    for index, item in enumerate(uncovered):
        items.append(
            HumanItem(
                item_id=f"missing-{index}",
                kind="missing",
                title=_short(item.title, 80),
                reason=_short(item.reason, 300),
            )
        )
    return items


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
    human_items: Iterable[HumanItem] = (),
    swarm: bool = False,
) -> WorkflowGraph:
    state_status, state_label = _run_state(status, control_state)
    terminal_failure = state_status in {"failed", "stopped"}
    by_unit = {branch.unit_id: branch for branch in branches}
    workers = list(worker_runs)
    adaptive = topology_mode == "adaptive_readonly_workers"
    delegated = len({item.worker_run_id for item in workers}) if adaptive else 0
    gates = list(human_items)
    # Adaptive workers are admitted but not yet started: the first wave waits for the person's go-ahead.
    await_start = adaptive and status == "waiting_input" and not workers and plan is not None
    start_units: list[str] = []

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
                if await_start and node_status == "running" and not unit.depends_on:
                    node_status, node_label = "pending", "待启动"
                    start_units.append(unit.unit_id)
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
            agent_label = f"子 Agent {len(unit_ids) + 1}" if swarm else "只读 Worker" if adaptive else "主 Agent"
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

    start_gate = len(start_units) >= 2
    if start_gate:
        nodes.append(
            WorkflowNode(
                node_id="gate-start",
                label=_short(f"确认后并行启动 {len(start_units)} 项", 22),
                kind="human_gate",
                status="waiting_human",
                status_label=_GATE_LABEL["start"],
                actor="human",
                actor_label="需要你",
                summary=f"计划里有 {len(start_units)} 项可以同时做的只读工作。你确认后才分头启动，每批最多同时 3 项；确认前不会调用分析模型。",
                facts=["不修改任何文件", "确认后每批最多 3 项并行"],
                depends_on=["plan"],
                ref_id="start",
                ref_kind="start",
                assessment=assess_human_gate(kind="start"),
            )
        )
        edges.append(WorkflowEdge(source="plan", target="gate-start"))
        for edge in edges:
            if edge.source == "plan" and edge.target in start_units:
                edge.source = "gate-start"
        for node in nodes:
            if node.node_id in start_units:
                node.depends_on = ["gate-start"]
    else:
        # Fewer than two independent units: nothing to fan out, leave the branch as it was.
        for node in nodes:
            if node.node_id in start_units:
                node.status, node.status_label = "running", "处理中"
        start_units = []

    unit_nodes = [node for node in nodes if node.kind == "work_unit"]
    unit_by_id = {node.node_id for node in unit_nodes}
    gate_ids: list[str] = []
    merged = 0
    if state_status in {"done", "running", "waiting_human"} and plan is not None:
        for gate in gates:
            if gate.kind == "missing" and not gate.carried:
                # The planner sometimes plans a unit for a requirement it also reports as having no
                # source. Show one yellow step, not two.
                twin = next(
                    (
                        node
                        for node in unit_nodes
                        if node.status in {"pending", "running", "waiting_human"}
                        and node.ref_id is None
                        and _same_topic(gate.title, node.label + node.summary)
                    ),
                    None,
                )
                if twin is not None:
                    twin.status, twin.actor, twin.actor_label = "waiting_human", "human", "需要你"
                    twin.status_label = _GATE_LABEL["missing"]
                    twin.summary = _short(f"{gate.title}：{gate.reason}", 400)
                    twin.ref_id, twin.ref_kind = gate.item_id, "missing"
                    twin.assessment = assess_human_gate(kind="missing", reason=_short(gate.reason, 160))
                    merged += 1
                    continue
            node_id = "gate-" + gate.item_id
            parents = [parent for parent in gate.parent_unit_ids if parent in unit_by_id] or ["plan"]
            facts = ["等你处理；不依赖它的分支继续推进"]
            if gate.carried:
                facts = ["上一轮留下的待办，这一轮还没有处理", *facts]
            nodes.append(
                WorkflowNode(
                    node_id=node_id,
                    label=_short(gate.title, 22),
                    kind="human_gate",
                    status="waiting_human",
                    status_label=_GATE_LABEL[gate.kind],
                    actor="human",
                    actor_label="需要你",
                    summary=_short(f"{gate.title}：{gate.reason}", 400),
                    facts=facts,
                    depends_on=parents,
                    ref_id=gate.item_id,
                    ref_kind=gate.kind,
                    carried=gate.carried,
                    assessment=assess_human_gate(kind=gate.kind, reason=_short(gate.reason, 160)),
                )
            )
            gate_ids.append(node_id)
            for parent in parents:
                edges.append(WorkflowEdge(source=parent, target=node_id))
                leaves.discard(parent)
    if start_gate:
        state_label = _GATE_LABEL["start"]
        if state_status in {"done", "running"}:
            state_status = "waiting_human"
    elif gate_ids or merged:
        kinds = {gate.kind for gate in gates}
        state_label = _GATE_LABEL[next(kind for kind in _GATE_ORDER if kind in kinds)]
        if state_status in {"done", "running"}:
            state_status = "waiting_human"
    leaves |= set(gate_ids)
    all_done = bool(unit_ids) and not (gate_ids or merged or start_gate) and all(node.status == "done" for node in unit_nodes)
    if (gate_ids or merged or start_gate) and not terminal_failure:
        deliver_status, deliver_label = "pending", "等你处理后交付"
    elif state_status == "done":
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

    waves: list[WorkflowWave] = []
    if swarm and unit_nodes:
        # Each work unit is one sub-agent; units with no unfinished dependency go out together.
        depth: dict[str, int] = {}
        by_id = {node.node_id: node for node in unit_nodes}

        def level(node_id: str, trail: frozenset[str] = frozenset()) -> int:
            if node_id in depth:
                return depth[node_id]
            deps = [d for d in by_id[node_id].depends_on if d in by_id and d not in trail]
            depth[node_id] = 1 + max((level(d, trail | {node_id}) for d in deps), default=-1)
            return depth[node_id]

        for node in unit_nodes:
            level(node.node_id)
        for index in range(max(depth.values()) + 1):
            members = [node for node in unit_nodes if depth[node.node_id] == index]
            statuses = {node.status for node in members}
            wave_status: NodeStatus = (
                "failed" if "failed" in statuses
                else "stopped" if "stopped" in statuses
                else "waiting_human" if "waiting_human" in statuses
                else "running" if "running" in statuses
                else "done" if statuses == {"done"}
                else "pending"
            )
            waves.append(
                WorkflowWave(
                    index=index + 1,
                    label=f"第 {index + 1} 波 · {len(members)} 个子 Agent 并行",
                    status=wave_status,
                    node_ids=[node.node_id for node in members],
                )
            )
        delegated = len(unit_nodes)

    return WorkflowGraph(
        mode="control_loop",
        nodes=nodes,
        edges=edges,
        swarm=bool(waves),
        waves=waves,
        state=WorkflowState(
            status=state_status,  # type: ignore[arg-type]
            label=state_label,
            can_interrupt=state_status in {"running", "waiting_human"}
            and control_state == "running"
            and status not in _TERMINAL,
            agent_count=min(40, 1 + delegated),
            delegated_count=min(40, delegated),
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


_OPEN_GATE_KINDS = {"judgment", "source_choice", "missing"}


def carried_node_ids(prior: WorkflowGraph, items: Iterable[HumanItem], run_sequence: int) -> dict[str, str]:
    """Map each still-open item of the parent run to the node of the task tree that shows it."""

    found: dict[str, str] = {}
    for item in items:
        if item.carried and item.node_id:
            found[item.item_id] = item.node_id
            continue
        node = next(
            (
                node
                for node in prior.nodes
                if node.ref_id == item.item_id
                and node.ref_kind == item.kind
                and node.status == "waiting_human"
                and node.run_sequence == run_sequence
            ),
            None,
        )
        if node is not None:
            found[item.item_id] = node.node_id
    return found


def merge_task_tree(
    prior: WorkflowGraph,
    current: WorkflowGraph,
    *,
    run_sequence: int,
    carried: dict[str, str],
) -> WorkflowGraph:
    """Extend the task's one tree with a follow-up run instead of starting a second tree.

    Earlier nodes stay where they were. A yellow step that this run settled turns green; one that is
    still open stays yellow. The new plan hangs under what is finished so far, and a single delivery
    node closes the tree.
    """

    prefix = f"r{run_sequence}-"
    kept_open = set(carried.values())
    old_deliver = {node.node_id for node in prior.nodes if node.kind == "deliver"}

    old_nodes = [node.model_copy(deep=True) for node in prior.nodes if node.node_id not in old_deliver]
    old_edges = [edge.model_copy() for edge in prior.edges if edge.source not in old_deliver and edge.target not in old_deliver]
    for node in old_nodes:
        node.carried = node.node_id in kept_open
        if node.carried:
            continue
        if node.status == "waiting_human" and node.ref_kind in _OPEN_GATE_KINDS:
            node.status, node.status_label = "done", "已处理"
            node.actor, node.actor_label = "system", "已处理"
            node.facts = ["之后的追加要求已处理这一项", *node.facts][:8]
    if not kept_open:
        for node in old_nodes:
            if node.kind == "work_unit" and node.status == "waiting_human" and node.ref_kind is None:
                node.status, node.status_label = "done", "已完成"
                node.actor, node.actor_label = "agent", "主 Agent"

    # Nodes of this run that already live in the tree (open items carried in) are not drawn twice.
    redirect = {f"gate-{item_id}": node_id for item_id, node_id in carried.items()}
    dropped = {node.node_id for node in current.nodes if node.carried and node.node_id in redirect}

    def new_id(node_id: str) -> str:
        if node_id in redirect:
            return redirect[node_id]
        return node_id if node_id == "deliver" else prefix + node_id

    with_dep = {edge.source for edge in old_edges}
    open_ids = kept_open
    leaves = [node.node_id for node in old_nodes if node.node_id not in with_dep and node.node_id not in open_ids]

    new_nodes: list[WorkflowNode] = []
    for node in current.nodes:
        if node.node_id in dropped:
            continue
        fresh = node.model_copy(deep=True)
        fresh.node_id = new_id(node.node_id)
        fresh.run_sequence = run_sequence
        fresh.depends_on = list(dict.fromkeys(new_id(dep) for dep in node.depends_on))
        if node.kind == "plan":
            fresh.label = "理解新要求 · 追加计划"
            fresh.depends_on = list(leaves)
        new_nodes.append(fresh)

    plan_id = new_id("plan")
    new_edges: list[WorkflowEdge] = []
    for edge in current.edges:
        if edge.target in dropped:
            continue
        new_edges.append(WorkflowEdge(source=new_id(edge.source), target=new_id(edge.target)))
    new_edges.extend(WorkflowEdge(source=leaf, target=plan_id) for leaf in leaves)
    # Earlier open steps still hold up the delivery.
    deliver = next((node for node in new_nodes if node.kind == "deliver"), None)
    if deliver is not None:
        for node_id in sorted(open_ids):
            if node_id not in deliver.depends_on:
                deliver.depends_on.append(node_id)
            new_edges.append(WorkflowEdge(source=node_id, target=deliver.node_id))

    seen: set[tuple[str, str]] = set()
    edges: list[WorkflowEdge] = []
    for edge in [*old_edges, *new_edges]:
        key = (edge.source, edge.target)
        if key not in seen and edge.source != edge.target:
            seen.add(key)
            edges.append(edge)

    waves = [wave.model_copy(deep=True) for wave in prior.waves]
    for wave in current.waves:
        waves.append(
            WorkflowWave(
                index=len(waves) + 1,
                label=wave.label,
                status=wave.status,
                node_ids=[new_id(node_id) for node_id in wave.node_ids],
            )
        )
    for index, wave in enumerate(waves, start=1):
        wave.index = index
        wave.label = f"第 {index} 波 · {len(wave.node_ids)} 个子 Agent 并行"
    state = current.state.model_copy(
        update={
            "agent_count": max(current.state.agent_count, prior.state.agent_count),
            "delegated_count": max(current.state.delegated_count, prior.state.delegated_count),
        }
    )
    return WorkflowGraph(
        mode="control_loop",
        nodes=[*old_nodes, *new_nodes],
        edges=edges,
        state=state,
        swarm=bool(waves),
        waves=waves,
    )
