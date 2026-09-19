"use client";

import { useEffect, useRef, useState } from "react";

export type ActionInput = {
  operation: "format_text" | "extract_excerpt" | "create_task" | "send_message" | "restricted_action" | "compare_materials";
  title: string; content: string; target: string; due_date: string | null; source_ref: string | null;
  alternative_content?: string;
};
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

export function OfficeActionWorkbench({ run, files, apiBase, headers, onSnapshot, onOpenSource, blocked, readOnly = false }: {
  run: { run_id: string; version: number; office_action: OfficeAction | null } | null;
  files: { file_ref: string; display_label: string; display_path: string }[];
  apiBase: string; headers: Record<string, string>;
  onSnapshot: (value: unknown) => void; onOpenSource: (ref: string) => void; blocked: boolean; readOnly?: boolean;
}) {
  const action = run?.office_action ?? null;
  const [draft, setDraft] = useState<ActionInput>(initial);
  const [editing, setEditing] = useState(false);
  const [newItem, setNewItem] = useState(false);
  const [checks, setChecks] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [unknown, setUnknown] = useState(false);
  const [draftEditing, setDraftEditing] = useState(false);
  const [editedText, setEditedText] = useState("");
  const [choice, setChoice] = useState<"first" | "second" | "">("");
  const [rationale, setRationale] = useState("");
  const [recent, setRecent] = useState<{ run_id: string; action: OfficeAction }[]>([]);
  const [recentError, setRecentError] = useState("");
  const [recentOpen, setRecentOpen] = useState(false);
  const [listRefresh, setListRefresh] = useState(0);
  const pending = useRef<{ url: string; body: string } | null>(null);
  const busyRef = useRef(false);
  const readRef = useRef(0);
  const titleRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    setChecks([]);
    setChoice(""); setRationale(""); setDraftEditing(false);
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
        if (!Array.isArray(payload.runs)) throw new Error("最近事项返回格式不完整。");
        setRecent(payload.runs.flatMap((item: { run_id?: string; office_action?: unknown }) => {
          const current = normalizeOfficeAction(item.office_action);
          return current && typeof item.run_id === "string" ? [{ run_id: item.run_id, action: current }] : [];
        }));
      })
      .catch(caught => { if (!controller.signal.aborted) { setRecent([]); setRecentError(caught instanceof Error ? caught.message : "读取失败"); } });
    return () => controller.abort();
  }, [recentOpen, listRefresh, apiBase, headers, run?.run_id, run?.version]);
  const shown = newItem ? null : action;
  const editable = !shown || editing || shown.status === "needs_input" || shown.status === "stale"
    || (shown.status === "deferred" && shown.missing_fields.length > 0);
  const open = !!shown && OPEN.has(shown.status);
  const canLeave = !open || shown?.status === "deferred";
  const earlier = shown ? [...shown.history].reverse().find(item => item.revision < shown.revision) : null;
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
    if (busyRef.current) return;
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
      if (!response.ok) {
        if (response.status < 500) { pending.current = null; setUnknown(false); }
        if (response.status === 409) {
          setChecks([]);
          await refresh();
        }
        if (response.status >= 500) setUnknown(true);
        throw new Error(typeof payload.detail === "string" ? payload.detail : "请检查填写内容后再提交。");
      }
      if (!normalizeOfficeAction(payload.run?.office_action)) throw new Error("返回内容无法核对，请查询最新状态。");
      onSnapshot(payload); pending.current = null; setUnknown(false); setNewItem(false); setEditing(false); setDraftEditing(false);
      titleRef.current?.focus();
    } catch (caught) {
      if (pending.current) setUnknown(true);
      setError(caught instanceof Error ? caught.message : "请求结果尚未确认。");
    } finally { window.clearTimeout(timer); busyRef.current = false; setBusy(false); }
  }
  async function refresh(runId = run?.run_id) {
    if (!runId) return;
    const readId = ++readRef.current;
    try {
      const response = await fetch(`${apiBase}/v1/harness/runs/${encodeURIComponent(runId)}`, { headers });
      if (!response.ok) throw new Error("暂时无法读取当前事项。");
      const payload = await response.json();
      if (readId !== readRef.current) return;
      if (!normalizeOfficeAction(payload.office_action)) throw new Error("当前事项无法核对。");
      onSnapshot(payload);
      setNewItem(false);
    } catch (caught) { if (readId === readRef.current) setError(caught instanceof Error ? caught.message : "读取失败，请稍后重试。"); }
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
    if (!shown) return;
    const note = [
      shown.input.title, `状态：${STATE_LABELS[shown.status] ?? shown.status}`,
      `内容版本：${shown.revision}`, `处理原因：${shown.reason}`,
      `影响：${shown.impact}`, `恢复范围：${shown.reversibility}`,
      `材料 A / 正文：\n${shown.input.content}`,
      ...(shown.input.alternative_content ? [`材料 B：\n${shown.input.alternative_content}`] : []),
      "请由有权且了解业务的人员核对。本说明仅供交接，未发起审批、未通知他人、未执行外部动作。",
    ].join("\n\n");
    const url = URL.createObjectURL(new Blob([note], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = "人工处理说明.txt"; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <section className="office-actions" aria-label="单步事项">
    <header className="office-action-heading"><div><span>办理一件具体事项</span><h2 ref={titleRef} tabIndex={-1}>{shown ? shown.input.title : "这次需要做什么？"}</h2></div>
      {shown && <button type="button" disabled={busy} onClick={() => void refresh()}>核对最新状态</button>}
    </header>
    <p className="office-action-environment">测试工作区：文本处理保存在本次记录中；协作任务和发件使用测试记录，不连接真实办公系统。</p>
    <details className="office-recent" onToggle={event => setRecentOpen(event.currentTarget.open)}>
      <summary>最近事项与暂缓记录</summary>
      <p>显示当前演示身份最近 20 个任务中的事项；读取记录不会继续执行。</p>
      {recentError && <p role="alert">{recentError}</p>}
      <button type="button" onClick={() => setListRefresh(value => value + 1)}>刷新事项列表</button>
      {!recentError && recent.length === 0 && <p>当前列表中没有可显示的事项。</p>}
      <ul>{recent.map(item => <li key={item.run_id}><button type="button"
        disabled={busy || unknown || blocked || !canLeave || editing || draftEditing}
        aria-current={!newItem && run?.run_id === item.run_id ? "true" : undefined}
        onClick={() => void refresh(item.run_id)}><span>{item.action.input.title}</span>
        <small>{STATE_LABELS[item.action.status] ?? "待核对"} · {item.action.mode}</small></button></li>)}</ul>
      {!canLeave && <p>请先暂缓或结束当前事项，再打开另一件。</p>}
    </details>
    {blocked && <p role="status">当前资料研究任务尚未结束，请先处理该任务或停止后办理新事项。</p>}
    {readOnly && shown && <p role="status">正在核对当前任务指针，或此记录仅供查看。核对通过前不能修改或确认事项。</p>}
    {error && <div className="office-action-error" role="alert"><p>{unknown ? "提交结果尚未确认。请保留本次请求，核对后继续。" : error}</p>{unknown && <><p>{error}</p><button disabled={busy} onClick={() => void send("", {}, true)}>重试同一请求</button></>}</div>}
    {shown && <div className={`office-action-state risk-${shown.risk_level}`} role="status"><span>{shown.risk_level} · {shown.mode}</span><p>{shown.result_message}</p></div>}
    {shown && <div className="office-control-context">
      <span>{editing || draftEditing ? "你正在编辑" : open ? "等待你处理 · Agent 不会自动继续" : shown.status === "draft_ready" ? "草稿已保存，可继续编辑" : "本次处理已结束，结果可查"}</span>
      <p>{shown.autonomy_level} · 第 {shown.revision} 版 · {STATE_LABELS[shown.status] ?? "请核对状态"}</p>
    </div>}
    {shown?.missing_fields.length ? <ul className="office-action-missing">{shown.missing_fields.map(item => <li key={item}>{item}</li>)}</ul> : null}
    <fieldset className="office-action-authority" disabled={readOnly && !!shown}>
    {editable && <form onSubmit={event => { event.preventDefault(); shown ? control("revise") : submit(); }}>
      <fieldset disabled={busy || unknown || blocked}>
        <label>事项类型<select aria-label="事项类型" value={draft.operation} disabled={!!shown} onChange={event => {
          const option = OPERATIONS.find(item => item.value === event.target.value)!;
          setDraft({ operation: option.value, title: option.title, content: option.content, target: "", due_date: null, source_ref: null,
            alternative_content: option.value === "compare_materials" ? "会议记录：评审材料于周五提交，是否替代原邮件尚未确认。" : "" });
        }}>{OPERATIONS.map(item => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label>标题<input aria-label="事项标题" value={draft.title} maxLength={120} required onChange={event => setDraft({ ...draft, title: event.target.value })} /></label>
        {draft.operation === "extract_excerpt" && <label>摘录来源<select aria-label="摘录来源" value={draft.source_ref ?? ""} onChange={event => setDraft({ ...draft, source_ref: event.target.value || null })}><option value="">使用下方填入的文字</option>{files.map(file => <option key={file.file_ref} value={file.file_ref}>{file.display_path || file.display_label}</option>)}</select></label>}
        <label>{draft.source_ref ? "补充说明（不计入摘录）" : "内容"}<textarea aria-label="事项内容" value={draft.content} maxLength={5000} rows={6} onChange={event => setDraft({ ...draft, content: event.target.value })} /></label>
        {draft.operation === "compare_materials" && <><p>上方为材料 A，下方为材料 B。均为你提供的对照内容，系统不自动判断哪份正确。</p><label>材料 B<textarea aria-label="第二份材料" rows={5} maxLength={5000} value={draft.alternative_content ?? ""} onChange={event => setDraft({ ...draft, alternative_content: event.target.value })} /></label></>}
        {["create_task", "send_message"].includes(draft.operation) && <label>{draft.operation === "create_task" ? "负责人" : "收件人"}<select aria-label="办理对象" value={draft.target} onChange={event => setDraft({ ...draft, target: event.target.value })}><option value="">请选择具体联系人</option>{CONTACTS.filter(([id]) => draft.operation !== "create_task" || id !== "client-review").map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label>}
        {draft.operation === "create_task" && <label>截止日期<input type="date" aria-label="截止日期" value={draft.due_date ?? ""} onChange={event => setDraft({ ...draft, due_date: event.target.value || null })} /></label>}
        <div className="office-action-buttons"><button className="primary" type="submit">{busy ? "正在处理" : shown ? "更新内容并重新核对" : "开始办理"}</button>{shown && editing && <button type="button" onClick={() => { setEditing(false); setDraft(shown.input); }}>放弃修改</button>}</div>
      </fieldset>
    </form>}
    {shown && !editable && <>
      {shown.input.operation === "compare_materials" ? <div className="office-comparison" role="group" aria-label="材料对照">
        <article><h3>材料 A · 用户提供</h3><pre>{shown.input.content}</pre></article>
        <article><h3>材料 B · 用户提供</h3><pre>{shown.input.alternative_content}</pre></article>
      </div> : <div className="office-action-preview"><h3>{shown.status === "draft_ready" ? "摘录草稿" : "本次内容"}</h3><p>{shown.target_label}</p>{shown.input.due_date && <p>截止日期：{shown.input.due_date}</p>}<pre>{shown.preview}</pre></div>}
      {shown.status === "draft_ready" && <div className="office-draft-edit">
        {draftEditing ? <form onSubmit={event => { event.preventDefault(); control("edit_draft"); }}>
          <fieldset disabled={busy || unknown}><label>修改内部草稿<textarea aria-label="编辑摘录草稿" rows={8} maxLength={5000} value={editedText} onChange={event => setEditedText(event.target.value)} /></label>
          <p>保存只更新内部草稿。原文继续保留在下方，修改后的内容不再称为逐字摘录。</p>
          <div className="office-action-buttons"><button type="submit" className="primary" disabled={!editedText.trim()}>保存草稿修改</button><button type="button" onClick={() => { setDraftEditing(false); setEditedText(shown.preview); }}>放弃草稿修改</button></div></fieldset>
        </form> : <button disabled={busy || unknown} onClick={() => { setEditedText(shown.preview); setDraftEditing(true); }}>编辑这份草稿</button>}
      </div>}
      {shown.input.operation === "format_text" && <details><summary>查看整理前的内容</summary><pre>{shown.before}</pre></details>}
      <details className="office-risk-lens" open={shown.risk_level === "L4" || shown.risk_level === "L5"}><summary>查看影响与处理依据 · Risk Lens</summary><dl><dt>处理原因</dt><dd>{shown.reason}</dd><dt>将影响什么</dt><dd>{shown.impact}</dd><dt>恢复方式</dt><dd>{shown.reversibility}</dd><dt>内容版本</dt><dd>第 {shown.revision} 版</dd></dl></details>
      {shown.source_excerpt && <details open={draftEditing || undefined}><summary>核对来源：{shown.source_label ?? "用户填写内容"}</summary><pre>{shown.source_excerpt}</pre>{shown.input.source_ref && <button onClick={() => onOpenSource(shown.input.source_ref!)}>打开资料预览</button>}</details>}
      {changes.length > 0 && <details className="office-version-changes"><summary>第 {shown.revision} 版修改了什么（{changes.length} 项）</summary>
        <p>{shown.status === "draft_ready" ? "人工修订与原始摘录分别保留，请按需对照。" : "旧核对不沿用，请按当前内容重新判断。"}</p>
        {changes.map(([label, before, after]) => <div key={label}><h4>{label}</h4><div className="office-comparison">
          <article><span>修改前</span><pre>{before || "未填写"}</pre></article>
          <article><span>当前内容</span><pre>{after || "未填写"}</pre></article>
        </div></div>)}
      </details>}
      {open && !unknown && shown.input.operation === "compare_materials" && <form className="office-decision" onSubmit={event => { event.preventDefault(); control("record_decision"); }}>
        <fieldset disabled={busy}><legend>这次先采用哪份材料？</legend><p>选择只记录本次判断，不证明材料正确，也不会改写原文。</p>
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
    {shown?.decision && <div className="office-decision-result"><h3>你的判断已记录</h3><p>采用材料 {shown.decision.option === "first" ? "A" : "B"}</p><p>判断理由：{shown.decision.rationale}</p><p>这项记录没有修改原材料，也不是业务审批。</p></div>}
    {shown?.receipt && !draftEditing && <div className="office-action-receipt"><h3>结果记录</h3><p>{shown.result_message}</p><p>{new Date(shown.receipt.created_at).toLocaleString("zh-CN")}</p><div className="office-action-buttons"><button type="button" onClick={downloadText}>下载本次内容</button>{shown.input.operation === "format_text" && shown.status === "executed" && <button disabled={busy || unknown} onClick={() => control("undo")}>撤销此次整理</button>}</div></div>}
    {shown?.status === "denied" && <p className="office-action-handoff">请将承诺内容交给有权人员核准。当前工作区未连接正式审批系统。</p>}
    {shown && (shown.status === "denied" || shown.status === "deferred") && <button type="button" onClick={downloadHandoff}>下载人工处理说明</button>}
    {shown && <details className="office-action-history"><summary>查看操作记录（{shown.history.length}）</summary><ol>{shown.history.map((item, index) => <li key={index}><span>第 {item.revision} 版 · {new Date(item.at).toLocaleTimeString("zh-CN")}</span><p>{item.message}</p><details><summary>当时的内容</summary><pre>{item.input.title}{"\n"}{item.input.content}{item.input.alternative_content ? `\n材料 B：\n${item.input.alternative_content}` : ""}</pre>{item.content_snapshot != null && item.content_snapshot !== item.input.content && <><h4>当时的结果 / 草稿</h4><pre>{item.content_snapshot}</pre></>}</details></li>)}</ol></details>}
    {shown && canLeave && <button type="button" disabled={busy || unknown || draftEditing} onClick={() => { setNewItem(true); setDraft(initial()); setError(""); setChecks([]); }}>办理另一件事项</button>}
    </fieldset>
  </section>;
}
