"use client";

import { useState } from "react";
import { IconCheck, IconCornerDownRight, IconPlayerPlay, IconSend, IconUser } from "@tabler/icons-react";
import type { HarnessRun } from "./harness-workbench";
import { projectTaskResponsibility } from "./task-responsibility";
import type { WorkflowGraph, WorkflowNode } from "./workflow-tree";
import "./task-board.css";

type Finding = NonNullable<HarnessRun["result"]>["findings"][number];

const KIND_ACTION: Record<string, string> = { judgment: "查看问题与选项", source_choice: "核对依据", missing: "补充资料", start: "确认并启动" };

// One place for "tell the agent something new". The demo records the request only; it does not
// change a running task yet, and the page says so.
export function TaskSteer({ disabled = false, running = false }: { disabled?: boolean; running?: boolean }) {
  const [text, setText] = useState("");
  const [notes, setNotes] = useState<string[]>([]);
  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    setNotes(current => [...current, value].slice(-3));
    setText("");
  };
  return <section className="steer" aria-label="修改任务要求">
    <label htmlFor="task-steer-input">{running ? "任务进行中，有新要求或想调整方向？" : "想补充新要求或调整方向？"}</label>
    <div>
      <input id="task-steer-input" value={text} disabled={disabled} maxLength={300} placeholder="例如：先不要处理第 2 项，改成只列出缺口"
        onChange={event => setText(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.nativeEvent.isComposing) submit(); }} />
      <button type="button" disabled={disabled || !text.trim()} onClick={submit}><IconSend aria-hidden="true" />提交</button>
    </div>
    {notes.length > 0 && <ul aria-live="polite">{notes.map((note, index) => <li key={index}><IconCheck aria-hidden="true" /><span>已记录：{note}<em>演示中暂不改变正在执行的任务</em></span></li>)}</ul>}
  </section>;
}

function findingFor(run: HarnessRun, node: WorkflowNode): Finding | undefined {
  const findings = run.result?.findings ?? run.artifact_versions.at(-1)?.findings ?? [];
  const request = run.decision_requests.find(item => item.request_id === node.ref_id);
  return findings.find(item => item.finding_id && (item.finding_id === node.ref_id || item.finding_id === request?.finding_id));
}

// Same two questions on every page: what is waiting for me, and what has the system finished.
export function TaskBoard({ run, graph, onFocus, onFinding, onEvidence, onConfirm, onStart, busy = false }: {
  run: HarnessRun; graph: WorkflowGraph;
  onFocus: (nodeId: string | null) => void; onFinding: (finding: Finding) => void; onEvidence: () => void; onConfirm?: () => void; onStart?: () => void; busy?: boolean;
}) {
  const office = graph.mode === "office_action";
  const waiting = graph.nodes.filter(node => node.status === "waiting_human" && (office || node.kind === "human_gate" || node.kind === "work_unit"));
  const handled = office
    ? graph.nodes.filter(node => node.status === "done" || node.status === "failed")
    : [];
  const system = office ? [] : projectTaskResponsibility(run).system;
  const active = graph.state.status === "running";

  return <section className="board" aria-label="任务看板">
    {run.simulated && <p className="board-sim" role="note"><strong>演示模式</strong>未调用模型。拆分与摘录由本地规则生成，只是按关键词摘出原文，不代表真实分析结论。</p>}
    <div className="board-col board-human">
      <h4><IconUser aria-hidden="true" />现在要你做的事<span>{waiting.length} 项</span></h4>
      {waiting.length ? <ul>{waiting.map(node => {
        const finding = node.ref_kind === "judgment" ? findingFor(run, node) : undefined;
        return <li key={node.node_id} onMouseEnter={() => onFocus(node.node_id)} onMouseLeave={() => onFocus(null)}>
          <strong>{node.label}</strong>
          <p>{node.summary || node.assessment.collaboration}</p>
          <div className="board-actions">
            {office
              ? onConfirm && <button type="button" onClick={onConfirm}>去下方确认<IconCornerDownRight aria-hidden="true" /></button>
              : node.ref_kind === "start"
                ? <button type="button" disabled={busy || !onStart} onClick={onStart}><IconPlayerPlay aria-hidden="true" />{busy ? "正在启动" : KIND_ACTION.start}</button>
                : <button type="button" onClick={() => finding ? onFinding(finding) : onEvidence()}>{KIND_ACTION[node.ref_kind ?? "judgment"] ?? "处理"}</button>}
            <span>{node.assessment.risk_level} · {node.status_label}</span>
          </div>
        </li>;
      })}</ul> : <p className="board-empty">{active ? "Agent 正在处理，需要你时会在这里提示。" : "目前没有需要你处理的事项。"}</p>}
      {!office && waiting.length > 0 && <small>{waiting.some(node => node.ref_kind === "start") ? "确认之前不会调用分析模型，也不会改动任何文件。" : "其余分支不会等你，继续往下推进。"}</small>}
    </div>
    <div className="board-col board-system">
      <h4><IconCheck aria-hidden="true" />系统已处理<span>{office ? handled.length : system.length} 项</span></h4>
      {(office ? handled.length : system.length) ? <ul>
        {office
          ? handled.map(node => <li key={node.node_id} onMouseEnter={() => onFocus(node.node_id)} onMouseLeave={() => onFocus(null)}><strong>{node.label}</strong><p>{node.summary}</p></li>)
          : system.slice(0, 3).map(item => <li key={item.id}><strong>{item.title}</strong><p>{item.reason}</p></li>)}
      </ul> : <p className="board-empty">还没有系统完成的部分。</p>}
      {!office && system.length > 3 && <details><summary>其余 {system.length - 3} 项</summary><ul>{system.slice(3).map(item => <li key={item.id}><strong>{item.title}</strong><p>{item.reason}</p></li>)}</ul></details>}
    </div>
  </section>;
}
