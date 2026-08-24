"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle, IconArrowRight, IconCheck, IconChevronDown, IconChevronRight,
  IconCircleDot, IconClock, IconFile, IconFolder, IconLoader2, IconPlayerPlay,
  IconRefresh, IconRoute, IconShieldCheck, IconSparkles, IconUserCheck,
} from "@tabler/icons-react";

export type HarnessDemo = "demo1" | "demo2" | "demo3";
type HarnessPhase = "read" | "plan" | "validate" | "ready_to_execute";
type ConnectionState = "connecting" | "available" | "live" | "reconnecting" | "offline";
type CatalogStatus = "checking" | "retrying" | "online" | "unavailable";
type CatalogFailureKind = "service_unreachable" | "catalog_unavailable" | "catalog_invalid";

export type HarnessFile = {
  key: string;
  file_ref?: string;
  display_label: string;
  display_group: string;
  display_summary: string;
};

type ContractDeliverable = { label: string; description?: string };

export type HarnessScenario = {
  scenario_id: string;
  demo: HarnessDemo;
  title: string;
  goal?: string;
  dataset_label?: string;
  dataset_version?: string;
  files: HarnessFile[];
  deliverables?: ContractDeliverable[];
  data_boundary?: string[];
  human_gate_summary?: string;
  allowed_capabilities?: string[];
};

export type HarnessPlanNode = {
  node_id: string;
  label: string;
  description?: string;
  depends_on: string[];
  source_refs: string[];
  allowed_tools: string[];
  needs_human: boolean;
  side_effect?: string;
};

type ModelReceipt = { called: boolean; model: string; elapsed_ms: number; output_used: boolean };

type HarnessServerEvent = {
  sequence: number;
  event_name: string;
  occurred_at?: string;
  status?: string;
  message?: string;
  details?: Record<string, unknown>;
};

export type HarnessRun = {
  run_id: string;
  scenario_id: string;
  status: string;
  version: number;
  last_event_sequence: number;
  source_documents: HarnessFile[];
  plan: HarnessPlanNode[];
  plan_summary?: string;
  model_receipt: ModelReceipt | null;
  validation_errors: string[];
  events: HarnessActivityItem[];
  observed_phase: HarnessPhase;
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
  runStatus: string | null;
  connection: ConnectionState;
  modelReceipt: ModelReceipt | null;
  events: HarnessActivityItem[];
  readyToExecute: boolean;
  error: string | null;
  notice: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010";
const HEADERS = { "Content-Type": "application/json", "X-User-Id": "demo_user" };
const NAMED_EVENTS = [
  "workspace_indexed", "workspace_index", "planning_started", "planning_completed",
  "plan_validated", "plan_validation", "ready_to_execute", "harness_failed",
];
const TERMINAL_EVENTS = new Set(["ready_to_execute", "harness_failed"]);
const TERMINAL_STATUSES = new Set(["ready_to_execute", "failed"]);
const PHASES: { id: HarnessPhase; label: string; hint: string }[] = [
  { id: "read", label: "读取文件", hint: "建立本轮资料范围" },
  { id: "plan", label: "生成计划", hint: "形成动态工作单元" },
  { id: "validate", label: "校验计划", hint: "核对来源、依赖和权限" },
  { id: "ready_to_execute", label: "准备执行", hint: "计划通过，任务尚未执行" },
];

function asText(value: unknown, fallback = "") { return typeof value === "string" ? value : fallback; }
function asStrings(value: unknown) { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }
class CatalogLoadError extends Error {
  constructor(public kind: CatalogFailureKind) { super(kind); }
}
async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 4_000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try { return await fetch(input, { ...init, signal: controller.signal }); }
  finally { window.clearTimeout(timer); }
}
function demoLabel(demo: HarnessDemo) { return demo === "demo1" ? "Demo 1 · 持续任务" : demo === "demo2" ? "Demo 2 · 动态协作" : "Demo 3 · 受控执行"; }
function toolLabel(tool: string) {
  const labels: Record<string, string> = {
    "file.read": "读取文件", "table.inspect": "检查表格",
    "artifact.write": "准备工作成果", "evidence.verify": "核验证据",
    "action.preview": "预演受控动作",
  };
  return labels[tool] ?? "受控办公工具";
}

function normalizeFiles(value: unknown): HarnessFile[] {
  if (!Array.isArray(value)) return [];
  const keyOccurrences = new Map<string, number>();
  return value.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const raw = item as Record<string, unknown>;
    const label = asText(raw.display_label);
    const group = asText(raw.display_group);
    const summary = asText(raw.display_summary);
    if (!label || !group || !summary) return [];
    const publicRef = asText(raw.file_ref);
    const baseKey = publicRef || `display:${group}:${label}`;
    const occurrence = (keyOccurrences.get(baseKey) ?? 0) + 1;
    keyOccurrences.set(baseKey, occurrence);
    return [{
      key: `${baseKey}:${occurrence}`,
      file_ref: publicRef || undefined,
      display_label: label,
      display_group: group,
      display_summary: summary,
    }];
  });
}

function normalizeDeliverables(value: unknown): ContractDeliverable[] | undefined {
  if (!Array.isArray(value)) return undefined;
  const result = value.flatMap((item) => {
    if (typeof item === "string") return [{ label: item }];
    if (!item || typeof item !== "object") return [];
    const raw = item as Record<string, unknown>;
    const label = asText(raw.label ?? raw.title ?? raw.name);
    return label ? [{ label, description: asText(raw.description) || undefined }] : [];
  });
  return result.length ? result : undefined;
}

function normalizeScenario(value: unknown): HarnessScenario | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const scenarioId = asText(raw.scenario_id);
  const demo = asText(raw.demo ?? raw.demo_id) as HarnessDemo;
  if (!scenarioId || !["demo1", "demo2", "demo3"].includes(demo)) return null;
  const dataBoundary = typeof raw.data_boundary === "string" ? [raw.data_boundary] : asStrings(raw.data_boundary);
  return {
    scenario_id: scenarioId,
    demo,
    title: asText(raw.title, "办公任务"),
    goal: asText(raw.goal) || undefined,
    dataset_label: asText(raw.dataset_label) || undefined,
    dataset_version: asText(raw.dataset_version) || undefined,
    files: normalizeFiles(raw.files ?? raw.file_tree),
    deliverables: normalizeDeliverables(raw.deliverables),
    data_boundary: dataBoundary.length ? dataBoundary : undefined,
    human_gate_summary: asText(raw.human_gate_summary) || undefined,
    allowed_capabilities: asStrings(raw.allowed_capabilities),
  };
}

function phaseFromEventName(eventName: string): HarnessPhase | null {
  if (["workspace_indexed", "workspace_index"].includes(eventName)) return "read";
  if (["planning_started", "planning_completed"].includes(eventName)) return "plan";
  if (["plan_validated", "plan_validation"].includes(eventName)) return "validate";
  if (eventName === "ready_to_execute") return "ready_to_execute";
  return null;
}

function normalizeRun(value: unknown): HarnessRun | null {
  if (!value || typeof value !== "object") return null;
  const outer = value as Record<string, unknown>;
  const raw = outer.run && typeof outer.run === "object" ? outer.run as Record<string, unknown> : outer;
  const runId = asText(raw.run_id);
  const scenarioId = asText(raw.scenario_id);
  if (!runId || !scenarioId) return null;
  const planRaw = raw.plan && typeof raw.plan === "object" ? raw.plan as Record<string, unknown> : null;
  const plan = Array.isArray(planRaw?.units) ? planRaw.units.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const unit = item as Record<string, unknown>;
    const nodeId = asText(unit.unit_id);
    if (!nodeId) return [];
    return [{
      node_id: nodeId,
      label: asText(unit.title, "工作单元"),
      description: asText(unit.objective) || undefined,
      depends_on: asStrings(unit.depends_on),
      source_refs: asStrings(unit.input_file_refs),
      allowed_tools: unit.tool ? [asText(unit.tool)] : [],
      needs_human: unit.requires_human_gate === true,
      side_effect: asText(unit.side_effect) || undefined,
    }];
  }) : [];
  const serverEvents = Array.isArray(raw.events) ? raw.events.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const event = item as Record<string, unknown>;
    if (typeof event.sequence !== "number" || !asText(event.event_name)) return [];
    return [{
      sequence: event.sequence,
      event_name: asText(event.event_name),
      occurred_at: asText(event.occurred_at) || undefined,
      status: asText(event.status) || undefined,
      message: asText(event.message) || undefined,
      details: event.details && typeof event.details === "object" ? event.details as Record<string, unknown> : undefined,
    } satisfies HarnessServerEvent];
  }) : [];
  const lastSequence = serverEvents.reduce((latest, event) => {
    const sequence = event.sequence;
    return typeof sequence === "number" ? Math.max(latest, sequence) : latest;
  }, typeof raw.last_event_sequence === "number" ? raw.last_event_sequence : 0);
  const receipt = raw.model_receipt && typeof raw.model_receipt === "object" ? raw.model_receipt as Record<string, unknown> : null;
  const observedPhase = serverEvents.slice().sort((a, b) => a.sequence - b.sequence).reduce<HarnessPhase>((latest, event) => phaseFromEventName(event.event_name) ?? latest, "read");
  return {
    run_id: runId,
    scenario_id: scenarioId,
    status: asText(raw.status, "queued"),
    version: typeof raw.version === "number" ? raw.version : 1,
    last_event_sequence: lastSequence,
    source_documents: normalizeFiles(raw.source_documents),
    plan,
    plan_summary: planRaw ? asText(planRaw.summary) || undefined : undefined,
    model_receipt: receipt ? { called: receipt.called === true, model: asText(receipt.model), elapsed_ms: typeof receipt.elapsed_ms === "number" ? receipt.elapsed_ms : 0, output_used: receipt.output_used === true } : null,
    validation_errors: asStrings(raw.validation_errors),
    events: serverEvents.map(activityItem).sort((a, b) => a.sequence - b.sequence),
    observed_phase: observedPhase,
  };
}

function phaseFromRun(run: HarnessRun | null): HarnessPhase {
  if (run?.status === "ready_to_execute") return "ready_to_execute";
  if (run?.status === "failed") return run.observed_phase;
  if (run?.status === "validating") return "validate";
  if (run?.status === "planning") return "plan";
  return "read";
}

function activityItem(event: HarnessServerEvent): HarnessActivityItem {
  const labels: Record<string, string> = {
    workspace_indexed: "已读取并冻结文件范围", workspace_index: "已读取并冻结文件范围",
    planning_started: "正在生成本轮计划", planning_completed: "模型计划已经返回",
    plan_validated: "计划已通过服务端校验", plan_validation: "计划已通过服务端校验",
    ready_to_execute: "计划已准备好", harness_failed: "本轮计划已停止",
  };
  const tone = event.event_name === "harness_failed" ? "warning" : event.event_name.includes("planning") ? "model" : event.event_name.includes("valid") || event.event_name === "ready_to_execute" ? "success" : "neutral";
  return { sequence: event.sequence, label: labels[event.event_name] ?? "服务端状态已更新", detail: event.message ?? (event.status ? `当前状态：${event.status}` : "本轮状态来自服务端回执。"), occurred_at: event.occurred_at, tone };
}

export function HarnessActivityPane({ state }: { state: HarnessActivityState | null }) {
  if (!state) return <section className="harness-activity-pane is-empty"><IconClock aria-hidden="true" /><h2>Agent 此刻在做什么</h2><p>打开工作现场后，这里会持续显示本轮服务端回执。</p></section>;
  return <section className="harness-activity-pane" aria-labelledby="harness-activity-title">
    <header><div className="harness-agent-avatar"><IconSparkles aria-hidden="true" /></div><div><span>Agent 此刻在做什么</span><h2 id="harness-activity-title">{state.scenarioTitle}</h2></div><b className={`is-${state.connection}`}><i />{state.connection === "live" ? "事件实时" : state.connection === "available" ? "服务可用" : state.connection === "reconnecting" ? "重连中" : state.connection === "offline" ? "离线" : "连接中"}</b></header>
    <div className="harness-model-receipt" aria-live="polite">{state.modelReceipt?.called ? <><IconSparkles aria-hidden="true" /><div><strong>模型调用完成</strong><span>{state.modelReceipt.model} · {state.modelReceipt.elapsed_ms} ms</span></div><b className={state.modelReceipt.output_used ? "is-used" : "is-rejected"}>{state.modelReceipt.output_used ? "模型计划已采纳" : "模型计划未采纳"}</b></> : <><IconClock aria-hidden="true" /><div><strong>等待模型事实</strong><span>尚未收到模型调用回执</span></div></>}</div>
    <ol className="harness-activity-list" aria-live="polite" aria-relevant="additions text">{state.events.length ? state.events.map((item) => <li key={item.sequence} className={`is-${item.tone}`}><span>{item.tone === "model" ? <IconSparkles aria-hidden="true" /> : item.tone === "success" ? <IconCheck aria-hidden="true" /> : item.tone === "warning" ? <IconAlertTriangle aria-hidden="true" /> : <IconCircleDot aria-hidden="true" />}</span><div><strong>{item.label}</strong><p>{item.detail}</p>{item.occurred_at && <small>{new Date(item.occurred_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</small>}</div></li>) : <li className="is-placeholder"><span><IconClock aria-hidden="true" /></span><div><strong>等待本轮开始</strong><p>先读取文件，再生成并校验计划。</p></div></li>}</ol>
    {state.readyToExecute && <footer className="is-ready" role="status"><IconShieldCheck aria-hidden="true" /><span>计划已通过校验，任务尚未执行</span></footer>}
    {state.notice && <footer className="is-notice" role="status"><IconAlertTriangle aria-hidden="true" /><span>{state.notice}</span></footer>}
    {state.error && <footer className="is-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{state.error}</span></footer>}
  </section>;
}

export function HarnessWorkbench({ initialDemo = "demo1", onActivityChange }: { initialDemo?: HarnessDemo; onActivityChange?: (state: HarnessActivityState | null) => void }) {
  const [scenarios, setScenarios] = useState<HarnessScenario[]>([]);
  const [selectedDemo, setSelectedDemo] = useState<HarnessDemo>(initialDemo);
  const [scenario, setScenario] = useState<HarnessScenario | null>(null);
  const [run, setRun] = useState<HarnessRun | null>(null);
  const [selectedFile, setSelectedFile] = useState<HarnessFile | null>(null);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [catalogStatus, setCatalogStatus] = useState<CatalogStatus>("checking");
  const [catalogFailureKind, setCatalogFailureKind] = useState<CatalogFailureKind | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [detailNotice, setDetailNotice] = useState("");
  const [starting, setStarting] = useState(false);
  const [startAttempted, setStartAttempted] = useState(false);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const [activity, setActivity] = useState<HarnessActivityItem[]>([]);
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  const catalogRetryTimerRef = useRef<number | undefined>(undefined);
  const catalogRequestRef = useRef(0);
  const catalogAttemptRef = useRef(0);
  const generationRef = useRef(0);
  const runRef = useRef<HarnessRun | null>(null);
  const lastSequenceRef = useRef(0);
  const startCommandRef = useRef<{ scenarioId: string; key: string } | null>(null);

  function closeTransport() { eventSourceRef.current?.close(); eventSourceRef.current = null; window.clearTimeout(reconnectTimerRef.current); reconnectTimerRef.current = undefined; }
  function applySnapshot(snapshot: HarnessRun, generation: number) {
    if (generation !== generationRef.current) return false;
    const current = runRef.current;
    if (current && snapshot.run_id !== current.run_id) return false;
    if (snapshot.last_event_sequence < lastSequenceRef.current) return false;
    if (current && (snapshot.version < current.version || (snapshot.version === current.version && snapshot.last_event_sequence < current.last_event_sequence))) return false;
    runRef.current = snapshot;
    lastSequenceRef.current = Math.max(lastSequenceRef.current, snapshot.last_event_sequence);
    setRun(snapshot);
    setActivity(snapshot.events.slice(-24));
    return true;
  }
  async function readSnapshot(runId: string, generation: number) {
    const response = await fetch(`${API_BASE}/v1/harness/runs/${encodeURIComponent(runId)}`, { headers: HEADERS });
    if (!response.ok) throw new Error(`本轮状态读取失败（${response.status}）`);
    const snapshot = normalizeRun(await response.json() as unknown);
    if (!snapshot) throw new Error("服务端返回的本轮状态无效");
    applySnapshot(snapshot, generation);
  }
  function connectStream(runId: string, generation: number) {
    if (generation !== generationRef.current) return;
    closeTransport();
    if (runRef.current?.run_id === runId && TERMINAL_STATUSES.has(runRef.current.status)) {
      setConnection("available");
      return;
    }
    setConnection("connecting");
    const source = new EventSource(`${API_BASE}/v1/harness/runs/${encodeURIComponent(runId)}/events?after=${lastSequenceRef.current}`);
    eventSourceRef.current = source;
    const receive = (raw: Event, name: string) => {
      if (generation !== generationRef.current || eventSourceRef.current !== source || runRef.current?.run_id !== runId) return;
      try {
        const parsed = JSON.parse((raw as MessageEvent<string>).data) as HarnessServerEvent;
        const event = { ...parsed, event_name: name };
        if (event.sequence <= lastSequenceRef.current) return;
        lastSequenceRef.current = event.sequence;
        setActivity((current) => [...current.filter((item) => item.sequence !== event.sequence), activityItem(event)].sort((a, b) => a.sequence - b.sequence).slice(-24));
        setConnection("live");
        if (TERMINAL_EVENTS.has(name)) {
          source.close();
          eventSourceRef.current = null;
          setConnection("available");
          window.clearTimeout(reconnectTimerRef.current);
          reconnectTimerRef.current = undefined;
          void readSnapshot(runId, generation).catch(() => {
            if (generation === generationRef.current && runRef.current?.run_id === runId) setConnection("offline");
          });
          return;
        }
        void readSnapshot(runId, generation).catch(() => setConnection("reconnecting"));
      } catch { setConnection("reconnecting"); }
    };
    NAMED_EVENTS.forEach((name) => source.addEventListener(name, (event) => receive(event, name)));
    source.onopen = () => { if (generation === generationRef.current && eventSourceRef.current === source) setConnection("live"); };
    source.onerror = () => {
      if (generation !== generationRef.current || eventSourceRef.current !== source) return;
      source.close(); eventSourceRef.current = null; setConnection("reconnecting");
      void readSnapshot(runId, generation).catch(() => setConnection("offline")).finally(() => {
        if (generation !== generationRef.current || runRef.current?.run_id !== runId) return;
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = window.setTimeout(() => connectStream(runId, generation), 900);
      });
    };
  }
  async function loadScenarios(manual = false) {
    const request = catalogRequestRef.current + 1;
    catalogRequestRef.current = request;
    window.clearTimeout(catalogRetryTimerRef.current);
    catalogRetryTimerRef.current = undefined;
    if (manual) catalogAttemptRef.current = 0;
    const attempt = catalogAttemptRef.current + 1;
    catalogAttemptRef.current = attempt;
    setLoading(true);
    setCatalogStatus(attempt === 1 ? "checking" : "retrying");
    setCatalogError("");
    try {
      let health: Response;
      try { health = await fetchWithTimeout(`${API_BASE}/v1/health`, { headers: HEADERS }); }
      catch { throw new CatalogLoadError("service_unreachable"); }
      if (!health.ok) throw new CatalogLoadError("service_unreachable");
      let response: Response;
      try { response = await fetchWithTimeout(`${API_BASE}/v1/harness/scenarios`, { headers: HEADERS }); }
      catch { throw new CatalogLoadError("catalog_unavailable"); }
      if (!response.ok) {
        let detail = "";
        try {
          const errorBody = await response.json() as unknown;
          if (errorBody && typeof errorBody === "object") detail = asText((errorBody as Record<string, unknown>).detail);
        } catch { /* The status remains the authoritative failure fact. */ }
        throw new CatalogLoadError(detail.includes("完整性") ? "catalog_invalid" : "catalog_unavailable");
      }
      let body: unknown;
      try { body = await response.json() as unknown; }
      catch { throw new CatalogLoadError("catalog_invalid"); }
      const raw = body && typeof body === "object" && Array.isArray((body as { scenarios?: unknown[] }).scenarios) ? (body as { scenarios: unknown[] }).scenarios : [];
      const normalized = raw.flatMap((item) => { const value = normalizeScenario(item); return value ? [value] : []; })
        .filter((item) => item.dataset_label?.toUpperCase().includes("FORTE"));
      const forteScenarios = (["demo1", "demo2", "demo3"] as HarnessDemo[]).flatMap((demo) => {
        const item = normalized.find((candidate) => candidate.demo === demo);
        return item ? [item] : [];
      });
      if (forteScenarios.length !== 3) throw new CatalogLoadError("catalog_invalid");
      if (request !== catalogRequestRef.current) return;
      setScenarios(forteScenarios);
      catalogAttemptRef.current = 0;
      setCatalogStatus("online");
      setCatalogFailureKind(null);
      setCatalogError("");
      setConnection("available");
    } catch (reason) {
      if (request !== catalogRequestRef.current) return;
      const kind = reason instanceof CatalogLoadError ? reason.kind : "service_unreachable";
      const unavailable = attempt >= 3;
      setCatalogFailureKind(kind);
      setCatalogStatus(unavailable ? "unavailable" : "retrying");
      setCatalogError(unavailable ? kind === "service_unreachable"
        ? "无法连接办公服务，系统会继续自动重试。"
        : kind === "catalog_invalid"
          ? "办公服务已连接，但场景目录未通过完整性检查；系统会继续自动重试。"
          : "办公服务已连接，但场景目录暂时无法读取；系统会继续自动重试。" : "");
      setConnection(kind === "service_unreachable" ? unavailable ? "offline" : "reconnecting" : "available");
      const delays = [650, 1_200, 2_500, 5_000];
      const delay = delays[Math.min(attempt - 1, delays.length - 1)];
      catalogRetryTimerRef.current = window.setTimeout(() => void loadScenarios(), delay);
    } finally {
      if (request === catalogRequestRef.current) setLoading(false);
    }
  }

  useEffect(() => { void loadScenarios(); return () => { catalogRequestRef.current += 1; window.clearTimeout(catalogRetryTimerRef.current); closeTransport(); }; }, []);
  useEffect(() => {
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    closeTransport(); runRef.current = null; lastSequenceRef.current = 0; startCommandRef.current = null;
    setRun(null); setActivity([]); setError(""); setDetailNotice(""); setStartAttempted(false); setSelectedFile(null);
    const preview = scenarios.find((item) => item.demo === selectedDemo) ?? null;
    setScenario(preview);
    if (!preview) return;
    void fetchWithTimeout(`${API_BASE}/v1/harness/scenarios/${encodeURIComponent(preview.scenario_id)}`, { headers: HEADERS })
      .then(async (response) => {
        if (!response.ok) throw new Error("detail unavailable");
        return response.json() as Promise<unknown>;
      })
      .then((body) => {
        if (generation !== generationRef.current) return;
        const detail = normalizeScenario(body);
        if (!detail) throw new Error("detail invalid");
        setScenario(detail);
        setDetailNotice("");
      })
      .catch(() => {
        if (generation === generationRef.current) setDetailNotice("场景详情暂时不可用，当前使用目录中的公开信息。");
      });
  }, [selectedDemo, scenarios]);

  async function startRun(newRound = false) {
    if (!scenario || starting) return;
    const command = !newRound && startCommandRef.current?.scenarioId === scenario.scenario_id ? startCommandRef.current : { scenarioId: scenario.scenario_id, key: `harness:${scenario.scenario_id}:${crypto.randomUUID()}` };
    startCommandRef.current = command;
    if (newRound) { generationRef.current += 1; closeTransport(); runRef.current = null; lastSequenceRef.current = 0; setRun(null); setActivity([]); }
    setStarting(true); setStartAttempted(true); setError("");
    const generation = generationRef.current;
    try {
      const response = await fetch(`${API_BASE}/v1/harness/runs`, { method: "POST", headers: HEADERS, body: JSON.stringify({ scenario_id: scenario.scenario_id, idempotency_key: command.key, expected_version: 1 }) });
      if (!response.ok) throw new Error(`本轮启动结果未知（${response.status}），重试会复用同一命令`);
      const snapshot = normalizeRun(await response.json() as unknown);
      if (!snapshot) throw new Error("本轮启动结果未知，重试会复用同一命令");
      runRef.current = null;
      if (applySnapshot(snapshot, generation)) connectStream(snapshot.run_id, generation);
    } catch (reason) { if (generation === generationRef.current) { setError(reason instanceof Error ? reason.message : "本轮启动结果未知"); setConnection("offline"); } }
    finally { if (generation === generationRef.current) setStarting(false); }
  }

  const activityState = useMemo<HarnessActivityState>(() => ({ scenarioTitle: scenario?.title ?? "工作现场", runStatus: run?.status ?? null, connection, modelReceipt: run?.model_receipt ?? null, events: activity, readyToExecute: run?.status === "ready_to_execute", error: run?.status === "failed" ? run.validation_errors[0] ?? "本轮计划未通过校验" : error || catalogError || null, notice: detailNotice || null }), [activity, catalogError, connection, detailNotice, error, run, scenario?.title]);
  useEffect(() => { onActivityChange?.(activityState); }, [activityState, onActivityChange]);
  useEffect(() => () => onActivityChange?.(null), [onActivityChange]);

  const files = run?.source_documents.length ? run.source_documents : scenario?.files ?? [];
  const plan = run?.plan ?? [];
  const phase = phaseFromRun(run);
  const currentPhaseIndex = PHASES.findIndex((item) => item.id === phase);
  const isReady = run?.status === "ready_to_execute";
  const groupedFiles = useMemo(() => { const groups = new Map<string, HarnessFile[]>(); files.forEach((item) => { const group = item.display_group || "本轮资料"; groups.set(group, [...(groups.get(group) ?? []), item]); }); return [...groups.entries()]; }, [files]);
  const hasContract = Boolean(scenario?.deliverables?.length || scenario?.data_boundary?.length || scenario?.human_gate_summary || scenario?.allowed_capabilities?.length);
  const startLabel = starting ? "启动中" : run && ["ready_to_execute", "failed"].includes(run.status) ? "开始新一轮" : startAttempted && error ? "重试启动" : "开始本轮";
  function manualReconnect() { if (!run) { void loadScenarios(true); return; } const generation = generationRef.current; closeTransport(); void readSnapshot(run.run_id, generation).finally(() => connectStream(run.run_id, generation)); }

  return <section className="harness-workbench" aria-label="工作现场">
    <header className="harness-header"><div className="harness-title"><div className="harness-mark"><IconRoute aria-hidden="true" /></div><div><span>工作现场</span><h1>{scenario?.title ?? "工作现场"}</h1><p>{scenario?.goal ?? "从公开办公资料开始，形成一份可核对的任务计划。"}</p></div></div><div className="harness-header-actions"><span className={`harness-connection is-${connection}`} aria-live="polite"><i />{connection === "live" ? "事件流实时" : connection === "available" ? "服务可用" : connection === "reconnecting" ? "正在重连" : connection === "offline" ? "暂时离线" : "连接中"}</span><button type="button" className="harness-icon-button" onClick={manualReconnect} title="重新连接" aria-label="重新连接"><IconRefresh aria-hidden="true" /></button></div></header>
    <nav className="harness-demo-tabs" aria-label="演示场景">{(["demo1", "demo2", "demo3"] as HarnessDemo[]).map((demo) => <button key={demo} type="button" aria-current={selectedDemo === demo ? "page" : undefined} className={selectedDemo === demo ? "is-active" : ""} onClick={() => demo !== selectedDemo && setSelectedDemo(demo)}><span>{demoLabel(demo)}</span><small>{scenarios.find((item) => item.demo === demo)?.title ?? "等待服务端场景"}</small><IconChevronRight aria-hidden="true" /></button>)}</nav>
    {!scenario && (loading || catalogStatus === "checking" || catalogStatus === "retrying") ? <div className="harness-empty" role="status" aria-live="polite"><IconLoader2 aria-hidden="true" /><h2>{catalogStatus === "checking" ? "正在连接办公服务" : catalogFailureKind === "service_unreachable" ? "办公服务正在恢复" : "正在重新读取工作场景"}</h2><p>{catalogFailureKind && catalogFailureKind !== "service_unreachable" ? "办公服务已连接，场景目录恢复后会自动显示三项 FORTE 办公场景。" : "连接恢复后会自动读取三项 FORTE 办公场景。"}</p></div> : !scenario && catalogStatus === "unavailable" ? <div className="harness-empty is-error" role="alert"><IconAlertTriangle aria-hidden="true" /><h2>{catalogFailureKind === "service_unreachable" ? "工作现场暂时离线" : catalogFailureKind === "catalog_invalid" ? "工作场景需要更新" : "工作场景暂时不可用"}</h2><p>{catalogError}</p><button type="button" className="harness-primary-button" onClick={() => void loadScenarios(true)}>立即重试</button></div> : <div className="harness-grid">
      <aside className="harness-source-panel" aria-labelledby="harness-source-title"><div className="harness-panel-heading"><div><span>来源工作区</span><h2 id="harness-source-title">{scenario?.dataset_label ?? "公开办公基准数据"}</h2></div><IconFolder aria-hidden="true" /></div>{scenario?.dataset_version && <div className="harness-source-meta"><b>{scenario.dataset_version}</b></div>}<div className="harness-file-tree" role="tree" aria-label="本轮文件来源">{groupedFiles.length === 0 && <div className="harness-muted">启动后显示服务端冻结的文件范围。</div>}{groupedFiles.map(([group, items]) => <div key={group} className="harness-folder"><button type="button" role="treeitem" aria-expanded={expandedGroups[group] ?? true} onClick={() => setExpandedGroups((current) => ({ ...current, [group]: !(current[group] ?? true) }))}><IconChevronDown className={expandedGroups[group] ?? true ? "is-open" : ""} aria-hidden="true" /><IconFolder aria-hidden="true" /><span>{group}</span><small>{items.length}</small></button>{(expandedGroups[group] ?? true) && <div className="harness-files" role="group">{items.map((item) => <button type="button" role="treeitem" aria-selected={selectedFile?.key === item.key} key={item.key} className={selectedFile?.key === item.key ? "is-selected" : ""} onClick={() => setSelectedFile(item)}><IconFile aria-hidden="true" /><span>{item.display_label}</span></button>)}</div>}</div>)}</div>{selectedFile && <FileInspector file={selectedFile} />}</aside>
      <main className="harness-main-panel"><div className="harness-scenario-heading"><div><span>{scenario ? demoLabel(scenario.demo) : "办公场景"}</span><h2>{scenario?.title ?? "等待场景"}</h2><p>{scenario?.goal}</p></div><button type="button" className="harness-primary-button" onClick={() => void startRun(Boolean(run && ["ready_to_execute", "failed"].includes(run.status)))} disabled={!scenario || starting || Boolean(run && !["ready_to_execute", "failed"].includes(run.status))}>{starting && <IconLoader2 aria-hidden="true" />}{!starting && <IconPlayerPlay aria-hidden="true" />}{startLabel}</button></div>
      {hasContract && <TaskContract scenario={scenario!} />}
      <section className="harness-phase-rail" aria-label="任务阶段">{PHASES.map((item, index) => { const complete = currentPhaseIndex > index; const active = currentPhaseIndex === index; return <div className={`harness-phase ${complete ? "is-complete" : active ? "is-active" : ""}`} key={item.id}><span>{complete ? <IconCheck aria-hidden="true" /> : index + 1}</span><div><strong>{item.label}</strong><small>{active ? item.hint : complete ? "服务端已回执" : "等待前一阶段"}</small></div>{index < PHASES.length - 1 && <IconArrowRight aria-hidden="true" />}</div>; })}</section>
      <section className="harness-plan-panel" aria-labelledby="harness-plan-title"><header><div><span>本轮工作图</span><h3 id="harness-plan-title">{plan.length ? `${plan.length} 个动态工作单元` : "等待 Agent 生成计划"}</h3></div>{isReady ? <b className="is-ready"><IconCheck aria-hidden="true" />计划已通过校验</b> : <b className="is-waiting"><IconClock aria-hidden="true" />{run?.status === "planning" ? "正在形成计划" : "尚未形成计划"}</b>}</header>{plan.length === 0 ? <div className="harness-plan-placeholder"><IconRoute aria-hidden="true" /><p>读取文件后，工作单元、依赖、允许工具和人工边界会按服务端回执出现。</p></div> : <div className="harness-plan-dag">{plan.map((node) => <article key={node.node_id} className="harness-plan-node"><header><span><IconCircleDot aria-hidden="true" /></span><div><strong>{node.label}</strong><small>计划产出</small></div></header>{node.description && <p>{node.description}</p>}{node.source_refs.length > 0 && <div className="harness-node-facts"><span>使用文件</span><div>{node.source_refs.map((fileRef) => <b key={fileRef}>{files.find((file) => file.file_ref === fileRef)?.display_label ?? "本轮受控文件"}</b>)}</div></div>}{node.allowed_tools.length > 0 && <div className="harness-node-facts"><span>允许工具</span><div>{node.allowed_tools.map((tool) => <b key={tool}>{toolLabel(tool)}</b>)}</div></div>}{node.needs_human && <div className="harness-human-gate"><IconUserCheck aria-hidden="true" /><span>此工作单元需要人工确认后才能进入执行</span></div>}{node.depends_on.length > 0 && <footer>依赖 {node.depends_on.length} 个前置工作单元</footer>}</article>)}</div>}</section>
      {detailNotice && <div className="harness-inline-notice" role="status"><IconAlertTriangle aria-hidden="true" /><span>{detailNotice}</span></div>}{isReady && <div className="harness-ready-banner" role="status"><IconShieldCheck aria-hidden="true" /><div><strong>计划已通过服务端校验，尚未执行任务</strong><span>任何外部动作仍需进入独立控制流程。</span></div></div>}{run?.status === "failed" && <div className="harness-inline-error" role="alert"><IconAlertTriangle aria-hidden="true" /><div><strong>计划未通过服务端校验</strong><span>{run.validation_errors[0] ?? "本轮已停止，执行未启动。"}</span></div></div>}{error && scenario && <div className="harness-inline-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{error}</span></div>}
      </main>
    </div>}
  </section>;
}

function TaskContract({ scenario }: { scenario: HarnessScenario }) {
  return <section className="harness-contract" aria-labelledby="harness-contract-title"><header><IconShieldCheck aria-hidden="true" /><div><span>本轮任务契约</span><h3 id="harness-contract-title">开始前确认完成条件与边界</h3></div></header><div>{scenario.deliverables?.length ? <dl><dt>完成条件</dt>{scenario.deliverables.map((item) => <dd key={item.label}><strong>{item.label}</strong>{item.description && <span>{item.description}</span>}</dd>)}</dl> : null}{scenario.data_boundary?.length ? <dl><dt>数据边界</dt>{scenario.data_boundary.map((item) => <dd key={item}>{item}</dd>)}</dl> : null}{scenario.allowed_capabilities?.length ? <dl><dt>允许能力</dt>{scenario.allowed_capabilities.map((item) => <dd key={item}>{item}</dd>)}</dl> : null}{scenario.human_gate_summary && <dl><dt>需要人工时</dt><dd>{scenario.human_gate_summary}</dd></dl>}</div></section>;
}

function FileInspector({ file }: { file: HarnessFile }) {
  return <div className="harness-file-inspector"><span>当前文件</span><strong>{file.display_label}</strong><p>{file.display_summary}</p></div>;
}
