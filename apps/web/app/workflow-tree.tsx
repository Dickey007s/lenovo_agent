"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { IconRobot, IconUser, IconPlayerStop, IconX } from "@tabler/icons-react";
import "./workflow-tree.css";

export type WorkflowStatus = "pending" | "running" | "done" | "waiting_human" | "failed" | "stopped";
export type WorkflowDimension = { key: string; label: string; finding: string; drives_level: boolean };
export type WorkflowAssessment = {
  risk_level: string; risk_title: string; autonomy_level: string; autonomy_title: string;
  collaboration: string; takeover_point: string; design_focus: string;
  dimensions: WorkflowDimension[]; rules: string[];
};
export type WorkflowNode = {
  node_id: string; label: string; kind: string; status: WorkflowStatus; status_label: string;
  actor: "agent" | "human" | "system"; actor_label: string; summary: string;
  facts: string[]; sources: string[]; depends_on: string[]; assessment: WorkflowAssessment;
};
export type WorkflowGraph = {
  mode: "control_loop" | "office_action";
  nodes: WorkflowNode[]; edges: { source: string; target: string }[];
  state: { status: "running" | "waiting_human" | "done" | "failed" | "stopped"; label: string; can_interrupt: boolean; agent_count: number; delegated_count: number };
};

const STATUSES: WorkflowStatus[] = ["pending", "running", "done", "waiting_human", "failed", "stopped"];
const text = (value: unknown, fallback = "") => typeof value === "string" ? value : fallback;
const list = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];

export function normalizeWorkflow(value: unknown): WorkflowGraph | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (!Array.isArray(raw.nodes) || raw.nodes.length === 0) return null;
  const nodes: WorkflowNode[] = [];
  for (const item of raw.nodes) {
    if (!item || typeof item !== "object") return null;
    const node = item as Record<string, unknown>;
    const assessment = node.assessment && typeof node.assessment === "object" ? node.assessment as Record<string, unknown> : null;
    if (!assessment || !Array.isArray(assessment.dimensions) || !STATUSES.includes(node.status as WorkflowStatus)) return null;
    nodes.push({
      node_id: text(node.node_id), label: text(node.label), kind: text(node.kind), status: node.status as WorkflowStatus,
      status_label: text(node.status_label), actor: node.actor === "human" || node.actor === "system" ? node.actor : "agent",
      actor_label: text(node.actor_label), summary: text(node.summary), facts: list(node.facts), sources: list(node.sources), depends_on: list(node.depends_on),
      assessment: {
        risk_level: text(assessment.risk_level), risk_title: text(assessment.risk_title), autonomy_level: text(assessment.autonomy_level), autonomy_title: text(assessment.autonomy_title),
        collaboration: text(assessment.collaboration), takeover_point: text(assessment.takeover_point), design_focus: text(assessment.design_focus), rules: list(assessment.rules),
        dimensions: assessment.dimensions.flatMap(entry => entry && typeof entry === "object"
          ? [{ key: text((entry as Record<string, unknown>).key), label: text((entry as Record<string, unknown>).label), finding: text((entry as Record<string, unknown>).finding), drives_level: (entry as Record<string, unknown>).drives_level === true }] : []),
      },
    });
  }
  const state = raw.state && typeof raw.state === "object" ? raw.state as Record<string, unknown> : {};
  const stateStatus = ["running", "waiting_human", "done", "failed", "stopped"].includes(text(state.status)) ? text(state.status) as WorkflowGraph["state"]["status"] : "running";
  return {
    mode: raw.mode === "office_action" ? "office_action" : "control_loop", nodes,
    edges: (Array.isArray(raw.edges) ? raw.edges : []).flatMap(edge => edge && typeof edge === "object" ? [{ source: text((edge as Record<string, unknown>).source), target: text((edge as Record<string, unknown>).target) }] : []),
    state: { status: stateStatus, label: text(state.label), can_interrupt: state.can_interrupt === true, agent_count: typeof state.agent_count === "number" ? state.agent_count : 1, delegated_count: typeof state.delegated_count === "number" ? state.delegated_count : 0 },
  };
}

const NODE_W = 156, NODE_H = 60, COL_GAP = 52, ROW_GAP = 22, PAD_TOP = 30, PAD_X = 8, PAD_BOTTOM = 10;

type Placed = { node: WorkflowNode; x: number; y: number };

function layout(graph: WorkflowGraph) {
  const incoming = new Map<string, string[]>();
  for (const edge of graph.edges) incoming.set(edge.target, [...(incoming.get(edge.target) ?? []), edge.source]);
  const depth = new Map<string, number>();
  const known = new Set(graph.nodes.map(node => node.node_id));
  const visit = (id: string, trail: Set<string>): number => {
    if (depth.has(id)) return depth.get(id)!;
    if (trail.has(id)) return 0;
    trail.add(id);
    const parents = (incoming.get(id) ?? []).filter(parent => known.has(parent));
    const value = parents.length ? Math.max(...parents.map(parent => visit(parent, trail))) + 1 : 0;
    trail.delete(id);
    depth.set(id, value);
    return value;
  };
  graph.nodes.forEach(node => visit(node.node_id, new Set()));
  const layers = new Map<number, WorkflowNode[]>();
  graph.nodes.forEach(node => layers.set(depth.get(node.node_id) ?? 0, [...(layers.get(depth.get(node.node_id) ?? 0) ?? []), node]));
  const layerCount = Math.max(...layers.keys()) + 1;
  const tallest = Math.max(...[...layers.values()].map(items => items.length));
  const innerHeight = tallest * NODE_H + (tallest - 1) * ROW_GAP;
  const placed: Placed[] = [];
  for (const [layer, items] of layers) {
    const blockHeight = items.length * NODE_H + (items.length - 1) * ROW_GAP;
    items.forEach((node, index) => placed.push({ node, x: PAD_X + layer * (NODE_W + COL_GAP), y: PAD_TOP + (innerHeight - blockHeight) / 2 + index * (NODE_H + ROW_GAP) }));
  }
  return { placed, width: PAD_X * 2 + layerCount * NODE_W + (layerCount - 1) * COL_GAP, height: PAD_TOP + innerHeight + PAD_BOTTOM };
}

const STATE_CLASS: Record<WorkflowGraph["state"]["status"], string> = { running: "is-running", waiting_human: "is-waiting", done: "is-done", failed: "is-failed", stopped: "is-failed" };

export function WorkflowTree({ graph, onInterrupt, interruptBusy = false, compact = false, title = "任务流程" }: {
  graph: WorkflowGraph; onInterrupt?: () => void; interruptBusy?: boolean; compact?: boolean; title?: string;
}) {
  const { placed, width, height } = useMemo(() => layout(graph), [graph]);
  const byId = useMemo(() => new Map(placed.map(item => [item.node.node_id, item])), [placed]);
  const [hover, setHover] = useState<{ id: string; rect: DOMRect } | null>(null);
  const [pinned, setPinned] = useState<{ id: string; rect: DOMRect } | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const root = useRef<HTMLElement | null>(null);
  const cardNode = pinned ?? hover;
  const card = cardNode ? graph.nodes.find(node => node.node_id === cardNode.id) : undefined;
  const detail = detailId ? graph.nodes.find(node => node.node_id === detailId) : undefined;

  const leave = () => { if (timer.current) clearTimeout(timer.current); timer.current = setTimeout(() => setHover(null), 140); };
  const enter = (id: string, element: HTMLElement) => { if (timer.current) clearTimeout(timer.current); setHover({ id, rect: element.getBoundingClientRect() }); };
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);
  useEffect(() => {
    if (!pinned) return;
    const close = (event: KeyboardEvent) => { if (event.key === "Escape") { setPinned(null); setHover(null); } };
    const outside = (event: MouseEvent) => { if (root.current && !root.current.contains(event.target as Node) && !(event.target as HTMLElement).closest?.(".wf-card")) setPinned(null); };
    window.addEventListener("keydown", close); window.addEventListener("mousedown", outside);
    return () => { window.removeEventListener("keydown", close); window.removeEventListener("mousedown", outside); };
  }, [pinned]);
  useEffect(() => { if (detailId && !graph.nodes.some(node => node.node_id === detailId)) setDetailId(null); }, [graph, detailId]);

  const cardStyle = cardNode ? (() => {
    const left = Math.min(Math.max(8, cardNode.rect.left + cardNode.rect.width / 2 - 150), (typeof window === "undefined" ? 1200 : window.innerWidth) - 308);
    const below = cardNode.rect.bottom + 8;
    const flip = typeof window !== "undefined" && below + 190 > window.innerHeight;
    return { left, top: flip ? Math.max(8, cardNode.rect.top - 8 - 176) : below } as const;
  })() : undefined;

  return <section ref={root} className={`wf${compact ? " is-compact" : ""}`} aria-label={title}>
    <header className="wf-head">
      <h3>{title}</h3>
      <div className="wf-head-right">
        <span className="wf-agents" title={graph.mode === "office_action" ? "固定规则直接办理，不调用大模型" : `${graph.state.agent_count} 个 Agent（含 ${graph.state.delegated_count} 个委派）`}>
          {Array.from({ length: Math.min(graph.state.agent_count, 6) }).map((_, index) => <IconRobot key={index} aria-hidden="true" />)}
          {graph.state.agent_count === 0 ? <em>固定规则</em> : <em>×{graph.state.agent_count}</em>}
        </span>
        <span className={`wf-state ${STATE_CLASS[graph.state.status]}`}>任务状态 · {graph.state.label}</span>
      </div>
    </header>
    <div className="wf-scroll">
      <div className="wf-canvas" style={{ width, height }}>
        <svg width={width} height={height} aria-hidden="true">
          <defs><marker id="wf-arrow" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L8 4L0 8z" fill="#9aa6b8" /></marker></defs>
          {graph.edges.map((edge, index) => {
            const from = byId.get(edge.source), to = byId.get(edge.target);
            if (!from || !to) return null;
            const x1 = from.x + NODE_W, y1 = from.y + NODE_H / 2, x2 = to.x, y2 = to.y + NODE_H / 2, mid = (x1 + x2) / 2;
            return <path key={index} d={`M${x1} ${y1} C${mid} ${y1} ${mid} ${y2} ${x2 - 2} ${y2}`} className={`wf-edge${from.node.status === "done" ? " is-done" : ""}`} markerEnd="url(#wf-arrow)" />;
          })}
        </svg>
        {placed.map(({ node, x, y }) => <div key={node.node_id} className="wf-slot" style={{ left: x, top: y, width: NODE_W, height: NODE_H }}>
          {node.status === "running" && <span className="wf-actor is-agent" title={node.actor_label}><IconRobot aria-hidden="true" /></span>}
          {node.status === "waiting_human" && <span className="wf-actor is-human" title="需要你处理"><IconUser aria-hidden="true" /></span>}
          <button type="button" className={`wf-node is-${node.status}`} data-node={node.node_id} aria-label={`${node.label}，${node.status_label}，风险等级 ${node.assessment.risk_level}`}
            aria-expanded={detailId === node.node_id}
            onMouseEnter={event => enter(node.node_id, event.currentTarget)} onMouseLeave={leave}
            onFocus={event => enter(node.node_id, event.currentTarget)} onBlur={leave}
            onClick={event => { const rect = event.currentTarget.getBoundingClientRect(); setPinned(current => current?.id === node.node_id ? null : { id: node.node_id, rect }); }}>
            <b className={`wf-risk level-${node.assessment.risk_level}`}>{node.assessment.risk_level}</b>
            <span className="wf-label">{node.label}</span>
            <small>{node.status_label}</small>
          </button>
        </div>)}
      </div>
    </div>
    {onInterrupt && graph.state.can_interrupt && <div className="wf-actions"><button type="button" className="wf-interrupt" disabled={interruptBusy} onClick={onInterrupt}><IconPlayerStop aria-hidden="true" />中断任务</button></div>}
    {card && cardStyle && <div className="wf-card" role="tooltip" style={cardStyle} onMouseEnter={() => { if (timer.current) clearTimeout(timer.current); }} onMouseLeave={leave}>
      <div className="wf-card-top"><strong>{card.label}</strong><span className={`wf-chip is-${card.status}`}>{card.status_label}</span></div>
      <div className="wf-card-risk"><b className={`wf-risk level-${card.assessment.risk_level}`}>{card.assessment.risk_level}</b><span>{card.assessment.risk_title} · {card.assessment.autonomy_level} {card.assessment.autonomy_title}</span></div>
      <p>{card.summary || card.assessment.collaboration}</p>
      <button type="button" onClick={() => { setDetailId(card.node_id); setPinned(null); setHover(null); }}>查看详情</button>
    </div>}
    {detail && <section className="wf-detail" aria-label={`${detail.label} 详情`}>
      <header>
        <div><strong>{detail.label}</strong><span className={`wf-chip is-${detail.status}`}>{detail.status_label}</span></div>
        <button type="button" aria-label="关闭详情" onClick={() => setDetailId(null)}><IconX aria-hidden="true" /></button>
      </header>
      <p className="wf-detail-level"><b className={`wf-risk level-${detail.assessment.risk_level}`}>{detail.assessment.risk_level}</b>{detail.assessment.risk_title}<span>自主程度 {detail.assessment.autonomy_level} · {detail.assessment.autonomy_title}</span></p>
      {detail.summary && <p>{detail.summary}</p>}
      <dl className="wf-collab">
        <div><dt>默认协作方式</dt><dd>{detail.assessment.collaboration}</dd></div>
        <div><dt>你接管的时点</dt><dd>{detail.assessment.takeover_point}</dd></div>
        <div><dt>设计重点</dt><dd>{detail.assessment.design_focus}</dd></div>
      </dl>
      <h4>八个维度怎么看这一步</h4>
      <ul className="wf-dims">{detail.assessment.dimensions.map(item => <li key={item.key} className={item.drives_level ? "is-driver" : ""}><b>{item.label}{item.drives_level && <em>决定等级</em>}</b><span>{item.finding}</span></li>)}</ul>
      {detail.facts.length > 0 && <><h4>执行信息</h4><ul className="wf-facts">{detail.facts.map((item, index) => <li key={index}>{item}</li>)}</ul></>}
      {detail.sources.length > 0 && <><h4>依据文件</h4><ul className="wf-facts">{detail.sources.map((item, index) => <li key={index}>{item}</li>)}</ul></>}
      <p className="wf-note">等级按操作类型取手册里的默认约定，维度只用来说明原因，不是打分得出。{detail.assessment.rules.length > 0 && <> 对应规则：{detail.assessment.rules.join("、")}。</>}</p>
    </section>}
  </section>;
}
