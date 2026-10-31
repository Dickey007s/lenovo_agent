"""Workflow graph and eight-dimension explanations follow the design manual."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from packages.contracts.office_actions import ActionInput
from services.api.app.application.action_dimensions import (
    AUTONOMY_LEVELS,
    DIMENSION_LABELS,
    RISK_LEVELS,
    assess_analysis_unit,
    assess_office_action,
)
from services.api.app.application.office_action_policy import prepare_action
from services.api.app.application.workflow_graph import (
    build_control_loop_workflow,
    build_office_action_workflow,
    collect_human_items,
)

APP = Path(__file__).resolve().parents[2] / "apps/web/app"
LEVEL_CASES = json.loads((APP / "office-action-examples.json").read_text(encoding="utf-8"))
MANUAL_DIMENSIONS = ["动作和对象", "数据流向", "状态变化", "影响范围", "恢复能力", "意图和证据", "权限和制度", "使用环境"]


def test_dimensions_match_the_manual_order():
    assert list(DIMENSION_LABELS.values()) == MANUAL_DIMENSIONS
    assert list(RISK_LEVELS) == ["L0", "L1", "L2", "L3", "L4", "L5"]
    assert list(AUTONOMY_LEVELS) == ["AL0", "AL1", "AL2", "AL3", "AL4", "AL5"]


@pytest.mark.parametrize("case", LEVEL_CASES, ids=lambda item: item["id"])
def test_level_case_assessment_agrees_with_policy(case):
    action = prepare_action(ActionInput.model_validate(case["input"]))
    graph = build_office_action_workflow(action)
    node = graph.nodes[0]
    assert graph.mode == "office_action"
    assert len(graph.nodes) == 1 and graph.edges == []
    # The explanation can never disagree with the policy that actually ran.
    assert node.assessment.risk_level == action.risk_level == case["level"]
    assert node.assessment.autonomy_level == action.autonomy_level == case["autonomy"]
    assert [item.label for item in node.assessment.dimensions] == MANUAL_DIMENSIONS
    assert all(item.finding.strip() for item in node.assessment.dimensions)
    assert any(item.drives_level for item in node.assessment.dimensions)
    assert node.assessment.collaboration == RISK_LEVELS[case["level"]][1]
    assert graph.state.agent_count == 0
    assert graph.state.can_interrupt is False


def test_office_action_node_status_and_colour_semantics():
    by_level = {case["level"]: build_office_action_workflow(prepare_action(ActionInput.model_validate(case["input"]))) for case in LEVEL_CASES}
    assert by_level["L1"].nodes[0].status == "done"
    assert by_level["L2"].nodes[0].status == "waiting_human"
    assert by_level["L3"].nodes[0].status == "waiting_human"
    assert by_level["L4"].nodes[0].status == "waiting_human"
    assert by_level["L5"].nodes[0].status == "failed"
    assert by_level["L5"].nodes[0].status_label == "已拒绝，转人工"
    for level in ("L2", "L3", "L4"):
        assert by_level[level].nodes[0].actor == "human"


def test_restricted_message_is_explained_as_restricted_not_as_send():
    assessment = assess_office_action("send_message", target_label="某联系人", risk_level="L5", autonomy_level="AL1", restricted_reason="含无权作出的承诺")
    assert assessment.risk_level == "L5"
    authority = next(item for item in assessment.dimensions if item.key == "authority")
    assert "无权作出的承诺" in authority.finding and authority.drives_level


def _unit(unit_id, *, depends_on=(), tool="file.read", side_effect="none", gate=False, files=1):
    return SimpleNamespace(
        unit_id=unit_id, title=f"工作 {unit_id}", objective=f"目标 {unit_id}", input_file_refs=[f"forte-{index:016x}" for index in range(files)],
        depends_on=list(depends_on), tool=tool, requires_human_gate=gate, side_effect=side_effect, artifact_name="报告" if tool == "artifact.write" else None,
    )


def _branch(unit_id, status, *, gate=False):
    return SimpleNamespace(unit_id=unit_id, branch_id=f"branch-{unit_id:0>12}", status=status, requires_human_gate=gate, missing_file_refs=[])


def _graph(units, branches, *, status="running", control="running", workers=(), mode=None, decisions=frozenset(), human=(), swarm=False):
    plan = SimpleNamespace(summary="计划摘要", units=units) if units is not None else None
    return build_control_loop_workflow(
        status=status, control_state=control, plan=plan, branches=branches, worker_runs=workers, topology_mode=mode,
        ref_to_label={}, artifact_count=0, open_decision_branch_ids=set(decisions), allowed_file_count=5,
        human_items=human, swarm=swarm,
    )


def test_fork_and_join_edges_follow_depends_on():
    units = [_unit("a"), _unit("b"), _unit("c", depends_on=["a", "b"], tool="artifact.write", side_effect="run_workspace_write")]
    graph = _graph(units, [_branch("a", "completed"), _branch("b", "running"), _branch("c", "blocked")])
    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert edges == {("plan", "a"), ("plan", "b"), ("a", "c"), ("b", "c"), ("c", "deliver")}
    status = {node.node_id: node.status for node in graph.nodes}
    assert status == {"plan": "done", "a": "done", "b": "running", "c": "pending", "deliver": "pending"}
    assert next(node for node in graph.nodes if node.node_id == "c").status_label == "等待前序"
    assert graph.state.status == "running" and graph.state.can_interrupt is True


def test_human_gate_and_open_decision_turn_the_node_yellow():
    units = [_unit("a", gate=True), _unit("b")]
    branches = [_branch("a", "waiting_input", gate=True), _branch("b", "running")]
    graph = _graph(units, branches, status="waiting_input")
    nodes = {node.node_id: node for node in graph.nodes}
    assert nodes["a"].status == "waiting_human" and nodes["a"].actor == "human" and nodes["a"].status_label == "等你确认"
    assert nodes["b"].actor == "agent"
    assert graph.state.status == "waiting_human"
    decided = _graph([_unit("b")], [_branch("b", "running")], status="waiting_input", decisions={"branch-00000000000b"})
    assert next(node for node in decided.nodes if node.node_id == "b").status == "waiting_human"


def test_terminal_states():
    units = [_unit("a")]
    done = _graph(units, [_branch("a", "completed")], status="completed")
    assert [node.status for node in done.nodes] == ["done", "done", "done"]
    assert done.state.can_interrupt is False
    stopped = _graph(units, [], status="stopped", control="stopped")
    assert {node.node_id: node.status for node in stopped.nodes} == {"plan": "done", "a": "stopped", "deliver": "stopped"}
    failed = _graph(None, [], status="failed")
    assert failed.nodes[0].status == "failed" and failed.state.status == "failed"
    early = _graph(None, [])
    assert early.nodes[0].status == "running" and early.nodes[-1].status == "pending"


def test_agent_count_counts_delegated_workers_only_when_admitted():
    workers = [SimpleNamespace(worker_run_id="w1"), SimpleNamespace(worker_run_id="w2"), SimpleNamespace(worker_run_id="w2")]
    adaptive = _graph([_unit("a"), _unit("b")], [_branch("a", "running"), _branch("b", "running")], workers=workers, mode="adaptive_readonly_workers")
    assert adaptive.state.agent_count == 3 and adaptive.state.delegated_count == 2
    assert {node.actor_label for node in adaptive.nodes if node.kind == "work_unit"} == {"只读 Worker"}
    single = _graph([_unit("a")], [_branch("a", "running")], workers=workers, mode="single_controller")
    assert single.state.agent_count == 1 and single.state.delegated_count == 0


@pytest.mark.parametrize(
    ("kwargs", "level", "autonomy"),
    [
        (dict(tool="file.read", side_effect="none", requires_human_gate=False), "L2", "AL2"),
        (dict(tool="artifact.write", side_effect="run_workspace_write", requires_human_gate=False), "L2", "AL2"),
        (dict(tool="file.read", side_effect="none", requires_human_gate=True), "L3", "AL3"),
        (dict(tool="action.preview", side_effect="external_action", requires_human_gate=True), "L4", "AL3"),
    ],
)
def test_unit_levels_follow_side_effect_and_gate(kwargs, level, autonomy):
    assessment = assess_analysis_unit(file_count=2, depends_on_count=1, **kwargs)
    assert (assessment.risk_level, assessment.autonomy_level) == (level, autonomy)
    assert len(assessment.dimensions) == 8


def _finding(fid, *, units, question="是否批准变更？"):
    review = SimpleNamespace(requires_human_decision=True, question=question, why_human="与明确备注冲突")
    return SimpleNamespace(finding_id=fid, plan_unit_id=None, affected_branch_ids=[f"branch-{u:0>12}" for u in units], title="发现", review=review)


def _items(findings=(), requests=(), records=(), uncovered=(), units=("a", "b", "c")):
    return collect_human_items(
        findings=findings, decision_requests=requests, decision_records=records, uncovered=uncovered,
        branch_unit={f"branch-{u:0>12}": u for u in units},
    )


def test_fork_with_one_branch_paused_for_a_person_while_others_finish():
    units = [_unit("a"), _unit("b"), _unit("c")]
    branches = [_branch(u, "completed") for u in "abc"]
    human = _items(findings=[_finding("finding-aaaaaaaaaaaa", units=["b"])])
    graph = _graph(units, branches, status="completed", human=human)
    nodes = {node.node_id: node for node in graph.nodes}
    gate = nodes["gate-finding-aaaaaaaaaaaa"]
    assert gate.kind == "human_gate" and gate.status == "waiting_human" and gate.status_label == "待你判断"
    assert gate.depends_on == ["b"] and gate.assessment.risk_level == "L3"
    # the siblings are finished, the gate holds only its own branch and the delivery
    assert [nodes[u].status for u in "abc"] == ["done"] * 3
    assert nodes["deliver"].status == "pending" and nodes["deliver"].status_label == "等你处理后交付"
    edges = {(edge.source, edge.target) for edge in graph.edges}
    assert ("b", "gate-finding-aaaaaaaaaaaa") in edges and ("gate-finding-aaaaaaaaaaaa", "deliver") in edges
    assert ("b", "deliver") not in edges and {("a", "deliver"), ("c", "deliver")} <= edges
    # a completed run that still waits for a person is not "done" and cannot be interrupted
    assert graph.state.status == "waiting_human" and graph.state.label == "待你判断" and graph.state.can_interrupt is False


def test_single_line_stuck_on_a_person():
    graph = _graph([_unit("a")], [_branch("a", "completed")], status="completed", human=_items(findings=[_finding("finding-bbbbbbbbbbbb", units=["a"])], units=("a",)))
    assert [node.node_id for node in graph.nodes] == ["plan", "a", "gate-finding-bbbbbbbbbbbb", "deliver"]
    assert {(e.source, e.target) for e in graph.edges} == {("plan", "a"), ("a", "gate-finding-bbbbbbbbbbbb"), ("gate-finding-bbbbbbbbbbbb", "deliver")}


def test_missing_material_branches_from_the_plan_and_decided_items_disappear():
    missing = SimpleNamespace(title="银行到账回单", reason="资料库没有这份凭证")
    human = _items(uncovered=[missing])
    graph = _graph([_unit("a")], [_branch("a", "completed")], status="completed", human=human)
    gate = next(node for node in graph.nodes if node.kind == "human_gate")
    assert gate.status_label == "待补资料" and gate.depends_on == ["plan"] and gate.assessment.risk_level == "L2"
    assert graph.state.label == "待补资料"
    finding = _finding("finding-cccccccccccc", units=["a"])
    answered = SimpleNamespace(finding_id="finding-cccccccccccc", action="accept")
    assert _items(findings=[finding], records=[answered]) == []
    still_open = SimpleNamespace(finding_id="finding-cccccccccccc", state="open", resolution_id=None, decision_request_id="decision-request-000000000001", reason="待决", branch_id=None, plan_unit_id=None)
    assert [item.kind for item in _items(findings=[finding], requests=[still_open])] == ["judgment"]


def test_swarm_groups_independent_units_into_waves():
    units = [_unit("a"), _unit("b"), _unit("c"), _unit("d", depends_on=["a", "b", "c"], tool="artifact.write", side_effect="run_workspace_write")]
    branches = [_branch("a", "completed"), _branch("b", "running"), _branch("c", "running"), _branch("d", "blocked")]
    graph = _graph(units, branches, swarm=True)
    assert graph.swarm and [(w.label, w.status, w.node_ids) for w in graph.waves] == [
        ("第 1 波 · 3 个子 Agent 并行", "running", ["a", "b", "c"]),
        ("第 2 波 · 1 个子 Agent 并行", "pending", ["d"]),
    ]
    assert graph.state.agent_count == 5 and graph.state.delegated_count == 4
    assert [node.actor_label for node in graph.nodes if node.kind == "work_unit"] == ["子 Agent 1", "子 Agent 2", "子 Agent 3", "子 Agent 4"]
    plain = _graph(units, branches)
    assert not plain.swarm and plain.waves == [] and plain.state.agent_count == 1


def test_a_planned_unit_and_its_missing_requirement_are_one_yellow_step():
    unit = _unit("a")
    unit.title = "核对绵阳公司往来银行到账回单"
    missing = SimpleNamespace(title="核对银行到账回单并判断是否到账", reason="资料库没有到账回单")
    graph = _graph([unit, _unit("b")], [_branch("a", "waiting_input"), _branch("b", "completed")], status="waiting_input", human=_items(uncovered=[missing], units=("a", "b")))
    assert [node.kind for node in graph.nodes] == ["plan", "work_unit", "work_unit", "deliver"]  # no duplicate gate
    twin = next(node for node in graph.nodes if node.node_id == "a")
    assert twin.status == "waiting_human" and twin.status_label == "待补资料" and twin.ref_kind == "missing"
    assert next(node for node in graph.nodes if node.node_id == "b").status == "done"
    assert graph.state.label == "待补资料" and graph.nodes[-1].status == "pending"


def test_admitted_workers_wait_for_one_go_ahead_before_fanning_out():
    units = [_unit("a"), _unit("b"), _unit("c")]
    branches = [_branch("a", "running"), _branch("b", "running"), _branch("c", "running")]
    graph = _graph(units, branches, status="waiting_input", mode="adaptive_readonly_workers")
    gate = next(node for node in graph.nodes if node.node_id == "gate-start")
    assert (gate.status, gate.ref_kind, gate.status_label) == ("waiting_human", "start", "待确认启动")
    assert {(edge.source, edge.target) for edge in graph.edges} == {
        ("plan", "gate-start"), ("gate-start", "a"), ("gate-start", "b"), ("gate-start", "c"),
        ("a", "deliver"), ("b", "deliver"), ("c", "deliver"),
    }
    assert [(node.status, node.status_label) for node in graph.nodes if node.kind == "work_unit"] == [("pending", "待启动")] * 3
    assert graph.state.status == "waiting_human" and graph.state.label == "待确认启动"
    # Once workers have run, there is no start gate any more.
    started = _graph(units, branches, status="waiting_input", mode="adaptive_readonly_workers", workers=[SimpleNamespace(worker_run_id="w1")])
    assert all(node.node_id != "gate-start" for node in started.nodes)
    # A single unit has nothing to fan out, so it keeps running as before.
    single = _graph([_unit("a")], [_branch("a", "running")], status="waiting_input", mode="adaptive_readonly_workers")
    assert all(node.node_id != "gate-start" for node in single.nodes)
