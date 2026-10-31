"use client";

import { useEffect, useRef, useState } from "react";
import { IconCheck, IconCornerDownRight, IconFileDescription, IconPlayerPlay, IconSend, IconUser, IconX } from "@tabler/icons-react";
import type { HarnessFile, HarnessRun } from "./harness-workbench";
import { projectTaskResponsibility } from "./task-responsibility";
import type { WorkflowGraph, WorkflowNode } from "./workflow-tree";
import "./task-board.css";

type Finding = NonNullable<HarnessRun["result"]>["findings"][number];

const KIND_ACTION: Record<string, string> = { judgment: "查看问题与选项", source_choice: "核对依据", missing: "补充资料", start: "确认并启动" };

export type SteerRequest = { nonce: number; subject: string };

const stemOf = (label: string) => (label.includes(".") ? label.slice(0, label.lastIndexOf(".")) : label);

// One place for "tell the agent something new". Typed text is only recorded in the demo and does not
// change a running task. Supplying a library file for a missing source is real: it opens a follow-up
// branch on the same task, so the paused step can finish.
export function TaskSteer({ disabled = false, running = false, files = [], request = null, canSupply = false, onSupply }: {
  disabled?: boolean; running?: boolean; files?: HarnessFile[]; request?: SteerRequest | null; canSupply?: boolean;
  onSupply?: (instruction: string) => Promise<boolean>;
}) {
  const [text, setText] = useState("");
  const [notes, setNotes] = useState<string[]>([]);
  const [subject, setSubject] = useState<string | null>(null);
  const [picked, setPicked] = useState<HarnessFile | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const sectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!request) return;
    setSubject(request.subject); setPicked(null); setQuery(""); setFailed("");
    setText(`为「${request.subject}」补充资料`);
    sectionRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    inputRef.current?.focus();
  }, [request]);

  const matches = files
    .filter(file => !query.trim() || `${file.display_label} ${file.display_path}`.toLocaleLowerCase("zh-CN").includes(query.trim().toLocaleLowerCase("zh-CN")))
    .slice(0, 8);
  const supplying = Boolean(subject);
  const submit = async () => {
    const value = text.trim();
    if (disabled || busy) return;
    if (supplying && picked && onSupply && canSupply) {
      setBusy(true); setFailed("");
      const ok = await onSupply(`补充资料：用《${stemOf(picked.display_label)}》核对「${subject}」，说明能否据此印证这一项。${value ? `\n用户补充：${value}` : ""}`);
      setBusy(false);
      if (ok) { setSubject(null); setPicked(null); setText(""); setQuery(""); } else setFailed("没有提交成功，请重试。");
      return;
    }
    if (!value) return;
    setNotes(current => [...current, value].slice(-3));
    setText("");
  };
  const canSubmit = supplying ? Boolean(picked) && canSupply && !busy : Boolean(text.trim());
  return <section className="steer" aria-label="修改任务要求" ref={sectionRef}>
    <label htmlFor="task-steer-input">{running ? "任务进行中，有新要求或想调整方向？" : "想补充新要求或调整方向？"}</label>
    <div>
      <input id="task-steer-input" ref={inputRef} value={text} disabled={disabled || busy} maxLength={300} placeholder="例如：先不要处理第 2 项，改成只列出缺口"
        onChange={event => setText(event.target.value)} onKeyDown={event => { if (event.key === "Enter" && !event.nativeEvent.isComposing) void submit(); }} />
      <button type="button" disabled={disabled || !canSubmit} onClick={() => void submit()}><IconSend aria-hidden="true" />{busy ? "正在提交" : supplying ? "补充并继续" : "提交"}</button>
    </div>
    {supplying && <div className="steer-supply" role="group" aria-label="补充资料">
      <p>为「{subject}」从资料库选一份资料{!canSupply && "（任务结束后才能继续）"}。资料只读，不会被修改。</p>
      {picked
        ? <span className="steer-picked"><IconFileDescription aria-hidden="true" />{picked.display_label}<button type="button" aria-label="取消选择" onClick={() => setPicked(null)}><IconX aria-hidden="true" /></button></span>
        : <>
          <input aria-label="搜索资料库" value={query} placeholder="搜索资料库文件名" onChange={event => setQuery(event.target.value)} />
          <ul>{matches.map(file => <li key={file.file_ref}><button type="button" onClick={() => setPicked(file)}><IconFileDescription aria-hidden="true" />{file.display_label}</button></li>)}
            {!matches.length && <li className="steer-none">没有匹配的文件</li>}</ul>
        </>}
      <button type="button" className="steer-cancel" onClick={() => { setSubject(null); setPicked(null); setText(""); }}>不补了</button>
      {failed && <em role="alert">{failed}</em>}
    </div>}
    {notes.length > 0 && <ul aria-live="polite">{notes.map((note, index) => <li key={index}><IconCheck aria-hidden="true" /><span>已记录：{note}<em>演示中暂不改变正在执行的任务</em></span></li>)}</ul>}
  </section>;
}

function findingFor(run: HarnessRun, node: WorkflowNode): Finding | undefined {
  const findings = run.result?.findings ?? run.artifact_versions.at(-1)?.findings ?? [];
  const request = run.decision_requests.find(item => item.request_id === node.ref_id);
  return findings.find(item => item.finding_id && (item.finding_id === node.ref_id || item.finding_id === request?.finding_id));
}

// Same two questions on every page: what is waiting for me, and what has the system finished.
export function TaskBoard({ run, graph, onFocus, onFinding, onEvidence, onConfirm, onStart, onSupply, busy = false }: {
  run: HarnessRun; graph: WorkflowGraph;
  onFocus: (nodeId: string | null) => void; onFinding: (finding: Finding) => void; onEvidence: () => void; onConfirm?: () => void; onStart?: () => void; onSupply?: (node: WorkflowNode) => void; busy?: boolean;
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
                : node.ref_kind === "missing" && onSupply
                  ? <button type="button" onClick={() => onSupply(node)}>{KIND_ACTION.missing}</button>
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
