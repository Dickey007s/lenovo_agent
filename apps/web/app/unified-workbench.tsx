"use client";

import { type ReactNode, useEffect, useState } from "react";
import { IconAdjustments, IconChevronRight, IconClock, IconCube, IconFolder, IconLayoutSidebar, IconPlus, IconRefresh, IconSearch, IconX } from "@tabler/icons-react";
import type { HarnessRun } from "./harness-workbench";
import { officeTaskTitle } from "./task-journey";
import { projectTaskResponsibility } from "./task-responsibility";
import { useDemoMode } from "./demo-mode";
import "./unified-workbench.css";

export type WorkbenchSpace = "solo" | "team" | "copilot";
export const WORKBENCH_SPACES = [
  { id: "solo", label: "Demo 1 · 单任务协作" },
  { id: "team", label: "Demo 2 · 自适应执行" },
  { id: "copilot", label: "Demo 3 · 人机共驾" },
] as const;

export function runSpace(run: HarnessRun): WorkbenchSpace {
  if (run.office_action) return "copilot";
  return run.execution_policy === "automatic_readonly" || run.topology_admission?.mode === "adaptive_readonly_workers" || run.worker_runs.length > 0 ? "team" : "solo";
}

function taskStatus(run: HarnessRun) {
  const action = run.office_action;
  if (action) return ({ needs_input: "待补信息", awaiting_confirmation: "待你确认", awaiting_decision: "待你判断", deferred: "已暂缓", draft_ready: "草稿已保存", executed: "结果已记录", decided: "判断已记录", denied: "受限未执行", cancelled: "已取消", undone: "已撤销", stale: "需重新核对" } as Record<string, string>)[action.status] ?? "状态待核对";
  if (run.status === "completed") {
    const division = projectTaskResponsibility(run);
    if (division.businessBlocked) return "业务条件未通过";
    if (division.human.some(item => item.kind === "judgment")) return "待你判断";
    if (division.human.some(item => item.kind === "source_choice")) return "待核对依据";
    if (division.human.some(item => item.kind === "missing")) return "待补资料";
  }
  if (run.control_state === "paused" && !["completed", "failed", "stopped", "waiting_input"].includes(run.status)) return "已暂停";
  return ({ waiting_input: "待处理", completed: "已完成", failed: "执行失败", stopped: "已停止", running: "进行中", planning: "拆解任务", analyzing: "分析资料", queued: "排队中" } as Record<string, string>)[run.status] ?? (run.control_state === "paused" ? "已暂停" : "进行中");
}

function taskMode(run: HarnessRun) {
  if (run.office_action) return "固定规则事项";
  if (!run.topology_admission) return ["completed", "failed", "stopped"].includes(run.status) ? "执行方式未记录" : "执行方式待评估";
  return run.topology_admission.mode === "adaptive_readonly_workers" ? "多 Agent 协作" : run.topology_admission.mode === "fixed_workflow" ? "顺序执行" : "单 Agent 执行";
}

function taskTone(run: HarnessRun) {
  if (!run.office_action) {
    if (run.status !== "completed") return run.status;
    const division = projectTaskResponsibility(run);
    return division.businessBlocked ? "failed" : division.human.length ? "waiting_input" : run.status;
  }
  const status = run.office_action.status;
  if (status === "denied") return "failed";
  if (["needs_input", "awaiting_confirmation", "awaiting_decision", "stale"].includes(status)) return "waiting_input";
  return ["executed", "decided"].includes(status) ? "completed" : "neutral";
}

export function UnifiedWorkbench({ space, onSpace, run, runs, loading, locked, historyError, onSelect, onNew, onRefresh, files, children, onHistory, activity, footer, batchActive }: {
  space: WorkbenchSpace; onSpace: (space: WorkbenchSpace) => void;
  run: HarnessRun | null; runs: HarnessRun[]; loading: boolean; locked: boolean; historyError?: string;
  onSelect: (run: HarnessRun) => void; onNew: () => void; onRefresh: () => void;
  files: ReactNode; children: ReactNode; onHistory: () => void; activity?: ReactNode; footer?: ReactNode;
  batchActive?: boolean;
}) {
  const [filter, setFilter] = useState("");
  const [navigationOpen, setNavigationOpen] = useState(false);
  const [simulated, setSimulated] = useDemoMode();
  useEffect(() => { setFilter(""); }, [space]);
  // This is a recent-task projection, never a fabricated execution queue.
  const latest = new Map<string, HarnessRun>();
  for (const item of runs) {
    const previous = latest.get(item.task_id);
    if (!previous || item.run_sequence > previous.run_sequence) latest.set(item.task_id, item);
  }
  if (run && !latest.has(run.task_id)) latest.set(run.task_id, run);
  const roots = new Map<string, HarnessRun>();
  for (const item of runs) if (item.run_sequence === 1) roots.set(item.task_id, item);
  const visible = [...latest.values()].filter(item => (runSpace(item) === space || item.run_id === run?.run_id) && (item.office_action?.input.title ?? item.instruction).toLowerCase().includes(filter.toLowerCase()));
  const label = WORKBENCH_SPACES.find(item => item.id === space)!.label;
  return <main className={`unified-workbench${navigationOpen ? " is-navigation-open" : ""}`}>
    <aside className="unified-rail" aria-label="工作区导航">
      <div className="unified-brand"><IconCube aria-hidden="true"/><strong>办公 Agent</strong></div>
      <button className="unified-new" onClick={onNew} disabled={locked}><IconPlus aria-hidden="true"/>新建任务</button>
      <p className="unified-label">工作区</p>
      <nav aria-label="演示工作区">{WORKBENCH_SPACES.map(item => <button key={item.id} aria-current={space === item.id ? "page" : undefined} disabled={locked} onClick={() => { onSpace(item.id); setNavigationOpen(false); }}><IconFolder aria-hidden="true"/><span>{item.label}</span></button>)}</nav>
      <label className={`unified-sim${simulated ? " is-on" : ""}`} title="打开后，新提交的任务用本地规则模拟拆分与分析，不调用模型，几秒内出结果；内容只是按关键词摘出原文，不是真实分析。">
        <input type="checkbox" role="switch" checked={simulated} disabled={locked} onChange={event => setSimulated(event.target.checked)}/>
        <span><strong>演示模式</strong><small>{simulated ? "已开启 · 不调用模型" : "关闭 · 调用真实模型"}</small></span>
      </label>
      <div className="unified-materials">{files}</div>
      <div className="unified-rail-bottom"><button onClick={onHistory} disabled={locked}><IconClock aria-hidden="true"/>历史记录</button><a href="/agent-capabilities" aria-disabled={locked || undefined} onClick={event => { if (locked) event.preventDefault(); }}><IconAdjustments aria-hidden="true"/>完整能力记录</a></div>
    </aside>
    <aside className="unified-tasks" aria-label="最近任务">
      <header><h2>任务</h2><button title="新建任务" aria-label="新建任务草稿" onClick={onNew} disabled={locked}><IconPlus aria-hidden="true"/></button><button title="刷新任务" aria-label="刷新任务" onClick={onRefresh} disabled={loading || locked}><IconRefresh aria-hidden="true"/></button></header>
      <label className="unified-task-search"><IconSearch aria-hidden="true"/><input placeholder="搜索最近任务" aria-label="搜索最近任务" value={filter} onChange={event => setFilter(event.target.value)}/></label>
      {!run && !filter && <div className="unified-task-draft"><strong>{space === "team" ? "待办列表" : "新任务"}</strong><span>{space === "team" ? "分别规划，独立执行" : "尚未提交"}</span></div>}
      <div className="unified-task-items">{visible.map(item => <button key={item.task_id} className={item.task_id === run?.task_id ? "is-selected" : ""} disabled={locked} onClick={() => { onSelect(item); setNavigationOpen(false); }} aria-current={item.task_id === run?.task_id ? "true" : undefined}><strong>{item.office_action?.input.title ?? officeTaskTitle(roots.get(item.task_id)?.instruction ?? item.instruction)}</strong><span>{item.run_sequence > 1 ? `${item.run_sequence} 段处理 · ` : ""}{taskMode(item)}</span><small className={`state-${taskTone(item)}`}><i/>{taskStatus(item)}</small></button>)}</div>
      {historyError ? <p className="unified-list-note" role="alert">{historyError}</p> : loading ? <p className="unified-list-note" role="status">正在读取任务…</p> : visible.length === 0 && <p className="unified-list-note">{filter ? "没有匹配的任务" : "暂无已提交任务"}</p>}
      <p className="unified-list-scope">最近 20 次运行 · 按任务归组</p>
    </aside>
    <section className="unified-main" aria-label="任务工作区">
      <header className="unified-topbar"><button className="unified-navigation-toggle" aria-label={navigationOpen ? "收起工作区导航" : "展开工作区导航"} aria-expanded={navigationOpen} onClick={() => setNavigationOpen(!navigationOpen)}>{navigationOpen ? <IconX/> : <IconLayoutSidebar/>}</button><span>{label}</span><IconChevronRight aria-hidden="true"/><strong>{run ? "任务详情" : space === "team" && batchActive ? "本次待办" : "新任务"}</strong><div className="unified-topbar-actions">{activity}</div></header>
      <div className="unified-main-scroll">{children}</div>
      {footer && <footer className="unified-delivery">{footer}</footer>}
    </section>
  </main>;
}
