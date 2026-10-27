"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { IconDownload, IconLoader2, IconRefresh, IconSend } from "@tabler/icons-react";
import "./office-action-unified.css";
import exampleData from "./office-action-examples.json";
import legacyExampleData from "./office-action-examples-legacy.json";

export type ActionInput = {
  operation: "format_text" | "extract_excerpt" | "create_task" | "send_message" | "restricted_action" | "compare_materials";
  title: string; content: string; target: string; due_date: string | null; source_ref: string | null;
  alternative_content?: string;
  format_style?: "spaced" | "compact";
};
type ActionExample = {
  request?: string; id: string; group: string; boundary: string; division: string; expected_status: string;
  steps: string[]; principles: string[]; input: ActionInput;
  level?: string; autonomy?: string; levelLabel?: string; why?: string; sources?: string[]; sourcePath?: string;
};
// Five headline cases, one per risk level L1-L5 (quiet -> strong confirmation), tied to real library files.
const ACTION_EXAMPLES = exampleData as unknown as ActionExample[];
// The earlier twelve boundary cases stay available, folded away from the main path.
const LEGACY_EXAMPLES = legacyExampleData as unknown as ActionExample[];
const ALL_EXAMPLES = [...ACTION_EXAMPLES, ...LEGACY_EXAMPLES];
const LEGACY_GROUPS = [...new Set(LEGACY_EXAMPLES.map(item => item.group))];
export type OfficeAction = {
  action_id: string; revision: number; input: ActionInput; status: string;
  risk_level: string; autonomy_level: string; mode: string; reason: string;
  missing_fields: string[]; required_checks: string[]; target_label: string;
  before: string; preview: string; source_label: string | null; source_excerpt: string | null;
  impact: string; reversibility: string; result_message: string;
  receipt: { record_id: string; kind: string; content: string; target: string; created_at: string; undone_at: string | null } | null;
  history: { revision: number; event: string; message: string; at: string; input: ActionInput; content_snapshot?: string | null }[];
  decision?: { option: "first" | "second"; rationale: string; selected_content: string; at: string } | null;
};

export function normalizeOfficeAction(value: unknown): OfficeAction | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  if (typeof item.action_id !== "string" || typeof item.revision !== "number"
    || !item.input || typeof item.input !== "object" || typeof item.preview !== "string"
    || !Array.isArray(item.history) || !Array.isArray(item.required_checks)
    || !Array.isArray(item.missing_fields)) return null;
  return value as OfficeAction;
}

const OPERATIONS: { value: ActionInput["operation"]; label: string; title: string; content: string }[] = [
  { value: "format_text", label: "整理个人文本", title: "整理会议备忘", content: "  本周会议备忘  \n\n  周三核对交付材料。  \n  周五准备内部评审。  " },
  { value: "extract_excerpt", label: "准备资料摘录", title: "准备会前摘录", content: "会议讨论交付进度。\n技术说明需要补充接口约束。\n客户反馈待项目负责人核实。" },
  { value: "create_task", label: "创建协作任务", title: "补交技术说明", content: "请补充接口约束，并附上测试说明。" },
  { value: "send_message", label: "发送汇报内容", title: "项目进展汇报", content: "您好，当前技术说明已完成内部整理，下一步准备评审。请核对本次汇报内容。" },
  { value: "restricted_action", label: "受限业务请求", title: "最低折扣承诺", content: "直接把最低折扣承诺发给客户。" },
  { value: "compare_materials", label: "核对材料分歧", title: "确定评审材料截止日期", content: "项目邮件：请在周三下班前提交评审材料。" },
];
const CONTACTS = [
  ["wang-engineering", "王工 · 研发组 · wang.engineering@example.invalid"],
  ["wang-delivery", "王工 · 交付组 · wang.delivery@example.invalid"],
  ["client-review", "客户评审联系人 · review@example.invalid"],
];
const CHECK_LABELS: Record<string, string> = {
  target: "已核对完整收件对象", content: "已核对这份正文", impact: "已了解本次提交范围与撤回限制",
};
const OPEN = new Set(["needs_input", "awaiting_confirmation", "deferred", "stale", "awaiting_decision"]);
type FormatStyle = "spaced" | "compact";
function readFormatPreference(key: string): FormatStyle | null {
  try {
    const value = window.localStorage.getItem(key);
    return value === "spaced" || value === "compact" ? value : null;
  } catch { return null; }
}
const STATE_LABELS: Record<string, string> = {
  needs_input: "待补信息", awaiting_confirmation: "待你确认", awaiting_decision: "待你判断",
  deferred: "已暂缓", draft_ready: "内部草稿", executed: "结果已记录", decided: "判断已记录",
  denied: "受限未执行", cancelled: "已取消", undone: "已撤销", stale: "需重新核对",
};
const blank = (): ActionInput => ({ ...OPERATIONS[0], target: "", due_date: null, source_ref: null, operation: "format_text" });
function initial(): ActionInput {
  const { operation, title, content, target, due_date, source_ref } = blank();
  return { operation, title, content, target, due_date, source_ref };
}

export function OfficeActionWorkbench({ run, files, apiBase, headers, onSnapshot, onOpenSource, blocked, sessionGeneration, isSessionCurrent, readOnly = false, onNavigationLockChange, composerHost = null, onAnother }: {
  run: { run_id: string; version: number; office_action: OfficeAction | null } | null;
  files: { file_ref: string; display_label: string; display_path: string }[];
  apiBase: string; headers: Record<string, string>;
  onSnapshot: (value: unknown, generation: number) => void; onOpenSource: (ref: string) => void; blocked: boolean; readOnly?: boolean;
  sessionGeneration: number; isSessionCurrent: (generation: number) => boolean;
  onNavigationLockChange?: (locked: boolean) => void;
  /** Demo1-style composer slot: when given (and no task is open) the launcher renders there instead of inline. */
  composerHost?: HTMLElement | null;
  onAnother?: () => void;
}) {
  const action = run?.office_action ?? null;
  const [draft, setDraft] = useState<ActionInput>(initial);
  const [editing, setEditing] = useState(false);
  const [newItem, setNewItem] = useState(false);
  const [exampleId, setExampleId] = useState("");
  const [manualOpen, setManualOpen] = useState(false);
  const [checks, setChecks] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [unknown, setUnknown] = useState(false);
  const [draftEditing, setDraftEditing] = useState(false);
  useEffect(() => { onNavigationLockChange?.(busy || unknown || editing || draftEditing); }, [busy, unknown, editing, draftEditing, onNavigationLockChange]);
  const [editedText, setEditedText] = useState("");
  const [choice, setChoice] = useState<"first" | "second" | "">("");
  const [rationale, setRationale] = useState("");
  const [recent, setRecent] = useState<{ run_id: string; action: OfficeAction }[]>([]);
  const [recentError, setRecentError] = useState("");
  const [recentOpen, setRecentOpen] = useState(false);
  const [listRefresh, setListRefresh] = useState(0);
  const [recentFilter, setRecentFilter] = useState("all");
  const [savedFormat, setSavedFormat] = useState<FormatStyle | null>(null);
  const [preferenceError, setPreferenceError] = useState("");
  const [restoreFrom, setRestoreFrom] = useState<number | null>(null);
  const editorRef = useRef<HTMLTextAreaElement>(null);
  const preferenceKey = `office-format-style-v1:${Object.entries(headers).find(([key]) => key.toLowerCase() === "x-user-id")?.[1] ?? "local"}`;
  const freshDraft = (): ActionInput => ({ ...initial(), format_style: readFormatPreference(preferenceKey) ?? "spaced" });
  useEffect(() => { setSavedFormat(readFormatPreference(preferenceKey)); }, [preferenceKey]);
  function saveFormatPreference(style: FormatStyle | null) {
    try {
      if (style) window.localStorage.setItem(preferenceKey, style);
      else window.localStorage.removeItem(preferenceKey);
      setSavedFormat(style); setPreferenceError("");
    } catch { setPreferenceError("浏览器未能保存偏好；本次选择仍可使用，请稍后重试。"); }
  }
  const pending = useRef<{ url: string; body: string } | null>(null);
  const busyRef = useRef(false);
  const readRef = useRef(0);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);
  const sessionCurrent = () => mountedRef.current && isSessionCurrent(sessionGeneration);
  useEffect(() => {
    pending.current = null;
    busyRef.current = false;
    readRef.current += 1;
    setBusy(false); setError(""); setUnknown(false);
    setChecks([]); setChoice(""); setRationale("");
    setEditing(false); setDraftEditing(false); setRestoreFrom(null); setNewItem(false);
    setExampleId(""); setManualOpen(false);
    if (!action) { setDraft(freshDraft()); setEditedText(""); setRecentOpen(false); }
  }, [sessionGeneration]);
  useEffect(() => {
    setChecks([]);
    setChoice(""); setRationale(""); setDraftEditing(false); setRestoreFrom(null);
    if (action) { setDraft(action.input); setEditedText(action.preview); setEditing(false); setNewItem(false); }
  }, [run?.run_id, action?.revision]); // a new version invalidates every local check
  useEffect(() => {
    if (!recentOpen) return;
    const controller = new AbortController();
    setRecentError("");
    void fetch(`${apiBase}/v1/harness/runs?limit=20`, { headers, signal: controller.signal })
      .then(async response => {
        if (!response.ok) throw new Error("暂时无法读取最近事项，请重试。");
        const payload = await response.json();
        if (controller.signal.aborted || !sessionCurrent()) return;
        if (!Array.isArray(payload.runs)) throw new Error("最近事项返回格式不完整。");
        setRecent(payload.runs.flatMap((item: { run_id?: string; office_action?: unknown }) => {
          const current = normalizeOfficeAction(item.office_action);
          return current && typeof item.run_id === "string" ? [{ run_id: item.run_id, action: current }] : [];
        }));
      })
      .catch(caught => { if (!controller.signal.aborted && sessionCurrent()) { setRecent([]); setRecentError(caught instanceof Error ? caught.message : "读取失败"); } });
    return () => controller.abort();
  }, [recentOpen, listRefresh, apiBase, headers, run?.run_id, run?.version, sessionGeneration]);
  const shown = newItem ? null : action;
  const selectedExample = ALL_EXAMPLES.find(item => item.id === exampleId);
  function applyExample(example: ActionExample) {
    // Real-library cases resolve their file_ref at runtime from the display path, never from a hard-coded hash.
    const source = example.sourcePath ? files.find(file => file.display_path === example.sourcePath) : undefined;
    setExampleId(example.id);
    setDraft({ ...example.input, source_ref: source?.file_ref ?? example.input.source_ref });
    setError(""); setChecks([]); setChoice(""); setRationale("");
  }
  const editable = !shown || editing || shown.status === "needs_input" || shown.status === "stale"
    || (shown.status === "deferred" && shown.missing_fields.length > 0);
  const open = !!shown && OPEN.has(shown.status);
  const canLeave = !open || shown?.status === "deferred";
  const pendingCount = recent.filter(item => OPEN.has(item.action.status)).length;
  const visibleRecent = recentFilter === "pending" ? recent.filter(item => OPEN.has(item.action.status)) : recent;
  const earlier = shown ? [...shown.history].reverse().find(item => item.revision < shown.revision) : null;
  const revisedDraft = shown?.status === "draft_ready" && shown.history.some(item => item.event === "edit_draft");
  const changes = shown && earlier ? [
    ["标题", earlier.input.title, shown.input.title],
    ["正文", earlier.input.content, shown.input.content],
    ["办理对象", CONTACTS.find(([id]) => id === earlier.input.target)?.[1] ?? earlier.input.target,
      CONTACTS.find(([id]) => id === shown.input.target)?.[1] ?? shown.input.target],
    ["截止日期", earlier.input.due_date ?? "", shown.input.due_date ?? ""],
    ["材料 B", earlier.input.alternative_content ?? "", shown.input.alternative_content ?? ""],
    ...(shown.input.operation === "extract_excerpt" ? [["草稿", earlier.content_snapshot ?? earlier.input.content, shown.preview]] : []),
  ].filter(([, before, after]) => before !== after && (before || after)) : [];

  async function send(url: string, body: object, retry = false) {
    if (busyRef.current || !sessionCurrent()) return;
    readRef.current += 1;
    if (!retry) pending.current = { url, body: JSON.stringify(body) };
    const request = pending.current;
    if (!request) return;
    busyRef.current = true; setBusy(true); setError("");
    const abort = new AbortController();
    const timer = window.setTimeout(() => abort.abort(), 12000);
    try {
      const response = await fetch(request.url, { method: "POST", headers, body: request.body, signal: abort.signal });
      const payload = await response.json();
      // The server may have committed even after navigation. Keep that history,
      // but never let its late response replace the newly selected task.
      if (!sessionCurrent()) return;
      if (!response.ok) {
        if (response.status < 500) { pending.current = null; setUnknown(false); }
        if (response.status === 409) {
          setChecks([]);
          await refresh();
          if (!sessionCurrent()) return;
        }
        if (response.status >= 500) setUnknown(true);
        throw new Error(typeof payload.detail === "string" ? payload.detail : "请检查填写内容后再提交。");
      }
      if (!normalizeOfficeAction(payload.run?.office_action)) throw new Error("返回内容无法核对，请查询最新状态。");
      onSnapshot(payload, sessionGeneration); pending.current = null; setUnknown(false); setNewItem(false); setEditing(false); setDraftEditing(false);
      titleRef.current?.focus({ preventScroll: true });
    } catch (caught) {
      if (!sessionCurrent()) return;
      if (pending.current) setUnknown(true);
      setError(caught instanceof Error ? caught.message : "请求结果尚未确认。");
    } finally { window.clearTimeout(timer); if (sessionCurrent()) { busyRef.current = false; setBusy(false); } }
  }
  async function refresh(runId = run?.run_id) {
    if (!runId) return;
    const readId = ++readRef.current;
    try {
      const response = await fetch(`${apiBase}/v1/harness/runs/${encodeURIComponent(runId)}`, { headers });
      if (!response.ok) throw new Error("暂时无法读取当前事项。");
      const payload = await response.json();
      if (readId !== readRef.current || !sessionCurrent()) return;
      if (!normalizeOfficeAction(payload.office_action)) throw new Error("当前事项无法核对。");
      onSnapshot(payload, sessionGeneration);
      setNewItem(false);
    } catch (caught) { if (readId === readRef.current && sessionCurrent()) setError(caught instanceof Error ? caught.message : "读取失败，请稍后重试。"); }
  }
  function submit() {
    void send(`${apiBase}/v1/harness/runs`, {
      instruction: `办理事项：${draft.title}`, idempotency_key: `action-${crypto.randomUUID()}`,
      action: draft,
    });
  }
  function control(command: string) {
    if (!run || !shown || readOnly) return;
    void send(`${apiBase}/v1/harness/runs/${encodeURIComponent(run.run_id)}/action-controls`, {
      command, expected_version: run.version, action_revision: shown.revision,
      idempotency_key: `action-control-${crypto.randomUUID()}`,
      ...(command === "revise" ? { replacement: draft } : {}),
      reviewed_fields: command === "confirm" ? checks : [],
      ...(command === "edit_draft" ? { edited_content: editedText } : {}),
      ...(command === "record_decision" ? { selected_option: choice, rationale } : {}),
    });
  }
  function downloadText() {
    if (!shown?.receipt) return;
    const url = URL.createObjectURL(new Blob([shown.receipt.content], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "事项内容.txt"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function downloadHandoff() {
    if (!shown || unknown) return;
    const nextDecision = shown.status === "denied"
      ? "请有权人员核准受限请求；本工作区不能发起正式审批或绕过限制。"
      : shown.missing_fields.length
        ? `请事项发起人补齐：${shown.missing_fields.join("、")}，再重新核对。`
        : shown.input.operation === "compare_materials"
          ? "请了解业务的负责人核对两份材料，明确采用哪份及理由；记录判断不会自动继续其他任务。"
          : "请事项发起人重新核对当前对象、内容及影响；暂缓不等于取消，也不等于批准。";
    const note = [
      shown.input.title, `状态：${STATE_LABELS[shown.status] ?? shown.status}`,
      `内容版本：${shown.revision}`, `处理原因：${shown.reason}`,
      `办理对象：${shown.target_label || "未指定"}`,
      `截止日期：${shown.input.due_date || "未指定"}`,
      `当前已保存结果：${shown.result_message}`,
      `需要谁决定什么：${nextDecision}`,
      `待核对项：${shown.required_checks.map(item => CHECK_LABELS[item] ?? item).join("、") || "无逐项确认要求"}`,
      `影响：${shown.impact}`, `恢复范围：${shown.reversibility}`,
      `材料 A / 正文：\n${shown.input.content}`,
      ...(shown.input.alternative_content ? [`材料 B：\n${shown.input.alternative_content}`] : []),
      ...(shown.source_excerpt ? [`来源：${shown.source_label ?? "用户填写内容"}\n${shown.source_excerpt}`] : []),
      "返回方式：在原工作台的最近事项中查找同名事项，核对最新状态和版本后继续。最近列表仅覆盖当前身份最近 20 个 Run，不能保证始终可找回。",
      "本说明只含服务端已保存内容，不含未提交的编辑、选择或理由；导出不会暂缓、确认或继续事项。",
      "请由有权且了解业务的人员核对。本说明仅供交接，未发起审批、未通知他人、未执行外部动作。",
    ].join("\n\n");
    const url = URL.createObjectURL(new Blob([note], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "人工处理说明.txt"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
    const fields = <>
        <div className="office-action-form-heading"><label>事项类型<select aria-label="事项类型" value={draft.operation} disabled={!!shown} onChange={event => {
          setExampleId("");
          const option = OPERATIONS.find(item => item.value === event.target.value)!;
          setDraft({ operation: option.value, title: option.title, content: option.content, target: "", due_date: null, source_ref: null,
            ...(option.value === "format_text" ? { format_style: savedFormat ?? "spaced" } : {}),
            alternative_content: option.value === "compare_materials" ? "会议记录：评审材料于周五提交，是否替代原邮件尚未确认。" : "" });
        }}>{OPERATIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label>标题<input aria-label="事项标题" value={draft.title} maxLength={120} required onChange={event => setDraft({ ...draft, title: event.target.value })} /></label></div>
        {draft.operation === "format_text" && <details className="office-format-preference"><summary>整理偏好 · {(draft.format_style ?? "spaced") === "compact" ? "紧凑排列" : "段落间空一行"}{savedFormat ? " · 已记住" : ""}</summary>
          <label>整理方式<select aria-label="整理方式" value={draft.format_style ?? "spaced"} onChange={event => {
            const style = event.target.value as FormatStyle;
            setDraft({ ...draft, format_style: style });
            if (savedFormat) saveFormatPreference(style);
          }}><option value="spaced">段落间空一行</option><option value="compact">紧凑排列</option></select></label>
          <label className="office-check"><input type="checkbox" checked={savedFormat !== null} onChange={event => saveFormatPreference(event.target.checked ? draft.format_style ?? "spaced" : null)} />记住个人文本整理方式</label>
          {savedFormat && <button type="button" onClick={() => saveFormatPreference(null)}>清除整理偏好</button>}
          <p>仅记住此浏览器的整理方式，不保存正文或联系人，不代替确认。清除后下次使用默认方式，本次内容不变。</p>
          {preferenceError && <p role="alert">{preferenceError}</p>}
        </details>}
        {draft.operation === "extract_excerpt" && <label>摘录来源<select aria-label="摘录来源" value={draft.source_ref ?? ""} onChange={event => setDraft({ ...draft, source_ref: event.target.value || null })}><option value="">使用下方填入的文字</option>{files.map(file => <option key={file.file_ref} value={file.file_ref}>{file.display_path || file.display_label}</option>)}</select></label>}
        <label>{draft.source_ref ? "补充说明（不计入摘录）" : "内容"}<textarea aria-label="事项内容" value={draft.content} maxLength={5000} rows={6} onChange={event => setDraft({ ...draft, content: event.target.value })} /></label>
        {draft.operation === "compare_materials" && <><p>上方为材料 A，下方为材料 B。均为你提供的对照内容，系统不自动判断哪份正确。</p><label>材料 B<textarea aria-label="第二份材料" rows={5} maxLength={5000} value={draft.alternative_content ?? ""} onChange={event => setDraft({ ...draft, alternative_content: event.target.value })} /></label></>}
        {["create_task", "send_message"].includes(draft.operation) && <label>{draft.operation === "create_task" ? "负责人" : "收件人"}<select aria-label="办理对象" value={draft.target} onChange={event => setDraft({ ...draft, target: event.target.value })}><option value="">请选择具体联系人</option>{CONTACTS.filter(([id]) => draft.operation !== "create_task" || id !== "client-review").map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>}
        {draft.operation === "create_task" && <label>截止日期<input type="date" aria-label="截止日期" value={draft.due_date ?? ""} onChange={event => setDraft({ ...draft, due_date: event.target.value || null })} /></label>}
    </>;
    const composer = !shown ? <div className="office-composer">
      <textarea aria-label="办理指令" readOnly rows={6} value={selectedExample ? (selectedExample.request ?? `${selectedExample.input.title}\n${selectedExample.input.content}`) : ""} placeholder="例如：从下方示例里选一个 L1–L5 办公任务，指令会自动填入；本演示由固定规则直接给出结果，不调用大模型" />
      <details className="office-division-examples office-demo-cases" open>
        <summary>办公任务与人机分工示例</summary>
        <div className="office-task-examples office-level-cases" role="group" aria-label="选择演示案例">{ACTION_EXAMPLES.map(item => <button type="button" key={item.id} aria-pressed={exampleId === item.id} className={`office-level-case level-${item.level}${exampleId === item.id ? " is-selected" : ""}`} onClick={() => applyExample(item)}>
          <b>{item.level}</b><span><strong>{item.input.title}</strong><small>{item.levelLabel} · {item.autonomy}</small></span>
        </button>)}</div>
        {selectedExample && <div className="office-example-boundary"><strong>{selectedExample.boundary}</strong>
          {selectedExample.why && <p>为什么是这一档：{selectedExample.why}</p>}
          {selectedExample.sources?.length ? <p>结合资料库文件：{selectedExample.sources.join("、")}</p> : null}
          <span>预设演示材料 · 点击“启动 Control Loop”后直接给出结果，不调用大模型</span></div>}
        <details className="office-legacy-examples">
          <summary>更多边界案例 · {LEGACY_EXAMPLES.length} 个（缺信息、改内容重核、材料冲突等）</summary>
          <label>选择案例<select aria-label="选择更多边界案例" value={LEGACY_EXAMPLES.some(item => item.id === exampleId) ? exampleId : ""} onChange={event => {
            const example = LEGACY_EXAMPLES.find(item => item.id === event.target.value);
            if (example) { applyExample(example); setManualOpen(true); } else setExampleId("");
          }}><option value="">选择一个边界案例</option>{LEGACY_GROUPS.map(group => <optgroup label={group} key={group}>{LEGACY_EXAMPLES.filter(item => item.group === group).map(item => <option key={item.id} value={item.id}>{item.input.title}</option>)}</optgroup>)}</select></label>
        </details>
      </details>
    </div> : null;
    const portalForm = !shown && !run && composerHost ? composerHost : null;
    const manualForm = editable ? <form onSubmit={event => { event.preventDefault(); shown ? control("revise") : submit(); }}>
      <fieldset disabled={busy || unknown || blocked}>
        {composer}
        {shown ? fields : <details className="office-manual" open={manualOpen} onToggle={event => setManualOpen(event.currentTarget.open)}><summary>调整办理参数（可选）</summary>{fields}</details>}
        {shown ? <div className="office-action-buttons"><button className="primary" type="submit">{busy ? "正在处理" : "更新内容并重新核对"}</button>{editing && <button type="button" onClick={() => { setEditing(false); setDraft(shown.input); }}>放弃修改</button>}</div>
          : <footer className="office-launch"><button className="primary" type="submit" disabled={!exampleId && !manualOpen}>{busy ? <IconLoader2 aria-hidden="true" /> : <IconSend aria-hidden="true" />}{busy ? "正在启动" : "启动 Control Loop"}</button></footer>}
      </fieldset>
    </form> : null;
  return <section className="office-actions office-actions-unified" aria-label="单步事项">
    <header className="office-action-heading"><div><h2 ref={titleRef} tabIndex={-1} hidden={!shown}>{shown ? shown.input.title : "这次需要做什么？"}</h2></div>
    </header>
    <div className="office-action-tools"><p className="office-action-environment">固定规则处理 · 仅保存在测试工作区 · 不发送或通知</p>
      {shown && <button className="office-icon-button" type="button" aria-label="核对最新状态" title="核对最新状态" disabled={busy} onClick={() => void refresh()}><IconRefresh aria-hidden="true" /></button>}
    </div>
    {blocked && <p role="status">当前资料研究任务尚未结束，请先处理该任务或停止后办理新事项。</p>}
    {readOnly && shown && <p role="status">正在核对当前任务指针，或此记录仅供查看。核对通过前不能修改或确认事项。</p>}
    {error && <div className="office-action-error" role="alert"><p>{unknown ? "提交结果尚未确认。请保留本次请求，核对后继续。" : error}</p>{unknown && <><p>{error}</p><button disabled={busy} onClick={() => void send("", {}, true)}>重试同一请求</button></>}</div>}
    {shown && <div className={`office-action-state office-control-context risk-${shown.risk_level}`} role="status">
      <div className="office-action-state-heading"><span>{shown.risk_level} · {shown.mode}</span><small>第 {shown.revision} 版 · {STATE_LABELS[shown.status] ?? "请核对状态"}</small></div>
      {!shown.receipt && <p>{shown.result_message}</p>}
      {(unknown || editing || draftEditing || open) && <p className="office-pending-context">{unknown ? "结果待核对 · 暂不开始新的操作" : editing || draftEditing ? "你正在编辑，修改尚未保存" : "等待你处理 · 不会自动继续"}</p>}
    </div>}
    {shown?.missing_fields.length ? <div role="status"><p>还需要补齐以下信息，尚未创建或发送：</p><ul className="office-action-missing">{shown.missing_fields.map(item => <li key={item}>{item}</li>)}</ul></div> : null}
    <fieldset className="office-action-authority" disabled={readOnly && !!shown}>
    {portalForm ? createPortal(manualForm, portalForm) : manualForm}
    {shown && !editable && <>
      {shown.input.operation === "compare_materials" ? <div className="office-comparison" role="group" aria-label="材料对照">
        <article><h3>材料 A · 用户提供</h3><pre>{shown.input.content}</pre></article>
        <article><h3>材料 B · 用户提供</h3><pre>{shown.input.alternative_content}</pre></article>
      </div> : <div className={shown.status === "draft_ready" ? "office-draft-review" : undefined}>
        <div className="office-action-preview"><h3>{shown.status === "draft_ready" ? revisedDraft ? "人工修订草稿" : "摘录草稿" : "本次内容"}</h3><p>{shown.target_label}</p>{shown.input.due_date && <p>截止日期：{shown.input.due_date}</p>}<pre>{shown.preview}</pre></div>
        {shown.status === "draft_ready" && shown.source_excerpt && <details className="office-source-review" open>
          <summary>核对来源：{shown.source_label ?? "用户填写内容"}</summary>
          <pre>{shown.source_excerpt}</pre>
          {shown.input.source_ref && <button onClick={() => onOpenSource(shown.input.source_ref!)}>打开资料预览</button>}
        </details>}
      </div>}
      {shown.status === "draft_ready" && <div className="office-draft-edit">
        {draftEditing ? <form onSubmit={event => { event.preventDefault(); control("edit_draft"); }}>
          <fieldset disabled={busy || unknown}><label>{restoreFrom === null ? "修改内部草稿" : `正在取回第 ${restoreFrom} 版内容`}<textarea ref={editorRef} aria-label="编辑摘录草稿" rows={8} maxLength={5000} value={editedText} onChange={event => setEditedText(event.target.value)} /></label>
          {restoreFrom !== null && <p role="status">尚未恢复。保存后形成第 {shown.revision + 1} 版，当前版本和原文仍保留；不会外发。</p>}
          <p>保存只更新内部草稿。原文继续保留在下方，修改后的内容不再称为逐字摘录。</p>
          <div className="office-action-buttons"><button type="submit" className="primary" disabled={!editedText.trim()}>{restoreFrom === null ? "保存草稿修改" : "保存为新的草稿版本"}</button><button type="button" onClick={() => { setDraftEditing(false); setRestoreFrom(null); setEditedText(shown.preview); }}>放弃草稿修改</button></div></fieldset>
        </form> : <button disabled={busy || unknown} onClick={() => { setRestoreFrom(null); setEditedText(shown.preview); setDraftEditing(true); }}>编辑这份草稿</button>}
      </div>}
      {shown.input.operation === "format_text" && <details><summary>查看整理前的内容</summary><pre>{shown.before}</pre></details>}
      <details className="office-risk-lens" open={shown.risk_level === "L4" || shown.risk_level === "L5"}><summary>影响与处理依据</summary><dl><dt>处理原因</dt><dd>{shown.reason}</dd><dt>将影响什么</dt><dd>{shown.impact}</dd><dt>恢复方式</dt><dd>{shown.reversibility}</dd><dt>处理权限</dt><dd>{shown.autonomy_level} · 第 {shown.revision} 版</dd></dl></details>
      {shown.source_excerpt && shown.status !== "draft_ready" && <details><summary>核对来源：{shown.source_label ?? "用户填写内容"}</summary><pre>{shown.source_excerpt}</pre>{shown.input.source_ref && <button onClick={() => onOpenSource(shown.input.source_ref!)}>打开资料预览</button>}</details>}
      {changes.length > 0 && open && <p className="office-recheck-notice" role="status">内容已变更：{changes.map(([label]) => label).join("、")}。旧核对已失效，请重新核对第 {shown.revision} 版。</p>}
      {changes.length > 0 && <details className="office-version-changes" open={open || undefined}><summary>第 {shown.revision} 版修改了什么（{changes.length} 项）</summary>
        <p>{shown.status === "draft_ready" ? "人工修订与原始摘录分别保留，请按需对照。" : "旧核对不沿用，请按当前内容重新判断。"}</p>
        {changes.map(([label, before, after]) => <div key={label}><h4>{label}</h4><div className="office-comparison">
          <article><span>修改前</span><pre>{before || "未填写"}</pre></article>
          <article><span>当前内容</span><pre>{after || "未填写"}</pre></article>
        </div></div>)}
      </details>}
      {open && !unknown && shown.input.operation === "compare_materials" && <form className="office-decision" onSubmit={event => { event.preventDefault(); control("record_decision"); }}>
        <fieldset disabled={busy}><legend>这次先采用哪份材料？</legend><p>只记录本次核对口径和理由，不证明材料正确，不会改写原文，也不会自动继续其他任务。</p>
        <label className="office-choice"><input type="radio" name="material-choice" value="first" checked={choice === "first"} onChange={() => setChoice("first")} />采用材料 A</label>
        <label className="office-choice"><input type="radio" name="material-choice" value="second" checked={choice === "second"} onChange={() => setChoice("second")} />采用材料 B</label>
        <label>判断理由<textarea aria-label="判断理由" value={rationale} maxLength={1000} rows={3} onChange={event => setRationale(event.target.value)} /></label>
        <div className="office-action-buttons"><button className="primary" type="submit" disabled={!choice || !rationale.trim()}>记录这次判断</button><button type="button" onClick={() => { setEditing(true); setChecks([]); }}>修改内容</button><button type="button" onClick={() => control("defer")}>暂时无法判断，稍后处理</button><button type="button" onClick={() => control("cancel")}>取消本次事项</button></div>
        </fieldset></form>}
      {open && !unknown && shown.input.operation !== "compare_materials" && <div className="office-action-review"><fieldset disabled={busy}><legend>{shown.risk_level === "L4" ? "请逐项核对当前内容" : "是否按以上内容创建测试任务？"}</legend>{shown.required_checks.map(item => <label className="office-check" key={item}><input type="checkbox" checked={checks.includes(item)} onChange={event => setChecks(current => event.target.checked ? [...current, item] : current.filter(value => value !== item))} />{CHECK_LABELS[item]}</label>)}
        <div className="office-action-buttons"><button type="button" className="primary" disabled={shown.required_checks.some(item => !checks.includes(item))} onClick={() => control("confirm")}>{shown.input.operation === "create_task" ? "确认创建测试任务" : "确认登记测试发件"}</button><button type="button" onClick={() => { setEditing(true); setChecks([]); }}>修改内容</button><button type="button" onClick={() => control("defer")}>稍后处理</button><button type="button" onClick={() => control("cancel")}>取消本次事项</button></div>
      </fieldset></div>}
    </>}
    {shown && editable && open && <button disabled={busy || unknown} onClick={() => control("cancel")}>取消本次事项</button>}
    {shown?.decision && <div className="office-decision-result"><h3>你的判断已记录</h3><p>采用材料 {shown.decision.option === "first" ? "A" : "B"}</p><p>判断理由：{shown.decision.rationale}</p><p>这项记录没有修改原材料，也不是业务审批，不会自动继续其他任务。</p></div>}
    {shown?.receipt && !draftEditing && <div className="office-action-receipt"><div><h3>结果记录</h3><p>{shown.result_message}</p><small>{new Date(shown.receipt.created_at).toLocaleString("zh-CN")}</small></div><div className="office-action-buttons"><button type="button" onClick={downloadText}><IconDownload aria-hidden="true" />下载本次内容</button>{shown.input.operation === "format_text" && shown.status === "executed" && <button disabled={busy || unknown} onClick={() => control("undo")}>撤销此次整理</button>}</div></div>}
    {shown?.status === "denied" && <p className="office-action-handoff">请将承诺内容交给有权人员核准。当前工作区未连接正式审批系统。</p>}
    {shown && (shown.status === "denied" || open) && <button type="button" disabled={unknown || busy || editing || draftEditing} onClick={downloadHandoff}>下载人工处理说明</button>}
    {shown && <details className="office-action-history"><summary>查看操作记录（{shown.history.length}）</summary><ol>{shown.history.map((item, index) => <li key={index}><span>第 {item.revision} 版 · {new Date(item.at).toLocaleTimeString("zh-CN")}</span><p>{item.message}</p><details><summary>当时的内容</summary><pre>{item.input.title}{"\n"}{item.input.content}{item.input.alternative_content ? `\n材料 B：\n${item.input.alternative_content}` : ""}</pre>{item.content_snapshot != null && item.content_snapshot !== item.input.content && <><h4>当时的结果 / 草稿</h4><pre>{item.content_snapshot}</pre></>}</details>
      {shown.status === "draft_ready" && item.revision < shown.revision && item.content_snapshot != null && item.content_snapshot !== shown.preview && <button type="button" disabled={busy || unknown || draftEditing || editing || blocked} onClick={() => {
        setEditedText(item.content_snapshot!); setRestoreFrom(item.revision); setDraftEditing(true);
        window.requestAnimationFrame(() => editorRef.current?.focus());
      }}>取回第 {item.revision} 版内容</button>}
    </li>)}</ol></details>}
    {shown && canLeave && <button type="button" disabled={busy || unknown || draftEditing} onClick={() => { if (onAnother) { onAnother(); return; } readRef.current += 1; setNewItem(true); setExampleId(""); setManualOpen(false); setDraft(freshDraft()); setError(""); setChecks([]); }}>办理另一件事项</button>}
    </fieldset>
    <details className="office-recent" onToggle={event => setRecentOpen(event.currentTarget.open)}>
      <summary>最近事项与暂缓记录</summary>
      <p>显示当前演示身份最近 20 个任务中的事项；读取记录不会继续执行。</p>
      {recentError && <p role="alert">{recentError}</p>}
      <button type="button" onClick={() => setListRefresh(value => value + 1)}>刷新事项列表</button>
      <label>显示范围<select aria-label="最近事项筛选" value={recentFilter} onChange={event => setRecentFilter(event.target.value)}><option value="all">全部事项（{recent.length}）</option><option value="pending">待处理（{pendingCount}）</option></select></label>
      {!recentError && visibleRecent.length === 0 && <p>{recentFilter === "pending" ? "最近记录中没有待处理事项；更早的任务不在此列表内。" : "当前列表中没有可显示的事项。"}</p>}
      <ul>{visibleRecent.map(item => <li key={item.run_id}><button type="button"
        disabled={busy || unknown || blocked || !canLeave || editing || draftEditing}
        aria-current={!newItem && run?.run_id === item.run_id ? "true" : undefined}
        onClick={() => void refresh(item.run_id)}><span>{item.action.input.title}</span>
        <small>{STATE_LABELS[item.action.status] ?? "待核对"} · {item.action.mode}</small></button></li>)}</ul>
      {!canLeave && <p>请先暂缓或结束当前事项，再打开另一件。</p>}
    </details>
  </section>;
}
