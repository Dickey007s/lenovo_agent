"use client";

import {
  CSSProperties,
  FormEvent,
  Fragment,
  KeyboardEvent,
  PointerEvent as ReactPointerEvent,
  ReactNode,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type { TaskEvent, TaskEventType, TaskSnapshot } from "./task-types";
import { TaskArtifactWorkspace } from "./task-artifact-workspace";
import { TaskRuntimePanel, type ControlIntent } from "./task-runtime-panel";

type ViewId = "mail" | "document" | "quote" | "tasks" | "calendar" | "expense" | "crm" | "audit";
type WorkspaceKind = Exclude<ViewId, "audit">;
type TaskViewMode = "runtime" | "manual";

type ChatMessage = {
  message_id: string;
  role: "user" | "assistant";
  content: string;
  status: "streaming" | "completed" | "failed";
};

type SourceReference = {
  source_id: string;
  label: string;
  system: string;
  excerpt: string;
  permission: string;
  updated_at: string;
};

type WorkspaceArtifact = {
  artifact_id: string;
  kind: WorkspaceKind;
  title: string;
  content: Record<string, unknown>;
  sources: SourceReference[];
  linked_action_id: string | null;
  linked_run_id: string | null;
  requires_recheck: boolean;
  change_history: { actor?: string; action?: string; time?: string }[];
};

type CapabilityDecision = { verdict: "allow" | "blocked" | "deny"; constraints: string[] };

type RunSnapshot = {
  run_id: string;
  trace_id: string;
  user_message: string;
  status: string;
  action: {
    action_id: string;
    action_type: string;
    capability: string;
    target_scope: string;
    recipients: string[];
    resources: string[];
    source_refs: string[];
    parameters: Record<string, unknown>;
  };
  risk: { risk_level: string; reason_codes: string[] };
  control_plan: {
    status: string;
    capabilities: Record<string, CapabilityDecision>;
    missing_requirements: string[];
    required_approvals: string[];
    reason_codes: string[];
    panel: { type: string; message: string };
  };
  permit: null | { permit_id: string; expires_at: string };
  tool_result: null | { execution_id: string; simulator: string; status: string; output: Record<string, unknown> };
};

type AuditEvent = {
  sequence: number;
  event_type: string;
  occurred_at: string;
  payload: Record<string, unknown>;
};

type EvidenceDefinition = {
  requirement: string;
  label: string;
  description: string;
  resolved_by: string;
  user_action: string;
  input_type: string;
  options: { value: string; label: string }[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010";
const TASK_MUTATION_SESSION_KEY = "office-agent.pending-task-mutation.v1";
const REQUEST_HEADERS = { "Content-Type": "application/json", "X-User-Id": "demo_user", "X-User-Roles": "current_user,sales_manager" };
const EVENT_TYPES = ["RUN_CREATED", "ACTION_PARSED", "EVIDENCE_SUBMITTED", "APPROVAL_RECORDED", "CONTROL_PLAN_UPDATED", "ACTION_INVALIDATED", "PERMIT_ISSUED", "TOOL_EXECUTED", "TAMPER_BLOCKED"];
const TASK_EVENT_TYPES: TaskEventType[] = [
  "TASK_CREATED", "TASK_RESTORED", "TASK_STATUS_CHANGED", "TASK_PHASE_CHANGED",
  "BRANCH_STATUS_CHANGED", "LOOP_STEP_STARTED", "LOOP_STEP_COMPLETED",
  "ARTIFACT_VERSION_CREATED", "VERIFICATION_RECORDED", "CONFLICT_OPENED",
  "CONFLICT_RESOLVED", "CONTROL_ACCEPTED", "CONTROL_APPLIED", "CONTROL_REJECTED",
  "BUDGET_UPDATED", "CHECKPOINT_COMMITTED", "TASK_COMMITTED", "TASK_FAILED",
];
const TASK_STATUS_LABELS: Record<TaskSnapshot["status"], string> = {
  ready: "等待启动", running: "运行中", waiting_input: "等待你的决定", paused: "已暂停",
  taken_over: "由你接管", verifying: "正在验证", committed: "已验证并提交",
  failed: "任务失败", cancelled: "已取消",
};
const TASK_PHASE_LABELS: Record<TaskSnapshot["phase"], string> = {
  contract: "任务契约", observe: "读取来源", plan: "规划分支", act: "生成工件",
  verify: "验证证据", commit: "提交结果",
};
const EVENT_LABELS: Record<string, string> = {
  RUN_CREATED: "创建运行", ACTION_PARSED: "解析动作", EVIDENCE_SUBMITTED: "补充证据",
  APPROVAL_RECORDED: "记录审批", CONTROL_PLAN_UPDATED: "更新控制计划", ACTION_INVALIDATED: "作废旧动作",
  PERMIT_ISSUED: "签发执行许可", TOOL_EXECUTED: "Simulator 执行", TAMPER_BLOCKED: "拦截参数篡改",
};
const ROLE_LABELS: Record<string, string> = { current_user: "由我确认", sales_manager: "销售经理审批" };
const RISK_REASON_LABELS: Record<string, string> = {
  EXTERNAL_RECIPIENT: "包含企业外部联系人", PUBLIC_SCOPE: "影响范围为公开发布",
  SENSITIVE_DATA: "包含敏感业务数据", PRICING_DATA: "涉及报价或定价",
  LOW_REVERSIBILITY: "执行后不易撤回", ACTION_INFORMATION_MISSING: "关键信息仍不完整",
  CREDENTIAL_EXPOSURE: "存在凭据暴露风险", RESTRICTED_OPERATION: "属于受限操作",
  RESTRICTED_EXECUTION: "属于受限执行",
};
const VIEW_LABELS: Record<ViewId, string> = {
  mail: "邮件", document: "文档", quote: "报价表", tasks: "任务", calendar: "日历",
  expense: "报销", crm: "CRM", audit: "审计",
};

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers: { ...REQUEST_HEADERS, ...init?.headers } });
  const body = await response.json();
  if (!response.ok) throw new ApiError(response.status, typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail));
  return body as T;
}

function Icon({ name }: { name: ViewId }) {
  const paths: Record<ViewId, ReactNode> = {
    mail: <><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></>,
    document: <><path d="M6 2h9l4 4v16H6z"/><path d="M14 2v5h5M9 12h6M9 16h6"/></>,
    quote: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M9 4v16M15 4v16"/></>,
    tasks: <><path d="M9 6h11M9 12h11M9 18h11"/><path d="m3 6 1 1 2-2m-3 7 1 1 2-2m-3 7 1 1 2-2"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 10h18M8 14h.01M12 14h.01M16 14h.01"/></>,
    expense: <><path d="M5 3h14v18l-2-1.5-2 1.5-3-1.5L9 21l-2-1.5L5 21z"/><path d="M9 8h6M9 12h6M9 16h3"/></>,
    crm: <><circle cx="9" cy="8" r="3"/><path d="M3 20c.6-4 2.6-6 6-6s5.4 2 6 6M17 7h4M19 5v4M16 13h5M16 17h5"/></>,
    audit: <><path d="M4 4h16v16H4z"/><path d="M8 9h8M8 13h8M8 17h5"/></>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

function InlineText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return <>{parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1, -1)}</code>;
    return part;
  })}</>;
}

function MessageContent({ text, streaming }: { text: string; streaming?: boolean }) {
  const lines = text.split("\n");
  const nodes: ReactNode[] = [];
  for (let index = 0; index < lines.length;) {
    const line = lines[index].trim();
    if (line.startsWith("|") && line.endsWith("|")) {
      const tableLines: string[] = [];
      while (index < lines.length && lines[index].trim().startsWith("|") && lines[index].trim().endsWith("|")) tableLines.push(lines[index++].trim());
      const rows = tableLines.map(row => row.slice(1, -1).split("|").map(cell => cell.trim())).filter(row => !row.every(cell => /^[-:]+$/.test(cell)));
      if (rows.length) nodes.push(<div className="message-table-wrap" key={`table-${index}`}><table><thead><tr>{rows[0].map((cell, i) => <th key={i}><InlineText text={cell}/></th>)}</tr></thead><tbody>{rows.slice(1).map((row, r) => <tr key={r}>{row.map((cell, c) => <td key={c}><InlineText text={cell}/></td>)}</tr>)}</tbody></table></div>);
      continue;
    }
    if (!line || line === "---") { index++; continue; }
    if (/^#{1,4}\s/.test(line)) nodes.push(<h4 key={index}><InlineText text={line.replace(/^#{1,4}\s+/, "")}/></h4>);
    else if (/^\d+\.\s/.test(line)) nodes.push(<div className="message-list-item" key={index}><b>{line.match(/^\d+/)?.[0]}.</b><span><InlineText text={line.replace(/^\d+\.\s+/, "")}/></span></div>);
    else if (/^[-•]\s/.test(line)) nodes.push(<div className="message-list-item" key={index}><b>•</b><span><InlineText text={line.replace(/^[-•]\s+/, "")}/></span></div>);
    else nodes.push(<p key={index}><InlineText text={line.replace(/^>\s?/, "")}/></p>);
    index++;
  }
  return <div className="message-rich">{nodes}{streaming && <i className="stream-caret"/>}</div>;
}

function SourceInspector({ artifact }: { artifact: WorkspaceArtifact }) {
  const [panel, setPanel] = useState<"sources" | "permissions" | "history">("sources");
  return <aside className="inspector-panel"><details className="context-dock">
    <summary><div><span>上下文与治理</span><strong>{artifact.sources.length} 个来源 · 权限与修改记录</strong></div><b>展开查看 <i>⌄</i></b></summary>
    <div className="context-dock-body"><div className="inspector-tabs" role="tablist">
      <button className={panel === "sources" ? "active" : ""} onClick={() => setPanel("sources")}>引用来源</button>
      <button className={panel === "permissions" ? "active" : ""} onClick={() => setPanel("permissions")}>权限使用</button>
      <button className={panel === "history" ? "active" : ""} onClick={() => setPanel("history")}>修改记录</button>
    </div><div className="inspector-stack">
      {panel === "sources" && artifact.sources.map((source, index) => <details className="inspector-card" key={source.source_id} open={index === 0}>
        <summary><span><i className="source-dot"/>{source.system}</span><b>⌄</b></summary>
        <div className="inspector-card-body"><time>{source.updated_at}</time><strong>{source.label}</strong><p>{source.excerpt}</p><small>{source.permission}</small></div>
      </details>)}
      {panel === "permissions" && artifact.sources.map((source, index) => <details className="inspector-card permission-card" key={source.source_id} open={index === 0}>
        <summary><span><i className="shield-dot">✓</i>{source.system}</span><b>⌄</b></summary>
        <div className="inspector-card-body"><strong>{source.permission}</strong><p>本次仅读取与当前工作项相关的字段，来源：{source.label}。</p><small>最小权限 · 可审计</small></div>
      </details>)}
      {panel === "history" && artifact.change_history.map((entry, index) => <details className="inspector-card history-card" key={`${entry.time}-${index}`} open={index === 0}>
        <summary><span><i className="history-dot"/>{entry.actor ?? "系统"}</span><b>⌄</b></summary>
        <div className="inspector-card-body"><time>{entry.time ? new Date(entry.time).toLocaleString("zh-CN") : "刚刚"}</time><strong>{entry.action ?? "更新工作区"}</strong><p>{index === 0 ? "当前保存版本" : "历史版本记录"}</p></div>
      </details>)}
      {panel === "history" && artifact.change_history.length === 0 && <div className="inspector-empty">尚无修改记录</div>}
    </div></div>
  </details></aside>;
}

function ArtifactHeader({ artifact, eyebrow, title, dirty, onSave, actions }: {
  artifact: WorkspaceArtifact; eyebrow: string; title: string; dirty: boolean; onSave: () => void; actions?: ReactNode;
}) {
  return <header className="artifact-header">
    <div className="artifact-title"><div className="app-chip"><Icon name={artifact.kind}/></div><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1></div></div>
    <div className="workspace-actions"><span className={`save-state ${dirty ? "dirty" : ""}`}><i/>{dirty ? "未保存修改" : "已保存"}</span>{actions}<button className="save-button" disabled={!dirty} onClick={onSave}>保存</button></div>
  </header>;
}

type ViewProps = { artifact: WorkspaceArtifact; dirty: boolean; onChange: (patch: Record<string, unknown>) => void; onSave: () => void };

function MailView({ artifact, dirty, onChange, onSave, onSend, onNew }: ViewProps & { onSend: () => void; onNew: () => void }) {
  const to = Array.isArray(artifact.content.to) ? artifact.content.to.join(", ") : String(artifact.content.to ?? "");
  const attachments = Array.isArray(artifact.content.attachments) ? artifact.content.attachments as string[] : [];
  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="MAIL" title="邮件工作台" dirty={dirty} onSave={onSave} actions={<><button className="outline-button" onClick={onNew}>＋ 新邮件</button><button className="outline-button" onClick={onSend}>发送邮件</button></>}/>
    <div className="artifact-layout"><section className="editor-card mail-editor">
      <div className="mail-field"><label>收件人</label><input aria-label="收件人" value={to} onChange={e => onChange({ to: e.target.value.split(",").map(v => v.trim()).filter(Boolean) })}/></div>
      <div className="mail-field"><label>抄送</label><input aria-label="抄送" value={Array.isArray(artifact.content.cc) ? artifact.content.cc.join(", ") : ""} onChange={e => onChange({ cc: e.target.value.split(",").map(v => v.trim()).filter(Boolean) })}/></div>
      <div className="mail-field subject"><label>主题</label><input aria-label="主题" value={String(artifact.content.subject ?? "")} onChange={e => onChange({ subject: e.target.value })}/></div>
      <textarea aria-label="邮件正文" value={String(artifact.content.body ?? "")} onChange={e => onChange({ body: e.target.value })} placeholder="在这里编写邮件正文…"/>
      <footer className="attachment-row"><button>＋ 添加附件</button>{attachments.map(name => <span key={name}>⌁ {name}<small>已绑定摘要</small></span>)}</footer>
    </section><SourceInspector artifact={artifact}/></div>
  </div>;
}

function DocumentView({ artifact, dirty, onChange, onSave }: ViewProps) {
  const sections = Array.isArray(artifact.content.sections) ? artifact.content.sections as { heading?: string; body?: string }[] : [];
  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="DOCUMENT" title="文档工作台" dirty={dirty} onSave={onSave}/><div className="artifact-layout">
    <section className="editor-card document-editor"><div className="document-meta"><span>{String(artifact.content.document_type ?? "内部文档")}</span><input aria-label="文档标题" value={artifact.title} readOnly/></div>
      {sections.map((section, index) => <section className="doc-section" key={`${section.heading}-${index}`}><input aria-label={`章节 ${index + 1} 标题`} value={section.heading ?? ""} onChange={e => onChange({ sections: sections.map((item, i) => i === index ? { ...item, heading: e.target.value } : item) })}/><textarea aria-label={`章节 ${index + 1} 正文`} value={section.body ?? ""} onChange={e => onChange({ sections: sections.map((item, i) => i === index ? { ...item, body: e.target.value } : item) })}/></section>)}
    </section><SourceInspector artifact={artifact}/></div></div>;
}

function QuoteView({ artifact, dirty, onChange, onSave, onImport }: ViewProps & { onImport: () => void }) {
  const items = Array.isArray(artifact.content.items) ? artifact.content.items as { name?: string; qty?: number; unit_price?: number; discount?: number; subtotal?: number }[] : [];
  const floor = Number(artifact.content.approved_floor ?? .88);
  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="QUOTE WORKBOOK" title="报价工作台" dirty={dirty} onSave={onSave} actions={<button className="outline-button" onClick={onImport}>导入报价表</button>}/><div className="artifact-layout">
    <section className="editor-card quote-editor"><div className="quote-summary"><div><span>客户</span><strong>{String(artifact.content.customer ?? "-")}</strong></div><div><span>报价编号</span><strong>{String(artifact.content.quote_id ?? "-")}</strong></div><div><span>有效期</span><input aria-label="报价有效期" value={String(artifact.content.valid_until ?? "")} onChange={e => onChange({ valid_until: e.target.value })}/></div><div><span>折扣底线</span><strong>{Math.round(floor * 100)}%</strong></div></div>
      <div className="sheet"><div className="sheet-letters"><span/><span>A</span><span>B</span><span>C</span><span>D</span><span>E</span></div><div className="sheet-row sheet-head"><span className="row-num"/><span>项目</span><span>数量</span><span>标准价</span><span>折扣 %</span><span>小计</span></div>{items.map((item, index) => <div className={`sheet-row ${Number(item.discount ?? 1) < floor ? "sheet-warning" : ""}`} key={`${item.name}-${index}`}><i className="row-num">{index + 1}</i><input value={item.name ?? ""} onChange={e => onChange({ items: items.map((row, i) => i === index ? { ...row, name: e.target.value } : row) })}/><input value={item.qty ?? 0} onChange={e => onChange({ items: items.map((row, i) => i === index ? { ...row, qty: Number(e.target.value) } : row) })}/><span>¥{Number(item.unit_price ?? 0).toLocaleString()}</span><input value={Math.round(Number(item.discount ?? 1) * 100)} onChange={e => { const discount = Number(e.target.value) / 100; const next = items.map((row, i) => i === index ? { ...row, discount, subtotal: Number(row.qty ?? 0) * Number(row.unit_price ?? 0) * discount } : row); onChange({ items: next, total: next.reduce((sum, row) => sum + Number(row.subtotal ?? 0), 0) }); }}/><span>¥{Number(item.subtotal ?? 0).toLocaleString()}</span></div>)}</div>
      <div className="quote-total"><span>含税总计</span><strong>¥{Number(artifact.content.total ?? 0).toLocaleString()}</strong></div>
    </section><SourceInspector artifact={artifact}/></div></div>;
}

function TasksView({ artifact, dirty, onChange, onSave }: ViewProps) {
  const tasks = Array.isArray(artifact.content.tasks) ? artifact.content.tasks as { id?: string; title?: string; source?: string; priority?: string; status?: string; reason?: string }[] : [];
  const updateTask = (index: number, patch: Record<string, unknown>) => onChange({ tasks: tasks.map((task, i) => i === index ? { ...task, ...patch } : task) });
  const addTask = () => onChange({ tasks: [...tasks, { id: `T-${Date.now().toString().slice(-4)}`, title: "新任务", source: "手动", priority: "中", status: "待处理", reason: "" }] });
  const columns: { status: string; color: string }[] = [
    { status: "待处理", color: "#8a93a1" }, { status: "进行中", color: "#2470e0" }, { status: "待确认", color: "#b97a12" },
    { status: "已完成", color: "#0e9f6e" }, { status: "异常挂起", color: "#cf4343" },
  ];
  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="TASKS" title="任务看板" dirty={dirty} onSave={onSave} actions={<button className="outline-button" onClick={addTask}>＋ 新建任务</button>}/><div className="artifact-layout">
    <section className="task-board editor-card">{columns.map(column => {
      const columnTasks = tasks.map((task, index) => ({ task, index })).filter(({ task }) => (task.status ?? "待处理") === column.status);
      return <div className="kanban-col" key={column.status} style={{ "--col": column.color } as CSSProperties}>
        <header className="kanban-head"><i/><strong>{column.status}</strong><span>{columnTasks.length}</span></header>
        {columnTasks.map(({ task, index }) => <article className="task-card" key={task.id ?? index}><div className="task-card-top"><select aria-label={`任务 ${index + 1} 优先级`} value={task.priority ?? "中"} onChange={e => updateTask(index, { priority: e.target.value })}><option>高</option><option>中</option><option>低</option></select><small>{task.source}</small></div><input aria-label={`任务 ${index + 1} 标题`} value={task.title ?? ""} onChange={e => updateTask(index, { title: e.target.value })}/><textarea aria-label={`任务 ${index + 1} 说明`} value={task.reason ?? ""} onChange={e => updateTask(index, { reason: e.target.value })}/><footer><select aria-label={`任务 ${index + 1} 状态`} value={task.status ?? "待处理"} onChange={e => updateTask(index, { status: e.target.value })}><option>待处理</option><option>进行中</option><option>待确认</option><option>已完成</option><option>异常挂起</option></select><code>{task.id}</code></footer></article>)}
        {columnTasks.length === 0 && <div className="kanban-empty">无任务</div>}
      </div>;
    })}</section>
    <SourceInspector artifact={artifact}/></div></div>;
}

function CalendarView({ artifact, dirty, onChange, onSave, onInvite }: ViewProps & { onInvite: () => void }) {
  type CalendarItem = { id?: string; title?: string; date?: string; start?: string; end?: string; attendees?: string[]; location?: string; agenda?: string };
  const events = Array.isArray(artifact.content.events) ? artifact.content.events as CalendarItem[] : [];
  const seedDate = String(artifact.content.selected_date ?? `${String(artifact.content.month ?? "2026-07")}-01`);
  const [selectedDate, setSelectedDate] = useState(seedDate);
  const [displayMonth, setDisplayMonth] = useState(seedDate.slice(0, 7));
  const [panel, setPanel] = useState<"month" | "day">("month");
  useEffect(() => {
    const next = String(artifact.content.selected_date ?? "");
    if (next) { setSelectedDate(next); setDisplayMonth(next.slice(0, 7)); }
  }, [artifact.artifact_id]);

  const [year, month] = displayMonth.split("-").map(Number);
  const firstDay = new Date(year, month - 1, 1).getDay();
  const formatDate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
  const cells = Array.from({ length: 42 }, (_, index) => {
    const date = new Date(year, month - 1, index - firstDay + 1);
    return { date: formatDate(date), day: date.getDate(), outside: date.getMonth() !== month - 1 };
  });
  const today = formatDate(new Date());
  const selectedEvents = events.filter(item => item.date === selectedDate).sort((a, b) => String(a.start ?? "").localeCompare(String(b.start ?? "")));
  const eventsByDate = events.reduce<Record<string, CalendarItem[]>>((result, item) => {
    if (item.date) (result[item.date] ??= []).push(item);
    return result;
  }, {});
  const changeMonth = (offset: number) => {
    const date = new Date(year, month - 1 + offset, 1);
    setDisplayMonth(formatDate(date).slice(0, 7));
  };
  const shiftDay = (offset: number) => {
    const date = new Date(`${selectedDate}T00:00:00`);
    date.setDate(date.getDate() + offset);
    setSelectedDate(formatDate(date));
  };
  const openDay = (date: string, outside: boolean) => {
    setSelectedDate(date);
    if (outside) setDisplayMonth(date.slice(0, 7));
    setPanel("day");
  };
  const updateEvent = (target: CalendarItem, patch: Partial<CalendarItem>) => onChange({ events: events.map(item => item === target ? { ...item, ...patch } : item) });
  const addEvent = () => onChange({ events: [...events, { id: `CAL-${Date.now()}`, title: "新日程", date: selectedDate, start: "09:00", end: "09:30", attendees: [], location: "", agenda: "" }] });

  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="CALENDAR" title="日历工作台" dirty={dirty} onSave={onSave} actions={<button className="outline-button" onClick={onInvite}>创建邀请</button>}/><div className="artifact-layout">
    <section className="calendar-workspace editor-card">
      {panel === "month" && <div className="month-calendar">
        <header><button aria-label="上个月" onClick={() => changeMonth(-1)}>‹</button><div><strong>{year} 年 {month} 月</strong><span>{events.filter(item => item.date?.startsWith(displayMonth)).length} 项日程 · 点击日期查看当日安排</span></div><button aria-label="下个月" onClick={() => changeMonth(1)}>›</button></header>
        <div className="calendar-weekdays">{["日", "一", "二", "三", "四", "五", "六"].map(day => <span key={day}>{day}</span>)}</div>
        <div className="calendar-grid">{cells.map(cell => {
          const dayEvents = (eventsByDate[cell.date] ?? []).slice().sort((a, b) => String(a.start ?? "").localeCompare(String(b.start ?? "")));
          return <button key={cell.date} className={`${cell.outside ? "outside" : ""} ${cell.date === selectedDate ? "selected" : ""} ${cell.date === today ? "today" : ""}`} onClick={() => openDay(cell.date, cell.outside)}>
            <span className="day-number">{cell.day}</span>
            <span className="day-events">{dayEvents.slice(0, 3).map(item => <i key={item.id ?? item.title}>{item.start ?? ""} {item.title ?? "日程"}</i>)}{dayEvents.length > 3 && <em>＋{dayEvents.length - 3} 更多</em>}</span>
          </button>;
        })}</div>
      </div>}
      {panel === "day" && <div className="day-agenda" key={selectedDate}>
        <header><div className="day-agenda-title"><button className="back-button" onClick={() => setPanel("month")}>‹ 月历</button><div><span>{selectedDate}</span><h2>{new Date(`${selectedDate}T00:00:00`).toLocaleDateString("zh-CN", { weekday: "long" })}</h2></div></div><div className="day-agenda-actions"><button aria-label="前一天" onClick={() => shiftDay(-1)}>‹</button><button aria-label="后一天" onClick={() => shiftDay(1)}>›</button><button className="add-event" onClick={addEvent}>＋ 新建日程</button></div></header>
        <div className="day-event-list">{selectedEvents.length ? selectedEvents.map((item, index) => <article className="day-event" key={item.id ?? index}><div className="event-time"><input aria-label={`日程 ${index + 1} 开始时间`} type="time" value={item.start ?? ""} onChange={e => updateEvent(item, { start: e.target.value })}/><span>—</span><input aria-label={`日程 ${index + 1} 结束时间`} type="time" value={item.end ?? ""} onChange={e => updateEvent(item, { end: e.target.value })}/></div><input className="event-title" aria-label={`日程 ${index + 1} 标题`} value={item.title ?? ""} onChange={e => updateEvent(item, { title: e.target.value })}/><label>地点<input value={item.location ?? ""} onChange={e => updateEvent(item, { location: e.target.value })}/></label><label>参与人<input value={Array.isArray(item.attendees) ? item.attendees.join(", ") : ""} onChange={e => updateEvent(item, { attendees: e.target.value.split(",").map(value => value.trim()).filter(Boolean) })}/></label><label>议程<textarea value={item.agenda ?? ""} onChange={e => updateEvent(item, { agenda: e.target.value })}/></label></article>) : <div className="calendar-empty"><span>○</span><strong>当天暂无日程</strong><p>可以手动新建，或让 Agent 协助安排。</p></div>}</div>
      </div>}
    </section>
    <SourceInspector artifact={artifact}/></div></div>;
}

function ExpenseView({ artifact, dirty, onChange, onSave }: ViewProps) {
  const invoices = Array.isArray(artifact.content.invoices) ? artifact.content.invoices as { number?: string; vendor?: string; amount?: number; result?: string }[] : [];
  const anomalies = Array.isArray(artifact.content.anomalies) ? artifact.content.anomalies as string[] : [];
  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="EXPENSE" title="报销核查" dirty={dirty} onSave={onSave}/><div className="artifact-layout"><section className="editor-card expense-card"><div className="expense-summary"><label>报销单<input aria-label="报销单号" value={String(artifact.content.case_id ?? "")} onChange={e => onChange({ case_id: e.target.value })}/></label><div><span>申请人</span><strong>{String(artifact.content.owner ?? "-")}</strong></div><div><span>总金额</span><strong>¥{Number(artifact.content.amount ?? 0).toLocaleString()}</strong></div></div><div className="invoice-list">{invoices.map((row, index) => <div key={`${row.number}-${index}`}><code>{row.number}</code><span>{row.vendor}</span><strong>¥{Number(row.amount ?? 0).toLocaleString()}</strong><b className={row.result?.includes("通过") ? "ok" : "warn"}>{row.result}</b></div>)}</div><div className="anomaly-box"><strong>需要关注</strong>{anomalies.map(item => <p key={item}>! {item}</p>)}</div></section><SourceInspector artifact={artifact}/></div></div>;
}

function CrmView({ artifact, dirty, onChange, onSave }: ViewProps) {
  const stages = ["需求确认", "方案沟通", "商务谈判", "合同谈判", "赢单"];
  const current = String(artifact.content.before ?? "");
  const target = String(artifact.content.suggested_stage ?? "合同谈判");
  const currentIndex = stages.indexOf(current);
  return <div className="artifact-page"><ArtifactHeader artifact={artifact} eyebrow="CRM" title="商机工作台" dirty={dirty} onSave={onSave}/><div className="artifact-layout"><section className="editor-card crm-card"><div className="crm-customer"><span>{String(artifact.content.customer ?? "客").slice(0, 1)}</span><div><h3>{String(artifact.content.customer ?? "-")}</h3><p>{String(artifact.content.opportunity_id ?? "-")}</p></div><strong>¥{Number(artifact.content.amount ?? 0).toLocaleString()}</strong></div><div className="stage-stepper">{stages.map((stage, index) => {
    const state = stage === target && stage !== current ? "target" : stage === current ? "current" : index < currentIndex ? "passed" : "";
    return <div className={`stage-step ${state}`} key={stage}><i>{index < currentIndex ? "✓" : index + 1}</i><span>{stage}</span></div>;
  })}</div><div className="stage-flow"><div><span>当前阶段</span><strong>{current || "-"}</strong></div><i>→</i><label><span>目标阶段</span><select aria-label="目标阶段" value={target} onChange={e => onChange({ suggested_stage: e.target.value })}><option>需求确认</option><option>方案沟通</option><option>商务谈判</option><option>合同谈判</option><option>赢单</option></select></label></div><label className="crm-next">下一步<textarea aria-label="CRM 下一步" value={String(artifact.content.next_step ?? "")} onChange={e => onChange({ next_step: e.target.value })}/></label></section><SourceInspector artifact={artifact}/></div></div>;
}

function AuditView({ events, run }: { events: AuditEvent[]; run: RunSnapshot | null }) {
  return <div className="artifact-page audit-page"><header className="artifact-header"><div className="artifact-title"><div className="app-chip"><Icon name="audit"/></div><div><span className="eyebrow">AUDIT</span><h1>执行审计</h1></div></div><code>{run?.trace_id ?? "等待受控动作"}</code></header>{events.length === 0 ? <div className="workspace-empty"><span>◇</span><strong>暂无审计事件</strong><p>Agent 发起受控动作后，证据、审批、Permit 与执行结果会记录在这里。</p></div> : <div className="audit-timeline">{events.map(event => <details key={event.sequence}><summary><b>{String(event.sequence).padStart(3, "0")}</b><span><strong>{EVENT_LABELS[event.event_type] ?? event.event_type}</strong><small>{event.event_type}</small></span><time>{new Date(event.occurred_at).toLocaleTimeString("zh-CN")}</time><i>⌄</i></summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details>)}</div>}</div>;
}

function ApprovalModal({ run, evidenceCatalog, evidence, busy, onEvidence, onSubmitEvidence, onDecide, onAuthorize }: {
  run: RunSnapshot; evidenceCatalog: Record<string, EvidenceDefinition>; evidence: Record<string, string>; busy: boolean;
  onEvidence: (key: string, value: string) => void; onSubmitEvidence: () => void;
  onDecide: (role: string, decision: "approved" | "rejected") => void; onAuthorize: () => void;
}) {
  const [expanded, setExpanded] = useState(true);
  const status = run.control_plan.status;
  const riskReasons = run.risk.reason_codes.map(code => RISK_REASON_LABELS[code] ?? code);
  return <div className={`approval-overlay ${expanded ? "" : "collapsed"}`}><section className={`approval-modal risk-${run.risk.risk_level}`} role="dialog" aria-modal="false" aria-label="动作确认">
    <header><div><span>AGENT 请求确认</span><h2>{run.action.action_type.replaceAll("_", " ")}</h2></div><div className="approval-header-actions"><b className={`risk-badge ${run.risk.risk_level}`}>{run.risk.risk_level}</b><button aria-label={expanded ? "收起确认卡片" : "展开确认卡片"} onClick={() => setExpanded(value => !value)}>{expanded ? "−" : "+"}</button></div></header>
    {expanded && <div className="approval-expandable">
    <p className="approval-summary">{run.user_message}</p>
    <div className="approval-risk-rule"><strong>{run.risk.risk_level} 风险判断</strong><span>{riskReasons.length ? riskReasons.join("；") : "仅草稿、只读或当前用户范围内操作，未命中额外风险因子"}</span></div>
    <div className="approval-facts"><span><small>能力</small><strong>{run.action.capability}</strong></span><span><small>影响范围</small><strong>{run.action.target_scope}</strong></span><span><small>目标</small><strong>{run.action.recipients.join(", ") || run.action.resources.join(", ") || "当前工作区"}</strong></span></div>
    <details className="approval-details"><summary>查看策略判断与约束 <b>⌄</b></summary><div>{Object.entries(run.control_plan.capabilities).map(([name, decision]) => <p key={name}><span><strong>{name}</strong><small>{decision.constraints.join(" · ") || "无额外约束"}</small></span><b className={decision.verdict}>{decision.verdict}</b></p>)}</div></details>
    {status === "WAITING_EVIDENCE" && <div className="approval-gate"><strong>需要补充可信依据</strong>{run.control_plan.missing_requirements.map(requirement => { const item = evidenceCatalog[requirement]; return <label key={requirement}><span>{item?.label ?? requirement}</span>{item?.input_type === "select" ? <select value={evidence[requirement] ?? ""} onChange={e => onEvidence(requirement, e.target.value)}><option value="">请选择</option>{item.options.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}</select> : <small>✓ {item?.user_action ?? "系统自动校验"}</small>}</label>})}<button className="primary-button" disabled={busy} onClick={onSubmitEvidence}>提交依据</button></div>}
    {status === "WAITING_APPROVAL" && <div className="approval-gate"><strong>需要以下角色确认</strong>{run.control_plan.required_approvals.map(role => <div className="approval-role" key={role}><span><b>{ROLE_LABELS[role] ?? role}</b><small>{role}</small></span><div><button disabled={busy} onClick={() => onDecide(role, "rejected")}>拒绝</button><button className="primary-button" disabled={busy} onClick={() => onDecide(role, "approved")}>批准</button></div></div>)}</div>}
    {status === "READY_TO_AUTHORIZE" && <footer className="approval-final"><div><strong>审批条件已满足</strong><small>确认后使用一次性 Permit 执行</small></div><button className="primary-button" disabled={busy} onClick={onAuthorize}>确认执行</button></footer>}
    </div>}
  </section></div>;
}

type TaskSyncState = "loading" | "connecting" | "synced" | "reconnecting" | "offline";
type TaskTransportState = "connecting" | "connected" | "interrupted";

const AGENT_CONNECTION_LABELS: Record<TaskTransportState, string> = {
  connecting: "正在连接当前工作区",
  connected: "已连接当前工作区",
  interrupted: "服务连接中断，正在恢复",
};
type PendingTaskMutation = {
  taskId: string;
  kind: "start" | ControlIntent["kind"];
  idempotencyKey: string;
  expectedVersion: number;
  intent?: ControlIntent;
};

function ActiveTaskStrip({ task, syncState, creating, blocked, onCreate, onRetry }: {
  task: TaskSnapshot | null;
  syncState: TaskSyncState;
  creating: boolean;
  blocked: boolean;
  onCreate: () => void;
  onRetry: () => void;
}) {
  const syncLabels: Record<TaskSyncState, string> = {
    loading: "正在读取", connecting: "正在连接", synced: "已同步",
    reconnecting: "正在重新对账", offline: "状态未知",
  };
  if (!task) return <section className="active-task-strip empty" aria-label="受控持久任务">
    <div><span>DEMO 1</span><strong>受控持久任务</strong><small>{syncState === "offline" ? "任务服务暂不可用，已有工作区仍可继续使用" : "服务端将创建 Task ID、契约和三个交付分支"}</small></div>
    <button className="task-create-button" disabled={blocked || creating || (syncState !== "synced" && syncState !== "offline")} onClick={syncState === "offline" ? onRetry : onCreate}>{creating ? "创建中" : syncState === "offline" ? "重新连接" : "＋ 创建任务"}</button>
  </section>;

  const terminal = ["committed", "failed", "cancelled"].includes(task.status);
  return <section className="active-task-strip" aria-label="当前受控持久任务">
    <div className="task-strip-main"><span>{terminal ? "RECENT TASK" : "ACTIVE TASK"}</span><strong>{task.contract.title}</strong><small>{task.contract.objective}</small></div>
    <dl className="task-strip-facts">
      <div><dt>状态</dt><dd>{TASK_STATUS_LABELS[task.status]}</dd></div>
      <div><dt>阶段</dt><dd>{TASK_PHASE_LABELS[task.phase]}</dd></div>
      <div><dt>预算</dt><dd>{task.budget.steps_used}/{task.contract.budget.max_steps} 步</dd></div>
      <div><dt>版本</dt><dd>v{task.version}</dd></div>
    </dl>
    <div className={`task-sync-state ${syncState}`}><i/><span>{syncLabels[syncState]}</span><code>{task.task_id}</code>{terminal && <button type="button" className="task-replay-button" disabled={blocked || creating || !["synced", "offline"].includes(syncState)} onClick={onCreate}>{creating ? "创建中" : "再次演示"}</button>}{["offline", "reconnecting"].includes(syncState) && <button type="button" disabled={blocked} onClick={onRetry}>{syncState === "offline" ? "重新连接" : "立即对账"}</button>}</div>
  </section>;
}

export default function Home() {
  const [threadId, setThreadId] = useState("");
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [assistantStatus, setAssistantStatus] = useState("");
  const [activeView, setActiveView] = useState<ViewId>("mail");
  const [artifacts, setArtifacts] = useState<Partial<Record<WorkspaceKind, WorkspaceArtifact>>>({});
  const [dirty, setDirty] = useState<Partial<Record<WorkspaceKind, boolean>>>({});
  const [streamingArtifact, setStreamingArtifact] = useState<WorkspaceKind | null>(null);
  const [run, setRun] = useState<RunSnapshot | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [evidenceCatalog, setEvidenceCatalog] = useState<Record<string, EvidenceDefinition>>({});
  const [evidence, setEvidence] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [task, setTask] = useState<TaskSnapshot | null>(null);
  const [taskSyncState, setTaskSyncState] = useState<TaskSyncState>("loading");
  const [taskTransportState, setTaskTransportState] = useState<TaskTransportState>("connecting");
  const [taskCreating, setTaskCreating] = useState(false);
  const [taskMutating, setTaskMutating] = useState(false);
  const [pendingTaskMutation, setPendingTaskMutation] = useState<PendingTaskMutation | null>(null);
  const [taskViewMode, setTaskViewMode] = useState<TaskViewMode>("runtime");
  const [selectedTaskArtifactVersionId, setSelectedTaskArtifactVersionId] = useState<string | null>(null);
  const [workspaceWidth, setWorkspaceWidth] = useState(0);
  const shellRef = useRef<HTMLElement>(null);
  const conversationRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);
  const silentRequestRef = useRef(false);
  const taskSequenceRef = useRef(0);
  const pendingTaskMutationRef = useRef<PendingTaskMutation | null>(null);
  const demo1CreateKeyRef = useRef<string | null>(null);

  useEffect(() => {
    try {
      const raw = window.sessionStorage.getItem(TASK_MUTATION_SESSION_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as PendingTaskMutation;
      if (saved.taskId && saved.kind && saved.idempotencyKey && Number.isInteger(saved.expectedVersion)) {
        rememberPendingTaskMutation(saved);
        setTaskSyncState("reconnecting");
      }
    } catch {
      window.sessionStorage.removeItem(TASK_MUTATION_SESSION_KEY);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      request<{ thread_id: string }>("/v1/threads", { method: "POST" }),
      request<EvidenceDefinition[]>("/v1/evidence/requirements"),
      request<WorkspaceArtifact[]>("/v1/workspace"),
    ]).then(([thread, requirements, workspace]) => {
      if (cancelled) return;
      setThreadId(thread.thread_id);
      setEvidenceCatalog(Object.fromEntries(requirements.map(item => [item.requirement, item])));
      setArtifacts(Object.fromEntries(workspace.map(item => [item.kind, item])) as Record<WorkspaceKind, WorkspaceArtifact>);
    }).catch(reason => setError(reason instanceof Error ? reason.message : "初始化失败"));
    request<TaskSnapshot[]>("/v1/tasks").then(tasks => {
      if (cancelled) return;
      const pendingTaskId = pendingTaskMutationRef.current?.taskId;
      const activeTask = tasks.find(item => item.task_id === pendingTaskId)
        ?? tasks.find(item => !["committed", "failed", "cancelled"].includes(item.status))
        ?? tasks[0]
        ?? null;
      setTask(activeTask);
      taskSequenceRef.current = activeTask?.last_event_sequence ?? 0;
      if (activeTask) reconcilePendingTaskMutation(activeTask);
      setTaskTransportState("connected");
      setTaskSyncState(pendingTaskMutationRef.current ? "reconnecting" : "synced");
    }).catch(() => {
      if (!cancelled) {
        setTaskTransportState("interrupted");
        setTaskSyncState("offline");
      }
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!run?.run_id) return;
    setEvents([]);
    const source = new EventSource(`${API_BASE}/v1/runs/${run.run_id}/events`);
    const receive = (raw: Event) => {
      const event = JSON.parse((raw as MessageEvent<string>).data) as AuditEvent;
      setEvents(current => current.some(item => item.sequence === event.sequence) ? current : [...current, event].sort((a, b) => a.sequence - b.sequence));
    };
    EVENT_TYPES.forEach(type => source.addEventListener(type, receive));
    return () => source.close();
  }, [run?.run_id]);

  useEffect(() => {
    const taskId = task?.task_id;
    if (!taskId) return;
    let cancelled = false;
    let source: EventSource | null = null;
    let reconnectTimer: number | undefined;

    const reconcile = async () => {
      try {
        const snapshot = await request<TaskSnapshot>(`/v1/tasks/${taskId}`);
        if (cancelled) return;
        setTask(snapshot);
        reconcilePendingTaskMutation(snapshot);
        taskSequenceRef.current = snapshot.last_event_sequence;
        setTaskSyncState(pendingTaskMutationRef.current ? "reconnecting" : "synced");
      } catch {
        if (!cancelled) setTaskSyncState("reconnecting");
      }
    };
    const receive = (raw: Event) => {
      const event = JSON.parse((raw as MessageEvent<string>).data) as TaskEvent;
      if (event.sequence <= taskSequenceRef.current) return;
      if (event.sequence !== taskSequenceRef.current + 1) setTaskSyncState("reconnecting");
      taskSequenceRef.current = event.sequence;
      void reconcile();
    };
    const connect = () => {
      if (cancelled) return;
      setTaskTransportState("connecting");
      setTaskSyncState(current => current === "synced" ? current : "connecting");
      source = new EventSource(`${API_BASE}/v1/tasks/${taskId}/events?after=${taskSequenceRef.current}`);
      TASK_EVENT_TYPES.forEach(type => source?.addEventListener(type, receive));
      source.onopen = () => {
        setTaskTransportState("connected");
        void reconcile();
      };
      source.onerror = () => {
        source?.close();
        if (cancelled) return;
        setTaskTransportState("interrupted");
        setTaskSyncState("reconnecting");
        reconnectTimer = window.setTimeout(connect, 1200);
      };
    };

    connect();
    return () => {
      cancelled = true;
      source?.close();
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
    };
  }, [task?.task_id]);

  useEffect(() => {
    const element = conversationRef.current;
    if (!element || !stickToBottomRef.current) return;
    const frame = requestAnimationFrame(() => { element.scrollTop = element.scrollHeight; });
    return () => cancelAnimationFrame(frame);
  }, [messages, assistantStatus]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 2400);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const activeArtifact = useMemo(() => activeView !== "audit" ? artifacts[activeView] : undefined, [activeView, artifacts]);

  async function createDemo1Task() {
    const repeat = Boolean(task && ["committed", "failed", "cancelled"].includes(task.status));
    const idempotencyKey = demo1CreateKeyRef.current ?? `demo1-round:${crypto.randomUUID()}`;
    demo1CreateKeyRef.current = idempotencyKey;
    setTaskCreating(true);
    if (!repeat) {
      setTaskTransportState("connecting");
      setTaskSyncState("connecting");
    }
    setError("");
    try {
      const snapshot = await request<TaskSnapshot>("/v1/demo1/tasks", {
        method: "POST",
        headers: { "Idempotency-Key": idempotencyKey },
      });
      demo1CreateKeyRef.current = null;
      setTask(snapshot);
      setSelectedTaskArtifactVersionId(null);
      setTaskViewMode("runtime");
      taskSequenceRef.current = snapshot.last_event_sequence;
      setTaskTransportState("connected");
      setTaskSyncState("synced");
      setNotice(repeat ? "新一轮 Demo 1 已创建" : "Demo 1 任务契约已创建");
    } catch (reason) {
      if (!repeat) {
        setTaskTransportState("interrupted");
        setTaskSyncState("offline");
      }
      setError(reason instanceof Error ? reason.message : "无法创建 Demo 1 任务");
    } finally {
      setTaskCreating(false);
    }
  }

  async function retryTaskConnection() {
    setTaskTransportState("connecting");
    setTaskSyncState("connecting");
    setError("");
    try {
      let activeTask: TaskSnapshot | null;
      if (task) {
        activeTask = await request<TaskSnapshot>(`/v1/tasks/${task.task_id}`);
      } else {
        const tasks = await request<TaskSnapshot[]>("/v1/tasks");
        activeTask = tasks.find(item => !["committed", "failed", "cancelled"].includes(item.status)) ?? tasks[0] ?? null;
      }
      setTask(activeTask);
      taskSequenceRef.current = activeTask?.last_event_sequence ?? 0;
      if (activeTask) reconcilePendingTaskMutation(activeTask);
      setTaskTransportState("connected");
      setTaskSyncState(pendingTaskMutationRef.current ? "reconnecting" : "synced");
    } catch (reason) {
      setTaskTransportState("interrupted");
      setTaskSyncState("offline");
      setError(reason instanceof Error ? reason.message : "任务服务仍不可用");
    }
  }

  async function retryPendingTaskMutation() {
    const pending = pendingTaskMutationRef.current;
    if (!pending || taskMutating) return;
    setTaskMutating(true);
    setError("");
    try {
      const path = pending.kind === "start"
        ? `/v1/tasks/${pending.taskId}/start`
        : `/v1/tasks/${pending.taskId}/controls`;
      const body = pending.kind === "start"
        ? { expected_task_version: pending.expectedVersion, idempotency_key: pending.idempotencyKey }
        : {
            ...pending.intent,
            expected_task_version: pending.expectedVersion,
            idempotency_key: pending.idempotencyKey,
          };
      const replayed = await request<TaskSnapshot>(path, { method: "POST", body: JSON.stringify(body) });
      rememberPendingTaskMutation(null);
      try {
        const latest = await request<TaskSnapshot>(`/v1/tasks/${pending.taskId}`);
        setTask(latest);
        taskSequenceRef.current = latest.last_event_sequence;
        setTaskSyncState("synced");
        setNotice(`原操作已确认，当前状态已对账至 v${latest.version}`);
      } catch {
        if (!task || task.task_id !== replayed.task_id || task.version <= replayed.version) {
          setTask(replayed);
          taskSequenceRef.current = Math.max(taskSequenceRef.current, replayed.last_event_sequence);
        }
        setTaskSyncState("reconnecting");
        setNotice("原操作已确认，正在读取最新任务状态");
      }
    } catch (reason) {
      let reconciled: TaskSnapshot | null = null;
      try { reconciled = await refreshTaskSnapshot(pending.taskId); } catch { /* Keep waiting on the original key. */ }
      if (!pendingTaskMutationRef.current) return;
      if (reason instanceof ApiError && reason.status < 500) {
        rememberPendingTaskMutation(null);
        setError(`${reason.message}${reconciled ? `；已刷新到 v${reconciled.version}` : ""}`);
      } else {
        setTaskSyncState("reconnecting");
        setError("原操作仍待确认；系统会继续保留同一幂等键，不会生成重复请求");
      }
    } finally {
      setTaskMutating(false);
    }
  }

  async function refreshTaskSnapshot(taskId: string) {
    const snapshot = await request<TaskSnapshot>(`/v1/tasks/${taskId}`);
    setTask(snapshot);
    reconcilePendingTaskMutation(snapshot);
    taskSequenceRef.current = snapshot.last_event_sequence;
    return snapshot;
  }

  function rememberPendingTaskMutation(mutation: PendingTaskMutation | null) {
    pendingTaskMutationRef.current = mutation;
    setPendingTaskMutation(mutation);
    if (typeof window !== "undefined") {
      if (mutation) window.sessionStorage.setItem(TASK_MUTATION_SESSION_KEY, JSON.stringify(mutation));
      else window.sessionStorage.removeItem(TASK_MUTATION_SESSION_KEY);
    }
  }

  function reconcilePendingTaskMutation(snapshot: TaskSnapshot) {
    const pending = pendingTaskMutationRef.current;
    if (!pending || pending.taskId !== snapshot.task_id) return;
    if (pending.kind === "start") {
      if (snapshot.version > pending.expectedVersion && snapshot.status !== "ready") {
        rememberPendingTaskMutation(null);
        setNotice(`服务端任务已更新，已对账至 v${snapshot.version}`);
      }
      return;
    }
    const recorded = snapshot.controls.find(item => item.idempotency_key === pending.idempotencyKey);
    if (!recorded) return;
    rememberPendingTaskMutation(null);
    if (recorded.status === "rejected") {
      setError(`服务端拒绝了 ${pending.kind} 控制，请按 v${snapshot.version} 复核后重试`);
    } else {
      setNotice(recorded.status === "accepted"
        ? "方向指令已记录，等待后续循环应用"
        : `服务端已应用控制，已对账至 v${snapshot.version}`);
    }
  }

  async function startDemo1Loop() {
    if (!task || taskMutating || pendingTaskMutationRef.current) return;
    const targetTask = task;
    const expectedVersion = targetTask.version;
    const idempotencyKey = `start-${crypto.randomUUID()}`;
    rememberPendingTaskMutation({ taskId: targetTask.task_id, kind: "start", idempotencyKey, expectedVersion });
    setTaskMutating(true);
    setError("");
    try {
      const snapshot = await request<TaskSnapshot>(`/v1/tasks/${targetTask.task_id}/start`, {
        method: "POST",
        body: JSON.stringify({
          expected_task_version: expectedVersion,
          idempotency_key: idempotencyKey,
        }),
      });
      setTask(snapshot);
      rememberPendingTaskMutation(null);
      taskSequenceRef.current = snapshot.last_event_sequence;
      setNotice(snapshot.status === "waiting_input"
        ? "任务已运行到证据验证阶段"
        : `任务状态已同步：${TASK_STATUS_LABELS[snapshot.status]}`);
    } catch (reason) {
      let reconciled: TaskSnapshot | null = null;
      try { reconciled = await refreshTaskSnapshot(targetTask.task_id); } catch { /* Keep the last confirmed Snapshot. */ }
      if (reconciled && reconciled.version > expectedVersion && reconciled.status !== "ready") {
        setNotice(`服务端任务已更新，已对账至 v${reconciled.version}`);
      } else if (reason instanceof ApiError && reason.status < 500) {
        rememberPendingTaskMutation(null);
        setError(`${reason.message}${reconciled ? `；已刷新到 v${reconciled.version}，请复核后重试` : ""}`);
      } else {
        setTaskSyncState("reconnecting");
        setError("启动结果待确认；已保留最后一次服务端状态，请稍后重试对账");
      }
    } finally {
      setTaskMutating(false);
    }
  }

  async function controlDemo1Task(intent: ControlIntent): Promise<boolean> {
    if (!task || taskMutating || pendingTaskMutationRef.current) return false;
    const targetTask = task;
    const idempotencyKey = `${intent.kind}-${crypto.randomUUID()}`;
    rememberPendingTaskMutation({
      taskId: targetTask.task_id,
      kind: intent.kind,
      idempotencyKey,
      expectedVersion: targetTask.version,
      intent,
    });
    setTaskMutating(true);
    setError("");
    try {
      const snapshot = await request<TaskSnapshot>(`/v1/tasks/${targetTask.task_id}/controls`, {
        method: "POST",
        body: JSON.stringify({
          ...intent,
          expected_task_version: targetTask.version,
          idempotency_key: idempotencyKey,
        }),
      });
      setTask(snapshot);
      rememberPendingTaskMutation(null);
      taskSequenceRef.current = snapshot.last_event_sequence;
      const recorded = snapshot.controls.find(item => item.idempotency_key === idempotencyKey);
      setNotice(intent.kind === "resolve_evidence"
        ? snapshot.status === "committed" ? "证据冲突已解决，任务已提交" : "证据选择已记录，仍有待处理项"
        : recorded?.status === "accepted"
          ? "方向指令已记录，等待后续循环应用"
          : "任务控制已应用");
      return true;
    } catch (reason) {
      let reconciled: TaskSnapshot | null = null;
      try { reconciled = await refreshTaskSnapshot(targetTask.task_id); } catch { /* Keep the last confirmed Snapshot. */ }
      const recorded = reconciled?.controls.find(item => item.idempotency_key === idempotencyKey);
      if (recorded && recorded.status !== "rejected") {
        rememberPendingTaskMutation(null);
        setNotice(recorded.status === "accepted"
          ? "方向指令已记录，等待后续循环应用"
          : `服务端已应用控制，已对账至 v${reconciled?.version}`);
        return true;
      }
      if (reason instanceof ApiError && reason.status < 500) {
        rememberPendingTaskMutation(null);
        setError(`${reason.message}${reconciled ? `；已刷新到 v${reconciled.version}，请复核后重试` : ""}`);
      } else {
        setTaskSyncState("reconnecting");
        setError("控制结果待确认；已重新读取服务端状态，未确认前不会显示为已应用");
      }
      return false;
    } finally {
      setTaskMutating(false);
    }
  }

  function handleStreamEvent(event: Record<string, unknown>) {
    const type = String(event.type ?? "");
    if (type === "message.created") {
      if (silentRequestRef.current) return;
      const incoming = event.message as ChatMessage;
      setMessages(current => [...current.filter(item => !item.message_id.startsWith("pending_")), incoming]);
    } else if (type === "artifact.stream.started") {
      const artifact = event.artifact as WorkspaceArtifact;
      setArtifacts(current => ({ ...current, [artifact.kind]: artifact }));
      setDirty(current => ({ ...current, [artifact.kind]: false }));
      setStreamingArtifact(artifact.kind);
    } else if (type === "artifact.delta") {
      const kind = String(event.kind) as WorkspaceKind;
      const patch = event.patch as Record<string, unknown>;
      setArtifacts(current => {
        const artifact = current[kind];
        return artifact ? { ...current, [kind]: { ...artifact, content: { ...artifact.content, ...patch } } } : current;
      });
    } else if (type === "artifact.updated") {
      const artifact = event.artifact as WorkspaceArtifact;
      setArtifacts(current => ({ ...current, [artifact.kind]: artifact }));
      setDirty(current => ({ ...current, [artifact.kind]: false }));
      setStreamingArtifact(current => current === artifact.kind ? null : current);
      setNotice(`Agent 已更新${VIEW_LABELS[artifact.kind]}`);
    } else if (type === "message.started") {
      const incoming = event.message as ChatMessage;
      setMessages(current => [...current.filter(item => item.status !== "streaming"), incoming]);
      setAssistantStatus("");
    } else if (type === "assistant.delta") {
      const messageId = String(event.message_id);
      const delta = String(event.delta ?? "");
      setMessages(current => current.map(item => item.message_id === messageId ? { ...item, content: item.content + delta } : item));
    } else if (type === "message.completed") {
      const incoming = event.message as ChatMessage;
      setMessages(current => current.map(item => item.message_id === incoming.message_id ? incoming : item));
    } else if (type === "assistant.status") {
      setAssistantStatus(String(event.label ?? "正在处理"));
    } else if (type === "action.proposed") {
      const nextRun = event.run as RunSnapshot | null;
      if (nextRun) { setRun(nextRun); setEvidence({}); setAssistantStatus(""); }
    } else if (type === "ui.focus") {
      const view = String(event.view) as ViewId;
      if (view in VIEW_LABELS && view !== "audit") setActiveView(view);
    } else if (type === "action.closed") {
      setRun(null);
    } else if (type === "error") {
      throw new Error(String(event.detail ?? "Agent 处理失败"));
    }
  }

  async function consumeStream(response: Response) {
    if (!response.ok || !response.body) throw new Error(`请求失败 (${response.status})`);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const block of blocks) {
        const data = block.split("\n").find(line => line.startsWith("data: "))?.slice(6);
        if (data) handleStreamEvent(JSON.parse(data) as Record<string, unknown>);
      }
    }
  }

  async function runAgent(text: string, silent = false) {
    if (!threadId || busy) return;
    setBusy(true); setError(""); setMessage("");
    silentRequestRef.current = silent;
    stickToBottomRef.current = true;
    if (!silent) setMessages(current => [...current, { message_id: `pending_${Date.now()}`, role: "user", content: text, status: "completed" }]);
    setAssistantStatus(silent ? "Agent 正在读取当前工作区" : "正在连接当前工作区");
    try {
      const response = await fetch(`${API_BASE}/v1/threads/${threadId}/messages/stream`, {
        method: "POST", headers: REQUEST_HEADERS,
        body: JSON.stringify({ message: text, active_view: activeView, workspace_context: activeArtifact?.content ?? {} }),
      });
      await consumeStream(response);
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : "Agent 处理失败";
      setError(detail);
      if (!silent) setMessages(current => [...current.filter(item => item.status !== "streaming"), { message_id: `error_${Date.now()}`, role: "assistant", content: `抱歉，当前任务没有完成：${detail}`, status: "failed" }]);
    } finally {
      setBusy(false); setAssistantStatus(""); silentRequestRef.current = false;
    }
  }

  async function sendMessage(event: FormEvent) {
    event.preventDefault();
    const text = message.trim();
    if (text) await runAgent(text);
  }

  function updateArtifact(patch: Record<string, unknown>) {
    if (!activeArtifact) return;
    setArtifacts(current => ({ ...current, [activeArtifact.kind]: { ...activeArtifact, content: { ...activeArtifact.content, ...patch } } }));
    setDirty(current => ({ ...current, [activeArtifact.kind]: true }));
  }

  async function saveArtifact(kind: WorkspaceKind = activeArtifact?.kind as WorkspaceKind) {
    const artifact = artifacts[kind];
    if (!artifact) return;
    setBusy(true); setError("");
    try {
      const saved = await request<WorkspaceArtifact>(`/v1/workspace/${kind}`, { method: "PUT", body: JSON.stringify({ title: artifact.title, content: artifact.content }) });
      setArtifacts(current => ({ ...current, [kind]: saved }));
      setDirty(current => ({ ...current, [kind]: false }));
      setNotice(`${VIEW_LABELS[kind]}已保存`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存失败");
    } finally { setBusy(false); }
  }

  async function triggerWorkspaceAction(text: string) {
    if (activeArtifact && dirty[activeArtifact.kind]) await saveArtifact(activeArtifact.kind);
    await runAgent(text, true);
  }

  async function startNewMail() {
    setBusy(true); setError("");
    try {
      const mail = await request<WorkspaceArtifact>("/v1/workspace/mail/new", { method: "POST" });
      setArtifacts(current => ({ ...current, mail }));
      setDirty(current => ({ ...current, mail: false }));
      setRun(null);
      setActiveView("mail");
      setNotice("已打开空白新邮件");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "无法新建邮件");
    } finally { setBusy(false); }
  }

  async function continueAfterAction(snapshot: RunSnapshot) {
    setRun(null);
    silentRequestRef.current = false;
    setAssistantStatus("Agent 正在读取执行结果");
    try {
      const response = await fetch(`${API_BASE}/v1/threads/${threadId}/runs/${snapshot.run_id}/continue/stream`, { method: "POST", headers: REQUEST_HEADERS });
      await consumeStream(response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Agent 无法读取执行结果");
    } finally { setAssistantStatus(""); setBusy(false); }
  }

  async function updateRun(path: string, init?: RequestInit) {
    if (!run) return;
    setBusy(true); setError("");
    try {
      const snapshot = await request<RunSnapshot>(path, init);
      setRun(snapshot);
      if (["EXECUTED", "DENIED", "FAILED"].includes(snapshot.status)) await continueAfterAction(snapshot);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "操作失败"); setBusy(false);
    } finally {
      if (run?.status !== "EXECUTED") setBusy(false);
    }
  }

  async function submitEvidence() { if (run) await updateRun(`/v1/actions/${run.action.action_id}/evidence`, { method: "POST", body: JSON.stringify({ values: evidence }) }); }
  async function decide(role: string, decision: "approved" | "rejected") { if (run) await updateRun(`/v1/actions/${run.action.action_id}/approvals`, { method: "POST", body: JSON.stringify({ approver_role: role, decision }) }); }
  async function authorize() { if (run) await updateRun(`/v1/actions/${run.action.action_id}/authorize`, { method: "POST" }); }

  function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
    event.preventDefault(); event.currentTarget.form?.requestSubmit();
  }

  function handleConversationScroll() {
    const element = conversationRef.current;
    if (element) stickToBottomRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 96;
  }

  function startResize(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    const shell = shellRef.current;
    if (!shell) return;
    const move = (pointer: PointerEvent) => {
      const rect = shell.getBoundingClientRect();
      const compact = rect.width < 980;
      const minimumWorkspace = compact ? rect.width * .48 : 520;
      const minimumChat = compact ? 260 : 330;
      setWorkspaceWidth(Math.min(Math.max(pointer.clientX - rect.left, minimumWorkspace), rect.width - minimumChat));
    };
    const stop = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", stop); document.body.classList.remove("is-resizing"); };
    document.body.classList.add("is-resizing");
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", stop);
  }

  const shellStyle = workspaceWidth ? ({ "--workspace-width": `${workspaceWidth}px` } as CSSProperties) : undefined;
  const currentDirty = activeArtifact ? Boolean(dirty[activeArtifact.kind]) : false;
  const viewProps = activeArtifact ? { artifact: activeArtifact, dirty: currentDirty, onChange: updateArtifact, onSave: () => void saveArtifact() } : null;
  const actionGateOpen = Boolean(run && !["EXECUTED", "DENIED", "FAILED"].includes(run.status));

  function openTaskArtifact(artifactVersionId: string) {
    setSelectedTaskArtifactVersionId(artifactVersionId);
    setTaskViewMode("runtime");
    setActiveView("tasks");
  }

  function handleTaskViewTabKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
    event.preventDefault();
    const nextMode: TaskViewMode = taskViewMode === "runtime" ? "manual" : "runtime";
    setTaskViewMode(nextMode);
    window.requestAnimationFrame(() => document.getElementById(`task-view-tab-${nextMode}`)?.focus());
  }

  return <main className="app-shell" ref={shellRef} style={shellStyle}>
    <section className="workbench" data-view={activeView}>
      <nav className="view-rail" aria-label="工作台视图">{(Object.keys(VIEW_LABELS) as ViewId[]).map(view => view === "audit"
        ? <Fragment key={view}><div className="rail-divider"/><button className={activeView === view ? "active" : ""} onClick={() => setActiveView(view)} title={VIEW_LABELS[view]}><Icon name={view}/><span>{VIEW_LABELS[view]}</span></button></Fragment>
        : <button key={view} className={activeView === view ? "active" : ""} onClick={() => setActiveView(view)} title={VIEW_LABELS[view]}><Icon name={view}/><span>{VIEW_LABELS[view]}</span></button>)}</nav>
      <div className={`workspace-viewport ${streamingArtifact === activeView ? "is-agent-editing" : ""}`}>
        {streamingArtifact === activeView && <div className="agent-edit-indicator"><i/><span>Agent 正在编辑{VIEW_LABELS[activeView]}</span></div>}
        {activeView === "mail" && viewProps && <MailView {...viewProps} onNew={() => void startNewMail()} onSend={() => void triggerWorkspaceAction("发送当前工作区中的邮件")}/>}
        {activeView === "document" && viewProps && <DocumentView {...viewProps}/>}
        {activeView === "quote" && viewProps && <QuoteView {...viewProps} onImport={() => setNotice("报价表导入入口已预留")}/>}
        {activeView === "tasks" && <div className="task-view-shell">
          <div className="task-view-tabs" role="tablist" aria-label="任务工作区模式">
            <button id="task-view-tab-runtime" type="button" role="tab" aria-controls="task-view-panel" aria-selected={taskViewMode === "runtime"} tabIndex={taskViewMode === "runtime" ? 0 : -1} className={taskViewMode === "runtime" ? "active" : ""} onKeyDown={handleTaskViewTabKeyDown} onClick={() => setTaskViewMode("runtime")}>长期任务工件</button>
            <button id="task-view-tab-manual" type="button" role="tab" aria-controls="task-view-panel" aria-selected={taskViewMode === "manual"} tabIndex={taskViewMode === "manual" ? 0 : -1} className={taskViewMode === "manual" ? "active" : ""} onKeyDown={handleTaskViewTabKeyDown} onClick={() => setTaskViewMode("manual")}>工作台待办</button>
          </div>
          <div id="task-view-panel" className="task-view-region" role="tabpanel" aria-labelledby={`task-view-tab-${taskViewMode}`}>
            {taskViewMode === "runtime"
              ? <TaskArtifactWorkspace task={task} selectedArtifactVersionId={selectedTaskArtifactVersionId} onSelectArtifact={setSelectedTaskArtifactVersionId}/>
              : viewProps && <TasksView {...viewProps}/>
            }
          </div>
        </div>}
        {activeView === "calendar" && viewProps && <CalendarView {...viewProps} onInvite={() => void triggerWorkspaceAction("创建当前工作区中的会议邀请")}/>}
        {activeView === "expense" && viewProps && <ExpenseView {...viewProps}/>}
        {activeView === "crm" && viewProps && <CrmView {...viewProps}/>}
        {activeView === "audit" && <AuditView events={events} run={run}/>}
      </div>
      {notice && <div className="workspace-toast">✓ {notice}</div>}
    </section>
    <div className="resize-divider" role="separator" aria-orientation="vertical" onPointerDown={startResize}><span>•••</span></div>
    <section className={`chat-pane ${!task || actionGateOpen ? "without-task-runtime" : ""} ${actionGateOpen ? "has-action-gate" : ""}`}>
      <div className="chat-identity"><div className="avatar">OA</div><div><strong>Office Agent</strong><span className={`id-status is-${taskTransportState}`}>{AGENT_CONNECTION_LABELS[taskTransportState]}</span></div></div>
      <ActiveTaskStrip task={task} syncState={taskSyncState} creating={taskCreating} blocked={actionGateOpen} onCreate={() => void createDemo1Task()} onRetry={() => void (pendingTaskMutation ? retryPendingTaskMutation() : retryTaskConnection())}/>
      {task && <div className={`task-runtime-slot ${actionGateOpen ? "is-hidden" : ""}`} aria-hidden={actionGateOpen}>
        <TaskRuntimePanel task={task} syncState={taskSyncState} busy={taskMutating || Boolean(pendingTaskMutation) || actionGateOpen} onStart={() => void startDemo1Loop()} onControl={controlDemo1Task} onOpenArtifact={openTaskArtifact}/>
      </div>}
      <div className="conversation" ref={conversationRef} onScroll={handleConversationScroll}>
        {messages.length === 0 && <article className="message assistant-message"><div className="msg-avatar">✦</div><div className="message-body"><strong>Office Agent</strong><p>我会读取你正在编辑的工作区，并直接协助修改。涉及发送、写入或外部影响时，我会先请求确认。</p><div className="suggestion-chips"><button type="button" onClick={() => void runAgent("帮我完善当前工作区中的内容")}>完善当前内容</button><button type="button" onClick={() => void runAgent("检查当前工作区有没有需要我注意的问题")}>检查潜在问题</button><button type="button" onClick={() => void runAgent("总结一下当前工作区的状态")}>总结当前状态</button></div></div></article>}
        {messages.map(item => <article className={`message ${item.role === "user" ? "user-message" : "assistant-message"} message-enter`} key={item.message_id}>{item.role === "assistant" && <div className="msg-avatar">✦</div>}<div className="message-body">{item.role === "assistant" && <strong>Office Agent</strong>}<MessageContent text={item.content} streaming={item.status === "streaming"}/></div></article>)}
        {assistantStatus && <article className="message assistant-message message-enter"><div className="msg-avatar">✦</div><div className="message-body"><div className="typing-bubble"><span/><span/><span/><em>{assistantStatus}</em></div></div></article>}
      </div>
      <div className="chat-footer">{error && <div className="error-banner">{error}</div>}<form className="chat-composer glass-card" onSubmit={sendMessage}><textarea aria-label="输入办公任务" value={message} onChange={event => setMessage(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder={`让 Agent 协助当前${VIEW_LABELS[activeView]}…`}/><button aria-label="发送消息" disabled={busy || !message.trim() || !threadId}>{busy ? <span className="send-spinner"/> : "↑"}</button></form><small>Agent 可读取当前未保存内容 · Enter 发送</small></div>
      {run && actionGateOpen && <ApprovalModal run={run} evidenceCatalog={evidenceCatalog} evidence={evidence} busy={busy} onEvidence={(key, value) => setEvidence(current => ({ ...current, [key]: value }))} onSubmitEvidence={submitEvidence} onDecide={decide} onAuthorize={authorize}/>}
    </section>
  </main>;
}
