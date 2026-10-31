"use client";

import { useEffect, useRef, useState } from "react";
import { IconArrowsExchange, IconCheck, IconChevronDown, IconFileText, IconChevronRight, IconLoader2, IconPlayerPlay, IconRobot, IconWand } from "@tabler/icons-react";
import type { HarnessRun } from "./harness-workbench";
import { WorkflowTree } from "./workflow-tree";
import { todoSummary } from "./todo-summary";
import { simulatedBody } from "./demo-mode";

export const OFFICE_TODO_SETS = [
  { name: "日常办公", instructions: [
    "整理招聘要求。\n阅读《文本评测岗位JD.docx》，摘出一项明确的岗位要求，形成招聘核对要点。引用一段完整、连续且能唯一定位的原文。只整理岗位要求，不评判候选人。",
    "核对一笔往来账。\n阅读《2026往来明细.xlsx》，找出绵阳长城发展融资担保有限公司的期初余额、本期借方发生额和期末余额，形成一条账面核对记录。引用该公司完整连续的表格原文。不将余额视为已收款，不推断逾期。",
    "准备入职与招聘交接清单。\n帮行政同事整理全员通用办公软件，帮招聘同事整理外卖商户BD岗位要求。资料在入职物资权限软件分配和对应岗位说明中。保留原文依据，不开通权限、不作录用决定。",
  ] },
  { name: "人事资料整理", instructions: [
    "整理通用办公软件清单。\n阅读《入职物资权限软件分配.pdf》，只摘出全体员工通用的软件配置，形成一条清单，引用完整连续原文。不判断个人例外，不实际安装软件。",
    "整理商务岗位要求。\n阅读《外卖商户BD岗位JD.docx》，摘出一项明确的岗位要求，形成一条招聘核对要点。引用完整连续原文，不评判候选人。",
    "准备两个岗位的招聘要点。\n招聘同事要查阅文本评测岗位和外卖商户BD岗位的任职要求，请整理要点并保留原文依据。不比较候选人，也不要把不同岗位要求合成共同门槛。",
  ] },
  { name: "办公准备 · 自主分工", instructions: [
    "准备今日办公摘要。\n行政同事需要《3月20日-4月20日入职时间表.csv》中吴嘉木的入职日期、岗位和特殊备注；招聘同事需要《文本评测岗位JD.docx》的必备条件，本摘要不包含加分项；财务同事需要《2026往来明细.xlsx》中绵阳长城发展融资担保有限公司的其他应收往来这一行的期初余额、本期借贷方发生额、期末余额和方向。分主题整理页面摘要，附各自原文。仅摘录已写明的信息，空白字段保留为空白，不推断付款、核销、逾期或风险，不执行人事或财务操作。",
    "整理商务岗位要求。\n从《外卖商户BD岗位JD.docx》摘录学历和沟通要求，保留优秀者可放宽等原文条件。形成便于招聘同事查阅的两项要点，附依据，不额外定义硬性门槛，不评价候选人。",
    "核对一笔往来账。\n从《2026往来明细.xlsx》摘录绵阳长城发展融资担保有限公司的其他应收往来这一行，列出期初余额、本期借方、本期贷方、期末余额和方向，附原始行。只整理这一科目，空白字段保留为空白，不推断付款、核销、逾期或风险，不修改文件。",
  ] },
  { name: "蜂群 · 一波波并行", instructions: [
    "本周办公盘点。请分别核对以下要求：\n1. 阅读《3月20日-4月20日入职时间表.csv》，摘出吴嘉木的入职日期、岗位和特殊备注，附原文。\n2. 阅读《入职物资权限软件分配.pdf》，摘出全体员工通用的软件配置，附原文。\n3. 阅读《文本评测岗位JD.docx》，摘出全部必备条件，附原文。\n4. 阅读《外卖商户BD岗位JD.docx》，摘出学历和沟通要求，附原文。\n5. 阅读《2026往来明细.xlsx》，摘出绵阳长城发展融资担保有限公司其他应收往来的期初余额、本期借贷方发生额和期末余额，附原始行。\n6. 在以上五项都完成后，汇总成一份本周办公要点，逐项注明出处。\n只在页面整理，不修改原文件。",
  ] },
];
const DEFAULT_TODO_SET = 2;
export const BATCH_EXAMPLES = OFFICE_TODO_SETS[DEFAULT_TODO_SET].instructions;

type Entry = { instruction: string; key: string; runId?: string; error?: string; source?: string };

// To-dos split from meeting minutes. They only pre-fill the list; nothing starts until the user confirms.
export type MinutesSeed = {
  id: number; method: "model" | "rules"; summary: string;
  todos: { title: string; instruction: string; source_quote: string }[];
};
const entriesFromSeed = (seed?: MinutesSeed | null): Entry[] =>
  seed?.todos.length ? seed.todos.map(todo => ({ instruction: todo.instruction, key: "", source: todo.source_quote })) : EMPTY_ENTRIES();

// A fresh to-do list starts blank; presets are only filled in when the user asks for them.
const EMPTY_ENTRIES = (): Entry[] => BATCH_EXAMPLES.map(() => ({ instruction: "", key: "" }));

export function TodoBatch({ apiBase, headers, normalize, runs, onCreated, onOpen, onLock, onSwitchSolo, seed }: {
  apiBase: string; headers: Record<string, string>; normalize: (value: unknown) => HarnessRun | null;
  runs: HarnessRun[]; onCreated: (run: HarnessRun) => void; onOpen: (run: HarnessRun) => void;
  onLock: (locked: boolean) => void; onSwitchSolo?: () => void; seed?: MinutesSeed | null;
}) {
  const [entries, setEntries] = useState<Entry[]>(() => entriesFromSeed(seed));
  const [busy, setBusy] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [exampleSet, setExampleSet] = useState(DEFAULT_TODO_SET);
  const [openTrees, setOpenTrees] = useState<Set<number>>(new Set());
  const pending = useRef(false);
  const seededId = useRef<number | null>(seed?.id ?? null);
  useEffect(() => {
    if (!seed || seededId.current === seed.id || submitted) return;
    seededId.current = seed.id;
    setEntries(entriesFromSeed(seed));
  }, [seed, submitted]);
  const unknown = entries.some(entry => Boolean(entry.error));
  useEffect(() => { onLock(busy || unknown); }, [busy, unknown, onLock]);
  useEffect(() => () => onLock(false), [onLock]);

  async function start() {
    if (pending.current) return;
    pending.current = true;
    setBusy(true);
    setSubmitted(true);
    const next = entries.map(entry => ({ ...entry, key: entry.key || crypto.randomUUID() }));
    setEntries(next);
    // Each accepted POST starts its own server task immediately. The next POST
    // does not wait for that task's model work; retries retain the exact payload.
    for (let index = 0; index < next.length; index++) {
      if (next[index].runId) continue;
      try {
        const response = await fetch(`${apiBase}/v1/harness/runs`, {
          method: "POST", headers, signal: AbortSignal.timeout(20000),
          body: JSON.stringify({ instruction: next[index].instruction, idempotency_key: next[index].key,
            output_preference: "analysis_only", execution_policy: "automatic_readonly", ...simulatedBody(),
            loop: { max_rounds: 3, max_files_per_round: 8, max_model_calls: 8, deadline_seconds: 600 } }),
        });
        if (!response.ok) throw new Error(`启动未确认（HTTP ${response.status}）`);
        const value = normalize((await response.json()).run);
        if (!value) throw new Error("启动回执无法读取");
        next[index] = { ...next[index], runId: value.run_id, error: undefined };
        onCreated(value);
      } catch (error) {
        next[index] = { ...next[index], error: error instanceof Error ? error.message : "启动结果未知" };
      }
      setEntries(next.map(entry => ({ ...entry })));
    }
    pending.current = false;
    setBusy(false);
  }

  const completedCount = entries.filter(entry => {
    const run = runs.find(item => item.run_id === entry.runId);
    return run && todoSummary(run).complete;
  }).length;
  return <section className="todo-batch" aria-label="多任务待办">
    <header><div><span>只读分析</span><div className="todo-title-row"><h1>多任务待办</h1>{!submitted && onSwitchSolo && <button type="button" className="mode-switch" disabled={busy || unknown} onClick={onSwitchSolo} title="切换到单任务（Demo 1）"><IconArrowsExchange aria-hidden="true"/>切换单任务模式</button>}</div></div><span className="todo-total">{submitted ? `${completedCount} / ${entries.length} 项已完成` : `${entries.length} 项待办`}</span>{!submitted && <div className="todo-preset"><label>待办示例<select aria-label="待办示例" value={exampleSet} onChange={event => setExampleSet(Number(event.target.value))}>{OFFICE_TODO_SETS.map((set, index) => <option key={set.name} value={index}>{set.name}</option>)}</select></label><button type="button" className="todo-fill" disabled={busy} onClick={() => setEntries(OFFICE_TODO_SETS[exampleSet].instructions.map(instruction => ({ instruction, key: "" })))}><IconWand aria-hidden="true"/>整理待办</button></div>}</header>
    {seed && !submitted && seededId.current === seed.id && <p className="todo-seed-note" role="status"><IconFileText aria-hidden="true"/><span><b>已从会议纪要拆出 {seed.todos.length} 项待办</b>（{seed.method === "model" ? "模型拆分" : "按编号拆分"}）。请逐项核对、必要时修改，确认后再点「开始全部待办」。</span></p>}
    <ol>{entries.map((entry, index) => {
      const run = runs.find(item => item.run_id === entry.runId);
      const summary = run ? todoSummary(run) : null;
      const completed = summary?.complete;
      const status = entry.error || (!entry.runId ? "尚未启动" : !summary ? "已受理，正在读取进展" : summary.status);
      const title = entry.instruction.split(/[。\n]/)[0].slice(0, 60) || `待办 ${index + 1}`;
      return <li key={index}>
        <div className="todo-number">{completed ? <IconCheck aria-hidden="true"/> : index + 1}</div>
        <div className="todo-body">{submitted ? <div className="todo-row-head">
          <button type="button" className="todo-tree-toggle" aria-expanded={openTrees.has(index)} aria-controls={`todo-tree-${index}`} disabled={!run?.workflow} title={run?.workflow ? "展开这项待办的流程" : "流程生成中"}
            onClick={() => setOpenTrees(current => { const next = new Set(current); if (next.has(index)) next.delete(index); else next.add(index); return next; })}><IconChevronDown aria-hidden="true"/><h2>{title}</h2></button>
          {run?.workflow && <span className="todo-agents" aria-label={`委派了 ${run.workflow.state.delegated_count} 个 Agent，共 ${run.workflow.state.agent_count} 个`} title={`主 Agent + ${run.workflow.state.delegated_count} 个委派 Agent`}>{Array.from({ length: Math.min(run.workflow.state.agent_count, 6) }).map((_, position) => <IconRobot key={position} aria-hidden="true"/>)}<em>×{run.workflow.state.agent_count}</em></span>}
        </div> : <label htmlFor={`todo-${index}`}>待办 {index + 1} · {title}</label>}
          {submitted && run?.workflow && openTrees.has(index) && <div id={`todo-tree-${index}`} className="todo-tree"><WorkflowTree graph={run.workflow} compact title="这项待办的流程"/></div>}
          {!submitted && entry.source && <details className="todo-source"><summary>纪要原句</summary><blockquote>{entry.source}</blockquote></details>}
          {!submitted && <textarea id={`todo-${index}`} aria-label={`待办 ${index + 1}`} placeholder="输入这一项待办，或点击上方「整理待办」填入预设示例" value={entry.instruction} maxLength={2000} onChange={event => setEntries(current => current.map((item, position) => position === index ? { ...item, instruction: event.target.value } : item))}/>}
          {submitted && <div className="todo-receipt"><span className={completed ? "is-complete" : entry.error || summary?.concerns.length || run?.status === "waiting_input" ? "is-waiting" : ""}>{status}{completed && summary ? ` · ${summary.findings.length} 条分析` : ""}</span><span>{run?.workflow?.swarm && run.workflow.state.delegated_count > 0 ? `蜂群 · ${run.workflow.state.delegated_count} 个子 Agent` : run?.topology_admission?.mode === "adaptive_readonly_workers" ? "多 Agent 协作" : run?.topology_admission ? "单 Agent 执行" : "评估执行方式"}</span>{run && <button disabled={busy || unknown} onClick={() => onOpen(run)}>查看任务<IconChevronRight aria-hidden="true"/></button>}</div>}
          {summary && <div className="todo-outcome">{!summary.findings.length && <strong className="is-empty">尚无已核对的分析</strong>}{summary.preview.slice(0, 1).map(item => <p key={item.id}>{item.finding?.fact_summary || item.title}</p>)}{summary.findings.length > 1 && <details className="todo-more-results"><summary>其余 {summary.findings.length - 1} 条分析</summary>{summary.findings.filter(item => item.id !== summary.preview[0]?.id).map(item => <p key={item.id}><b>{item.title}</b><br/>{item.finding?.fact_summary || item.finding?.detail}</p>)}</details>}{summary.concerns.length > 0 && <div className="todo-unfinished"><strong>未完成</strong><ul>{summary.concerns.map((text, i) => <li key={i}>{text}</li>)}</ul></div>}</div>}
          {submitted && <details className="todo-instruction"><summary>指令与执行记录</summary><p className="todo-original">{entry.instruction}</p>{run?.topology_admission && <><strong>分工依据</strong><ul>{run.topology_admission.reasons.map((reason, i) => <li key={i}>{reason}</li>)}</ul><p>{summary?.routing}</p><p>已用 {run.budget.model_calls_used} 次模型调用，上限 {run.budget.max_model_calls} 次</p></>}</details>}
          {entry.error && <p role="alert">本项内容已锁定。重试使用原请求，不重复创建已受理任务。</p>}
        </div>
      </li>;
    })}</ol>
    <footer><details className="todo-limits"><summary>运行范围与用量</summary><p>每项最多 8 次模型调用、10 分钟；协作时每波最多 3 个只读 Agent。只生成分析，不修改原文件或执行外部动作。</p></details>{(!submitted || unknown) && <button className="todo-start" disabled={busy || entries.some(entry => entry.instruction.trim().length < 3)} onClick={() => void start()}>{busy ? <IconLoader2 aria-hidden="true"/> : <IconPlayerPlay aria-hidden="true"/>}{busy ? "正在提交待办" : unknown ? "重试未确认的启动" : "开始全部待办"}</button>}</footer>
  </section>;
}
