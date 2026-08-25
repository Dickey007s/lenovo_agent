"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconCheck,
  IconChevronDown,
  IconCircleCheck,
  IconCircleDot,
  IconClock,
  IconDatabase,
  IconFile,
  IconFileDescription,
  IconFileSpreadsheet,
  IconLoader2,
  IconRefresh,
  IconRoute,
  IconSearch,
  IconSend,
  IconShieldCheck,
  IconSparkles,
} from "@tabler/icons-react";

type ConnectionState = "connecting" | "available" | "live" | "reconnecting" | "offline";
type CatalogStatus = "checking" | "retrying" | "online" | "unavailable";
type CatalogFailureKind = "service_unreachable" | "catalog_unavailable" | "catalog_invalid";
type WorkspaceView = "data" | "plan" | "result";

export type HarnessFile = {
  key: string;
  file_ref: string;
  display_label: string;
  display_group: string;
  display_summary: string;
};

export type HarnessWorkProfile = {
  task_topology: "single_task" | "multi_task";
  orchestration: "bounded_loop" | "adaptive_swarm";
  control_requirements: ("evidence_gate" | "human_gate" | "risk_gate")[];
  current_runtime_scope: "read_only_analysis";
};

export type HarnessScenario = {
  scenario_id: string;
  work_profile: HarnessWorkProfile;
  title: string;
  goal: string;
  dataset_label: string;
  dataset_version: string;
  files: HarnessFile[];
  data_boundary?: string;
  human_gate_summary?: string;
};

type HarnessPreview = {
  scenario_id: string;
  file_ref: string;
  display_label: string;
  display_group: string;
  display_summary: string;
  kind: "table" | "markdown";
  sheet_name: string | null;
  columns: string[];
  rows: { row_number: number; values: string[] }[];
  total_rows: number | null;
  text: string | null;
  truncated: boolean;
};

export type HarnessPlanNode = {
  node_id: string;
  label: string;
  description: string;
  depends_on: string[];
  source_refs: string[];
  allowed_tools: string[];
  needs_human: boolean;
};

type ModelReceipt = { called: boolean; model: string; elapsed_ms: number; output_used: boolean };
type HarnessFinding = { title: string; detail: string; file_refs: string[] };
type HarnessResult = { summary: string; findings: HarnessFinding[]; follow_ups: string[]; review_required: boolean };
type HarnessServerEvent = { sequence: number; event_name: string; occurred_at?: string; status?: string; message?: string };

export type HarnessRun = {
  run_id: string;
  scenario_id: string;
  status: string;
  version: number;
  last_event_sequence: number;
  instruction: string;
  instruction_source: "dataset_task" | "user";
  source_documents: HarnessFile[];
  plan: HarnessPlanNode[];
  plan_summary?: string;
  model_receipt: ModelReceipt | null;
  analysis_receipt: ModelReceipt | null;
  result: HarnessResult | null;
  validation_errors: string[];
  events: HarnessActivityItem[];
};

export type HarnessActivityItem = {
  sequence: number;
  label: string;
  detail: string;
  occurred_at?: string;
  tone: "neutral" | "model" | "success" | "warning";
};

export type HarnessActivityState = {
  scenarioTitle: string;
  instruction: string | null;
  runStatus: string | null;
  connection: ConnectionState;
  planningReceipt: ModelReceipt | null;
  analysisReceipt: ModelReceipt | null;
  events: HarnessActivityItem[];
  resultReady: boolean;
  error: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010";
const HEADERS = { "Content-Type": "application/json", "X-User-Id": "demo_user" };
const NAMED_EVENTS = [
  "workspace_index", "planning_started", "planning_completed", "plan_validation",
  "ready_to_execute", "analysis_started", "analysis_completed", "result_validation",
  "task_completed", "harness_failed",
];
const TERMINAL_EVENTS = new Set(["ready_to_execute", "task_completed", "harness_failed"]);
const TERMINAL_STATUSES = new Set(["ready_to_execute", "completed", "failed"]);
const COLLECTION_LABELS: Record<string, string> = {
  "Finance-018": "财务证据", "pm-014": "上线核对", "Operations-008": "运营规则",
};
const COLLECTION_HINTS: Record<string, string> = {
  "Finance-018": "跨期往来与余额", "pm-014": "配置、测试与发布资料", "Operations-008": "外呼规则与人工边界",
};
const EXAMPLE_TASKS: Record<string, string> = {
  "Finance-018": "找出三个期间期末余额完全不变的往来项，并说明依据。",
  "pm-014": "核对当前版本是否满足上线条件，列出未通过项和引用文件。",
  "Operations-008": "检查规则中哪些情况必须转人工，并按触发条件归类。",
};

function asText(value: unknown, fallback = "") { return typeof value === "string" ? value : fallback; }
function asStrings(value: unknown) { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }
class CatalogLoadError extends Error { constructor(public kind: CatalogFailureKind) { super(kind); } }
async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 5_000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try { return await fetch(input, { ...init, signal: controller.signal }); }
  finally { window.clearTimeout(timer); }
}

function normalizeFiles(value: unknown): HarnessFile[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item, index) => {
    if (!item || typeof item !== "object") return [];
    const raw = item as Record<string, unknown>;
    const fileRef = asText(raw.file_ref); const label = asText(raw.display_label);
    const group = asText(raw.display_group); const summary = asText(raw.display_summary);
    if (!fileRef || !label || !group || !summary) return [];
    return [{ key: `${fileRef}:${index}`, file_ref: fileRef, display_label: label, display_group: group, display_summary: summary }];
  });
}

function normalizeWorkProfile(value: unknown): HarnessWorkProfile | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const taskTopology = asText(raw.task_topology);
  const orchestration = asText(raw.orchestration);
  const controlRequirements = asStrings(raw.control_requirements);
  const runtimeScope = asText(raw.current_runtime_scope);
  const validControls = new Set(["evidence_gate", "human_gate", "risk_gate"]);
  if (
    !["single_task", "multi_task"].includes(taskTopology)
    || !["bounded_loop", "adaptive_swarm"].includes(orchestration)
    || !controlRequirements.length
    || controlRequirements.some((item) => !validControls.has(item))
    || runtimeScope !== "read_only_analysis"
  ) return null;
  return {
    task_topology: taskTopology as HarnessWorkProfile["task_topology"],
    orchestration: orchestration as HarnessWorkProfile["orchestration"],
    control_requirements: controlRequirements as HarnessWorkProfile["control_requirements"],
    current_runtime_scope: "read_only_analysis",
  };
}

function normalizeScenario(value: unknown): HarnessScenario | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const scenarioId = asText(raw.scenario_id);
  const workProfile = normalizeWorkProfile(raw.work_profile);
  const files = normalizeFiles(raw.files);
  if (!scenarioId || !workProfile || !files.length) return null;
  return {
    scenario_id: scenarioId, work_profile: workProfile, title: asText(raw.title, COLLECTION_LABELS[scenarioId] ?? "办公资料"),
    goal: asText(raw.goal, "查看公开办公资料并形成可核对结论。"),
    dataset_label: asText(raw.dataset_label, "FORTE 公开办公基准数据"),
    dataset_version: asText(raw.dataset_version, "FORTE 公开版本"), files,
    data_boundary: asText(raw.data_boundary) || undefined,
    human_gate_summary: asText(raw.human_gate_summary) || undefined,
  };
}

function normalizePreview(value: unknown): HarnessPreview | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>; const kind = asText(raw.kind);
  if (!asText(raw.file_ref) || !["table", "markdown"].includes(kind)) return null;
  const rows = Array.isArray(raw.rows) ? raw.rows.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    return typeof row.row_number === "number" && Array.isArray(row.values) ? [{ row_number: row.row_number, values: asStrings(row.values) }] : [];
  }) : [];
  return {
    scenario_id: asText(raw.scenario_id), file_ref: asText(raw.file_ref),
    display_label: asText(raw.display_label), display_group: asText(raw.display_group),
    display_summary: asText(raw.display_summary), kind: kind as HarnessPreview["kind"],
    sheet_name: asText(raw.sheet_name) || null, columns: asStrings(raw.columns), rows,
    total_rows: typeof raw.total_rows === "number" ? raw.total_rows : null,
    text: typeof raw.text === "string" ? raw.text : null, truncated: raw.truncated === true,
  };
}

function normalizeReceipt(value: unknown): ModelReceipt | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  return { called: raw.called === true, model: asText(raw.model), elapsed_ms: typeof raw.elapsed_ms === "number" ? raw.elapsed_ms : 0, output_used: raw.output_used === true };
}

function normalizeResult(value: unknown): HarnessResult | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const findings = Array.isArray(raw.findings) ? raw.findings.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const finding = item as Record<string, unknown>; const title = asText(finding.title);
    const detail = asText(finding.detail); const fileRefs = asStrings(finding.file_refs);
    return title && detail && fileRefs.length ? [{ title, detail, file_refs: fileRefs }] : [];
  }) : [];
  const summary = asText(raw.summary); if (!summary || !findings.length) return null;
  return { summary, findings, follow_ups: asStrings(raw.follow_ups), review_required: raw.review_required === true };
}

function activityItem(event: HarnessServerEvent): HarnessActivityItem {
  const labels: Record<string, string> = {
    workspace_index: "已锁定所选文件", planning_started: "规划模型开始组织任务",
    planning_completed: "规划模型返回工作图", plan_validation: "服务端校验工作图",
    ready_to_execute: "工作图已准备", analysis_started: "分析模型开始读取内容",
    analysis_completed: "分析模型返回结果", result_validation: "服务端核对文件引用",
    task_completed: "初步结果已形成", harness_failed: "本轮已安全停止",
  };
  const tone = event.event_name === "harness_failed" ? "warning"
    : event.event_name.includes("planning") || event.event_name.includes("analysis") ? "model"
      : event.event_name.includes("validation") || event.event_name === "task_completed" || event.event_name === "ready_to_execute" ? "success" : "neutral";
  return { sequence: event.sequence, label: labels[event.event_name] ?? "服务端状态已更新", detail: event.message ?? "本轮状态来自服务端回执。", occurred_at: event.occurred_at, tone };
}

function normalizeRun(value: unknown): HarnessRun | null {
  if (!value || typeof value !== "object") return null;
  const outer = value as Record<string, unknown>;
  const raw = outer.run && typeof outer.run === "object" ? outer.run as Record<string, unknown> : outer;
  const runId = asText(raw.run_id); const scenarioId = asText(raw.scenario_id);
  if (!runId || !scenarioId) return null;
  const planRaw = raw.plan && typeof raw.plan === "object" ? raw.plan as Record<string, unknown> : null;
  const plan = Array.isArray(planRaw?.units) ? planRaw.units.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const unit = item as Record<string, unknown>; const nodeId = asText(unit.unit_id);
    if (!nodeId) return [];
    return [{ node_id: nodeId, label: asText(unit.title, "工作单元"), description: asText(unit.objective), depends_on: asStrings(unit.depends_on), source_refs: asStrings(unit.input_file_refs), allowed_tools: unit.tool ? [asText(unit.tool)] : [], needs_human: unit.requires_human_gate === true }];
  }) : [];
  const serverEvents = Array.isArray(raw.events) ? raw.events.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const event = item as Record<string, unknown>;
    if (typeof event.sequence !== "number" || !asText(event.event_name)) return [];
    return [{ sequence: event.sequence, event_name: asText(event.event_name), occurred_at: asText(event.occurred_at) || undefined, status: asText(event.status) || undefined, message: asText(event.message) || undefined } satisfies HarnessServerEvent];
  }) : [];
  return {
    run_id: runId, scenario_id: scenarioId, status: asText(raw.status, "queued"),
    version: typeof raw.version === "number" ? raw.version : 1,
    last_event_sequence: typeof raw.last_event_sequence === "number" ? raw.last_event_sequence : 0,
    instruction: asText(raw.instruction), instruction_source: raw.instruction_source === "user" ? "user" : "dataset_task",
    source_documents: normalizeFiles(raw.source_documents), plan,
    plan_summary: planRaw ? asText(planRaw.summary) || undefined : undefined,
    model_receipt: normalizeReceipt(raw.model_receipt), analysis_receipt: normalizeReceipt(raw.analysis_receipt),
    result: normalizeResult(raw.result), validation_errors: asStrings(raw.validation_errors),
    events: serverEvents.map(activityItem).sort((a, b) => a.sequence - b.sequence),
  };
}

function toolLabel(tool: string) {
  const labels: Record<string, string> = { "file.read": "读取文件", "table.inspect": "检查表格", "artifact.write": "组织工作成果", "evidence.verify": "核对证据", "action.preview": "预演受控动作" };
  return labels[tool] ?? "受控办公工具";
}

function Receipt({ receipt, label }: { receipt: ModelReceipt | null; label: string }) {
  if (!receipt) return null;
  const status = !receipt.called ? "未调用" : receipt.output_used ? "已采用" : "校验未通过";
  const explanation = !receipt.called
    ? "本轮没有发起模型请求"
    : receipt.output_used
      ? "模型返回结果已通过服务端校验并进入下一步"
      : "模型已经返回结果，但结果没有通过服务端校验，未进入下一步";
  return <div className="trace-receipt"><IconSparkles aria-hidden="true" /><div><strong>{label}</strong><span>{receipt.called ? `${receipt.model} · ${(receipt.elapsed_ms / 1000).toFixed(1)} 秒` : "模型未调用"}</span></div><b className={receipt.output_used ? "is-used" : "is-rejected"} title={explanation} aria-label={`${label}：${status}。${explanation}`}>{status}</b></div>;
}

export function HarnessActivityPane({ state }: { state: HarnessActivityState | null }) {
  if (!state) return <section className="trace-pane is-empty"><IconRoute aria-hidden="true" /><h2>执行轨迹</h2><p>提交一个任务后，这里会按服务端事件显示 Agent 做了什么。</p></section>;
  return <section className="trace-pane" aria-labelledby="trace-title">
    <header><div className="trace-avatar"><IconSparkles aria-hidden="true" /></div><div><span>可核对的 Agent 路径</span><h2 id="trace-title">执行轨迹</h2></div><b className={`is-${state.connection}`}><i />{state.connection === "live" ? "实时" : state.connection === "available" ? "可用" : state.connection === "reconnecting" ? "重连" : state.connection === "offline" ? "离线" : "连接"}</b></header>
    {state.instruction && <div className="trace-task"><span>本轮任务</span><p>{state.instruction}</p></div>}
    <div className="trace-receipts"><Receipt receipt={state.planningReceipt} label="规划调用" /><Receipt receipt={state.analysisReceipt} label="分析调用" /></div>
    <ol className="trace-list" aria-live="polite" aria-relevant="additions text">{state.events.length ? state.events.map((item) => <li key={item.sequence} className={`is-${item.tone}`}><span>{item.tone === "model" ? <IconSparkles aria-hidden="true" /> : item.tone === "success" ? <IconCheck aria-hidden="true" /> : item.tone === "warning" ? <IconAlertTriangle aria-hidden="true" /> : <IconCircleDot aria-hidden="true" />}</span><div><strong>{item.label}</strong><p>{item.detail}</p>{item.occurred_at && <small>{new Date(item.occurred_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</small>}</div></li>) : <li><span><IconClock aria-hidden="true" /></span><div><strong>等待任务</strong><p>选择文件并输入任务，轨迹会从读取开始。</p></div></li>}</ol>
    {state.resultReady && <footer className="is-success"><IconCircleCheck aria-hidden="true" /><span>只读结果已形成，等待你的复核</span></footer>}
    {state.error && <footer className="is-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{state.error}</span></footer>}
  </section>;
}

export function HarnessWorkbench({ onActivityChange }: { onActivityChange?: (state: HarnessActivityState | null) => void }) {
  const [scenarios, setScenarios] = useState<HarnessScenario[]>([]);
  const [scenarioId, setScenarioId] = useState(""); const [selectedRefs, setSelectedRefs] = useState<string[]>([]);
  const [activeFileRef, setActiveFileRef] = useState(""); const [preview, setPreview] = useState<HarnessPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false); const [previewError, setPreviewError] = useState("");
  const [query, setQuery] = useState(""); const [fileSearch, setFileSearch] = useState("");
  const [expanded, setExpanded] = useState<Record<string, boolean>>({}); const [view, setView] = useState<WorkspaceView>("data");
  const [run, setRun] = useState<HarnessRun | null>(null); const [activity, setActivity] = useState<HarnessActivityItem[]>([]);
  const [catalogStatus, setCatalogStatus] = useState<CatalogStatus>("checking");
  const [catalogFailureKind, setCatalogFailureKind] = useState<CatalogFailureKind | null>(null);
  const [catalogError, setCatalogError] = useState(""); const [starting, setStarting] = useState(false);
  const [error, setError] = useState(""); const [connection, setConnection] = useState<ConnectionState>("connecting");
  const eventSourceRef = useRef<EventSource | null>(null); const reconnectTimerRef = useRef<number | undefined>(undefined);
  const retryTimerRef = useRef<number | undefined>(undefined); const catalogAttemptRef = useRef(0); const requestRef = useRef(0);
  const previewRequestRef = useRef(0);
  const generationRef = useRef(0); const runRef = useRef<HarnessRun | null>(null); const lastSequenceRef = useRef(0);
  const startCommandRef = useRef<{ signature: string; key: string } | null>(null);
  const scenario = scenarios.find((item) => item.scenario_id === scenarioId) ?? null;
  const activeFile = scenarios.flatMap((item) => item.files).find((item) => item.file_ref === activeFileRef) ?? null;

  function closeTransport() { eventSourceRef.current?.close(); eventSourceRef.current = null; window.clearTimeout(reconnectTimerRef.current); reconnectTimerRef.current = undefined; }
  function applySnapshot(snapshot: HarnessRun, generation: number) {
    if (generation !== generationRef.current) return false;
    const current = runRef.current;
    if (current && current.run_id !== snapshot.run_id) return false;
    if (snapshot.last_event_sequence < lastSequenceRef.current || (current && snapshot.version < current.version)) return false;
    runRef.current = snapshot; lastSequenceRef.current = Math.max(lastSequenceRef.current, snapshot.last_event_sequence);
    setRun(snapshot); setActivity(snapshot.events.slice(-30)); if (snapshot.status === "completed") setView("result"); return true;
  }
  async function readSnapshot(runId: string, generation: number) {
    const response = await fetch(`${API_BASE}/v1/harness/runs/${encodeURIComponent(runId)}`, { headers: HEADERS });
    if (!response.ok) throw new Error(`任务状态读取失败（${response.status}）`);
    const snapshot = normalizeRun(await response.json() as unknown); if (!snapshot) throw new Error("服务端返回的任务状态无效");
    applySnapshot(snapshot, generation);
  }
  function connectStream(runId: string, generation: number) {
    if (generation !== generationRef.current) return; closeTransport();
    if (runRef.current?.run_id === runId && TERMINAL_STATUSES.has(runRef.current.status)) { setConnection("available"); return; }
    setConnection("connecting");
    const source = new EventSource(`${API_BASE}/v1/harness/runs/${encodeURIComponent(runId)}/events?after=${lastSequenceRef.current}`);
    eventSourceRef.current = source;
    const receive = (raw: Event, name: string) => {
      if (generation !== generationRef.current || eventSourceRef.current !== source || runRef.current?.run_id !== runId) return;
      try {
        const parsed = JSON.parse((raw as MessageEvent<string>).data) as HarnessServerEvent;
        if (parsed.sequence <= lastSequenceRef.current) return;
        lastSequenceRef.current = parsed.sequence; const item = activityItem({ ...parsed, event_name: name });
        setActivity((current) => [...current.filter((entry) => entry.sequence !== item.sequence), item].sort((a, b) => a.sequence - b.sequence).slice(-30)); setConnection("live");
        if (TERMINAL_EVENTS.has(name)) { source.close(); eventSourceRef.current = null; setConnection("available"); void readSnapshot(runId, generation).catch(() => setConnection("offline")); return; }
        void readSnapshot(runId, generation).catch(() => setConnection("reconnecting"));
      } catch { setConnection("reconnecting"); }
    };
    NAMED_EVENTS.forEach((name) => source.addEventListener(name, (event) => receive(event, name)));
    source.onopen = () => setConnection("live");
    source.onerror = () => {
      if (generation !== generationRef.current || eventSourceRef.current !== source) return;
      source.close(); eventSourceRef.current = null; setConnection("reconnecting");
      void readSnapshot(runId, generation).catch(() => setConnection("offline")).finally(() => {
        if (generation !== generationRef.current || runRef.current?.run_id !== runId || TERMINAL_STATUSES.has(runRef.current.status)) return;
        reconnectTimerRef.current = window.setTimeout(() => connectStream(runId, generation), 900);
      });
    };
  }

  async function loadScenarios(manual = false) {
    const request = requestRef.current + 1; requestRef.current = request; window.clearTimeout(retryTimerRef.current);
    if (manual) catalogAttemptRef.current = 0; const attempt = catalogAttemptRef.current + 1; catalogAttemptRef.current = attempt;
    setCatalogStatus(attempt === 1 ? "checking" : "retrying"); setCatalogError("");
    try {
      let health: Response; try { health = await fetchWithTimeout(`${API_BASE}/v1/health`, { headers: HEADERS }); } catch { throw new CatalogLoadError("service_unreachable"); }
      if (!health.ok) throw new CatalogLoadError("service_unreachable");
      const response = await fetchWithTimeout(`${API_BASE}/v1/harness/scenarios`, { headers: HEADERS });
      if (!response.ok) { const detail = await response.json().then((body: unknown) => body && typeof body === "object" ? asText((body as Record<string, unknown>).detail) : "").catch(() => ""); throw new CatalogLoadError(detail.includes("完整性") ? "catalog_invalid" : "catalog_unavailable"); }
      const body = await response.json() as unknown;
      const raw = body && typeof body === "object" && Array.isArray((body as { scenarios?: unknown[] }).scenarios) ? (body as { scenarios: unknown[] }).scenarios : [];
      const normalized = raw.flatMap((item) => { const value = normalizeScenario(item); return value ? [value] : []; }).filter((item) => item.dataset_label.toUpperCase().includes("FORTE"));
      if (normalized.length !== 3) throw new CatalogLoadError("catalog_invalid"); if (request !== requestRef.current) return;
      setScenarios(normalized); const first = normalized[0];
      setScenarioId((current) => current && normalized.some((item) => item.scenario_id === current) ? current : first.scenario_id);
      setSelectedRefs((current) => current.length ? current : first.files.map((file) => file.file_ref));
      setActiveFileRef((current) => current || first.files[0].file_ref); setQuery((current) => current || EXAMPLE_TASKS[first.scenario_id]);
      catalogAttemptRef.current = 0; setCatalogStatus("online"); setCatalogFailureKind(null); setConnection("available");
    } catch (reason) {
      if (request !== requestRef.current) return; const kind = reason instanceof CatalogLoadError ? reason.kind : "service_unreachable"; const unavailable = attempt >= 3;
      setCatalogFailureKind(kind); setCatalogStatus(unavailable ? "unavailable" : "retrying");
      setCatalogError(unavailable ? kind === "service_unreachable" ? "无法连接办公服务，系统会继续自动重试。" : kind === "catalog_invalid" ? "FORTE 目录未通过完整性检查。" : "FORTE 目录暂时无法读取。" : "");
      setConnection(kind === "service_unreachable" ? unavailable ? "offline" : "reconnecting" : "available");
      retryTimerRef.current = window.setTimeout(() => void loadScenarios(), [650, 1200, 2500, 5000][Math.min(attempt - 1, 3)]);
    }
  }

  useEffect(() => { void loadScenarios(); return () => { requestRef.current += 1; previewRequestRef.current += 1; window.clearTimeout(retryTimerRef.current); closeTransport(); }; }, []);
  useEffect(() => {
    if (!scenario || !activeFileRef) return; const request = previewRequestRef.current + 1; previewRequestRef.current = request;
    setPreviewLoading(true); setPreviewError(""); setPreview(null);
    void fetchWithTimeout(`${API_BASE}/v1/harness/scenarios/${encodeURIComponent(scenario.scenario_id)}/files/${encodeURIComponent(activeFileRef)}`, { headers: HEADERS })
      .then(async (response) => { if (!response.ok) throw new Error(`文件预览读取失败（${response.status}）`); const normalized = normalizePreview(await response.json() as unknown); if (!normalized) throw new Error("文件预览格式无效"); return normalized; })
      .then((value) => { if (request === previewRequestRef.current) setPreview(value); })
      .catch((reason) => { if (request === previewRequestRef.current) setPreviewError(reason instanceof Error ? reason.message : "文件预览读取失败"); })
      .finally(() => { if (request === previewRequestRef.current) setPreviewLoading(false); });
  }, [activeFileRef, scenario]);

  function chooseScenario(next: HarnessScenario, fileRef?: string) {
    generationRef.current += 1; closeTransport(); runRef.current = null; lastSequenceRef.current = 0; startCommandRef.current = null;
    setRun(null); setActivity([]); setError(""); setScenarioId(next.scenario_id); setSelectedRefs(next.files.map((file) => file.file_ref));
    setActiveFileRef(fileRef ?? next.files[0].file_ref); setQuery(EXAMPLE_TASKS[next.scenario_id]); setView("data");
  }
  function openCollection(next: HarnessScenario) {
    if (next.scenario_id !== scenarioId) {
      setExpanded((current) => ({ ...current, [next.scenario_id]: true }));
      chooseScenario(next);
      return;
    }
    setExpanded((current) => ({ ...current, [next.scenario_id]: !(current[next.scenario_id] ?? true) }));
  }
  function openFile(owner: HarnessScenario, file: HarnessFile) { if (owner.scenario_id !== scenarioId) chooseScenario(owner, file.file_ref); else { setActiveFileRef(file.file_ref); setView("data"); } }
  function toggleFile(fileRef: string) { setSelectedRefs((current) => current.includes(fileRef) ? current.length === 1 ? current : current.filter((item) => item !== fileRef) : [...current, fileRef]); startCommandRef.current = null; }

  async function startRun() {
    if (!scenario || starting || query.trim().length < 3 || !selectedRefs.length) return;
    const signature = JSON.stringify({ scenario: scenario.scenario_id, instruction: query.trim(), files: selectedRefs });
    const terminalRun = run?.status === "completed" || run?.status === "failed" || run?.status === "ready_to_execute";
    const command = startCommandRef.current?.signature === signature && !terminalRun ? startCommandRef.current : { signature, key: `harness:${crypto.randomUUID()}` };
    startCommandRef.current = command; generationRef.current += 1; const generation = generationRef.current;
    closeTransport(); runRef.current = null; lastSequenceRef.current = 0; setRun(null); setActivity([]); setError(""); setStarting(true);
    try {
      const response = await fetch(`${API_BASE}/v1/harness/runs`, { method: "POST", headers: HEADERS, body: JSON.stringify({ scenario_id: scenario.scenario_id, idempotency_key: command.key, expected_version: 1, instruction: query.trim(), selected_file_refs: selectedRefs }) });
      if (!response.ok) throw new Error(`任务启动结果未知（${response.status}），重试会复用同一命令`);
      const snapshot = normalizeRun(await response.json() as unknown); if (!snapshot) throw new Error("任务启动结果无效");
      if (applySnapshot(snapshot, generation)) connectStream(snapshot.run_id, generation);
    } catch (reason) { if (generation === generationRef.current) { setError(reason instanceof Error ? reason.message : "任务启动结果未知"); setConnection("offline"); } }
    finally { if (generation === generationRef.current) setStarting(false); }
  }
  function reconnect() { if (!run) { void loadScenarios(true); return; } const generation = generationRef.current; closeTransport(); void readSnapshot(run.run_id, generation).finally(() => connectStream(run.run_id, generation)); }

  const activityState = useMemo<HarnessActivityState>(() => ({ scenarioTitle: scenario?.title ?? "FORTE 数据任务", instruction: run?.instruction ?? null, runStatus: run?.status ?? null, connection, planningReceipt: run?.model_receipt ?? null, analysisReceipt: run?.analysis_receipt ?? null, events: activity, resultReady: run?.status === "completed" && Boolean(run.result), error: run?.status === "failed" ? run.validation_errors[0] ?? "本轮已安全停止" : error || catalogError || null }), [activity, catalogError, connection, error, run, scenario?.title]);
  useEffect(() => { onActivityChange?.(activityState); }, [activityState, onActivityChange]); useEffect(() => () => onActivityChange?.(null), [onActivityChange]);
  const filteredScenarios = useMemo(() => { const needle = fileSearch.trim().toLowerCase(); if (!needle) return scenarios; return scenarios.map((item) => ({ ...item, files: item.files.filter((file) => `${file.display_label} ${file.display_group}`.toLowerCase().includes(needle)) })).filter((item) => item.files.length); }, [fileSearch, scenarios]);
  const runFiles = run?.source_documents.length ? run.source_documents : scenario?.files ?? [];
  const runInProgress = Boolean(run && ["queued", "indexing", "planning", "validating", "analyzing", "verifying"].includes(run.status));
  const runButtonLabel = starting ? "正在启动" : runInProgress ? "Agent 处理中" : run?.status === "failed" ? "重新规划" : run?.status === "completed" || run?.status === "ready_to_execute" ? "再次运行" : "运行任务";

  if (catalogStatus !== "online" && !scenarios.length) return <section className={`data-workbench-empty ${catalogStatus === "unavailable" ? "is-error" : ""}`} role={catalogStatus === "unavailable" ? "alert" : "status"}>{catalogStatus === "unavailable" ? <IconAlertTriangle aria-hidden="true" /> : <IconLoader2 aria-hidden="true" />}<h1>{catalogStatus === "unavailable" ? catalogFailureKind === "service_unreachable" ? "办公服务暂时离线" : "FORTE 数据暂时不可用" : "正在读取 FORTE 数据"}</h1><p>{catalogError || "正在校验公开数据目录与文件完整性。"}</p>{catalogStatus === "unavailable" && <button type="button" onClick={() => void loadScenarios(true)}>重新读取</button>}</section>;

  return <section className="data-workbench" aria-label="FORTE 数据工作台">
    <header className="data-workbench-header"><div><span>公开办公数据</span><h1>FORTE 数据工作台</h1><p>浏览真实基准文件，选择上下文，再把任务交给 Agent。</p></div><div className="data-workbench-status"><b className={`is-${connection}`}><i />{connection === "live" ? "轨迹实时" : connection === "available" ? "服务可用" : connection === "reconnecting" ? "正在重连" : connection === "offline" ? "暂时离线" : "连接中"}</b><button type="button" className="icon-action" onClick={reconnect} aria-label="重新连接" title="重新连接"><IconRefresh aria-hidden="true" /></button></div></header>
    <div className="data-workbench-grid"><aside className="dataset-browser" aria-label="FORTE 数据目录"><header><div><IconDatabase aria-hidden="true" /><div><strong>基准资料</strong><span>{scenarios.reduce((total, item) => total + item.files.length, 0)} 份公开文件</span></div></div><label><IconSearch aria-hidden="true" /><input value={fileSearch} onChange={(event) => setFileSearch(event.target.value)} placeholder="查找文件" aria-label="查找文件" /></label></header><div className="dataset-tree">{filteredScenarios.map((item) => <section key={item.scenario_id} className={item.scenario_id === scenarioId ? "is-active" : ""}><button type="button" className="dataset-group" onClick={() => openCollection(item)} aria-expanded={expanded[item.scenario_id] ?? true}><IconChevronDown className={(expanded[item.scenario_id] ?? true) ? "is-open" : ""} aria-hidden="true" /><div><strong>{COLLECTION_LABELS[item.scenario_id] ?? item.title}</strong><span>{COLLECTION_HINTS[item.scenario_id] ?? item.goal}</span></div><b>{item.files.length}</b></button>{(expanded[item.scenario_id] ?? true) && <div className="dataset-files">{item.files.map((file) => <div key={file.file_ref} className={file.file_ref === activeFileRef ? "is-open" : ""}><label title={item.scenario_id === scenarioId ? "纳入本轮上下文" : "打开后切换资料集"}><input type="checkbox" checked={item.scenario_id === scenarioId && selectedRefs.includes(file.file_ref)} onChange={() => item.scenario_id === scenarioId ? toggleFile(file.file_ref) : chooseScenario(item, file.file_ref)} /><span aria-hidden="true"><IconCheck /></span></label><button type="button" onClick={() => openFile(item, file)}><IconFile aria-hidden="true" /><span>{file.display_label}</span></button></div>)}</div>}</section>)}</div></aside>
      <main className="data-task-surface"><section className="task-composer" aria-labelledby="task-composer-title"><div><span>给 Agent 一个任务</span><h2 id="task-composer-title">你想从这些数据里知道什么？</h2></div><textarea aria-label="你想从这些数据里知道什么？" value={query} onChange={(event) => { setQuery(event.target.value); startCommandRef.current = null; }} maxLength={2000} rows={3} placeholder="例如：找出三期都没有变化的往来项，并给出引用文件。" /><footer><span>{selectedRefs.length} 份文件已选 · 只读分析，不会修改原数据</span><button type="button" onClick={() => void startRun()} disabled={!scenario || starting || runInProgress || query.trim().length < 3 || !selectedRefs.length}>{starting || runInProgress ? <IconLoader2 aria-hidden="true" /> : <IconSend aria-hidden="true" />}{runButtonLabel}</button></footer></section>
        <nav className="workspace-tabs" aria-label="工作台视图"><button type="button" className={view === "data" ? "is-active" : ""} onClick={() => setView("data")}><IconFileSpreadsheet aria-hidden="true" />数据预览</button><button type="button" className={view === "plan" ? "is-active" : ""} onClick={() => setView("plan")} disabled={!run?.plan.length}><IconRoute aria-hidden="true" />任务计划{run?.plan.length ? <b>{run.plan.length}</b> : null}</button><button type="button" className={view === "result" ? "is-active" : ""} onClick={() => setView("result")} disabled={!run?.result}><IconFileDescription aria-hidden="true" />分析结果</button></nav>
        <section className="workspace-content">{view === "data" && <FilePreview preview={preview} file={activeFile} loading={previewLoading} error={previewError} />}{view === "plan" && <PlanView run={run} files={runFiles} />}{view === "result" && <ResultView key={run?.run_id ?? "empty"} result={run?.result ?? null} files={runFiles} />}</section>
        <details className="workspace-boundary"><summary><IconShieldCheck aria-hidden="true" />本轮边界</summary><p>{scenario?.data_boundary ?? "只读取所选 FORTE 公开输入，不访问真实企业系统。"}</p><p>{scenario?.human_gate_summary ?? "任何外部动作都不在本轮只读分析范围内。"}</p></details>
      </main></div>
  </section>;
}

function FilePreview({ preview, file, loading, error }: { preview: HarnessPreview | null; file: HarnessFile | null; loading: boolean; error: string }) {
  if (loading) return <div className="file-preview-empty" role="status"><IconLoader2 aria-hidden="true" /><strong>正在读取文件内容</strong></div>;
  if (error) return <div className="file-preview-empty is-error" role="alert"><IconAlertTriangle aria-hidden="true" /><strong>{error}</strong></div>;
  if (!preview || !file) return <div className="file-preview-empty"><IconFile aria-hidden="true" /><strong>从左侧选择一份文件</strong></div>;
  return <div className="file-preview"><header><div><span>{preview.display_group}</span><h2>{preview.display_label}</h2><p>{preview.display_summary}</p></div>{preview.kind === "table" && <b>{preview.total_rows ?? preview.rows.length} 行 · {preview.columns.length} 列</b>}</header>{preview.kind === "markdown" ? <article className="markdown-preview">{preview.text}</article> : <div className="table-preview" tabIndex={0} aria-label={`${preview.display_label} 表格内容`}><table><thead><tr><th className="row-number">#</th>{preview.columns.map((column, index) => <th key={`${column}:${index}`}>{column}</th>)}</tr></thead><tbody>{preview.rows.map((row) => <tr key={row.row_number}><th className="row-number">{row.row_number}</th>{preview.columns.map((_, index) => <td key={index}>{row.values[index] ?? ""}</td>)}</tr>)}</tbody></table></div>}{preview.truncated && <footer>当前显示安全预览范围，文件仍由服务端完整校验。</footer>}</div>;
}

function PlanView({ run, files }: { run: HarnessRun | null; files: HarnessFile[] }) {
  if (!run?.plan.length) return <div className="workspace-placeholder"><IconRoute aria-hidden="true" /><h2>任务计划尚未形成</h2><p>运行任务后，模型计划与服务端校验结果会出现在这里。</p></div>;
  return <div className="plan-view"><header><span>已校验的工作图</span><h2>{run.plan_summary ?? `${run.plan.length} 个工作步骤`}</h2></header><ol>{run.plan.map((node, index) => <li key={node.node_id}><b>{index + 1}</b><div><strong>{node.label}</strong><p>{node.description}</p><footer>{node.source_refs.map((ref) => <span key={ref}>{files.find((file) => file.file_ref === ref)?.display_label ?? "所选文件"}</span>)}{node.allowed_tools.map((tool) => <span key={tool}>{toolLabel(tool)}</span>)}{node.needs_human && <span className="is-gate">需要人工确认</span>}</footer></div></li>)}</ol></div>;
}

function ResultView({ result, files }: { result: HarnessResult | null; files: HarnessFile[] }) {
  const [expanded, setExpanded] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  if (!result) return <div className="workspace-placeholder"><IconClock aria-hidden="true" /><h2>分析结果尚未形成</h2><p>Agent 完成只读分析并通过引用校验后，结果会出现在这里。</p></div>;
  const visibleFindings = expanded ? result.findings : result.findings.slice(0, 3);
  const hiddenCount = result.findings.length - visibleFindings.length;
  return <article className="result-view"><header><IconCircleCheck aria-hidden="true" /><div><span>模型初步结论 · 待复核</span><h2 className={summaryExpanded ? "" : "is-clamped"}>{result.summary}</h2>{result.summary.length > 120 && <button type="button" className="result-summary-toggle" aria-expanded={summaryExpanded} onClick={() => setSummaryExpanded((current) => !current)}>{summaryExpanded ? "收起结论" : "展开结论"}</button>}</div></header><div className="result-findings">{visibleFindings.map((finding, index) => <section key={`${finding.title}:${index}`}><b>{index + 1}</b><div><h3>{finding.title}</h3><p>{finding.detail}</p><footer>{finding.file_refs.map((ref) => <span key={ref}>{files.find((file) => file.file_ref === ref)?.display_label ?? "所选文件"}</span>)}</footer></div></section>)}</div>{result.findings.length > 3 && <button type="button" className="result-expand" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}><IconChevronDown className={expanded ? "is-open" : ""} aria-hidden="true" />{expanded ? "收起详细发现" : `查看其余 ${hiddenCount} 条发现`}</button>}{result.follow_ups.length > 0 && <details className="result-follow-ups"><summary>仍需你判断 · {result.follow_ups.length} 项</summary>{result.follow_ups.map((item) => <p key={item}>{item}</p>)}</details>}<footer><IconShieldCheck aria-hidden="true" />服务端只核对了所选文件引用与只读边界，结论和数值仍需人工复核；本轮没有外部动作。</footer></article>;
}
