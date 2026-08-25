"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconAdjustments,
  IconCheck,
  IconChevronDown,
  IconCircleCheck,
  IconCircleDot,
  IconClock,
  IconDatabase,
  IconFile,
  IconFileDescription,
  IconLoader2,
  IconPlayerPause,
  IconPlayerPlay,
  IconPlayerStop,
  IconRefresh,
  IconRoute,
  IconSearch,
  IconSend,
  IconShieldCheck,
  IconSparkles,
} from "@tabler/icons-react";

type ConnectionState = "connecting" | "available" | "live" | "reconnecting" | "offline";
type WorkspaceStatus = "checking" | "online" | "unavailable";
type WorkspaceView = "data" | "loop" | "result";
type FileTypeFilter = string;
type PreviewKind = "table" | "document" | "pdf" | "text" | "unavailable";
type LoopPhase = "observe" | "plan" | "act" | "verify" | "evidence_gate" | "commit";
type LoopCommand = "pause" | "resume" | "steer" | "stop";

export type HarnessFile = {
  file_ref: string;
  folder_id: string;
  display_label: string;
  display_group: string;
  display_path: string;
  display_summary: string;
  extension: string;
  mime: string;
  size: number;
  preview_kind: PreviewKind;
  preview_available: boolean;
};

type HarnessFolder = {
  folder_id: string;
  display_label: string;
  display_summary: string;
  availability: "local_input_bundle" | "task_only_requires_external_system";
  external_dependency_label: string | null;
  file_count: number;
  total_bytes: number;
  files: HarnessFile[];
};

type HarnessWorkspace = {
  workspace_id: "forte-public-office";
  title: string;
  dataset_label: string;
  dataset_version: string;
  source_label: string;
  license: string;
  data_boundary: string;
  file_count: number;
  folder_count: number;
  previewable_file_count: number;
  folders: HarnessFolder[];
};

type PreviewSecurity = {
  integrity_verified: boolean;
  read_only: boolean;
  active_content_executed: boolean;
  external_resources_loaded: boolean;
  notes: string[];
};

type HarnessPreview = {
  workspace_id: string;
  file_ref: string;
  folder_id: string;
  display_label: string;
  display_group: string;
  display_path: string;
  display_summary: string;
  mime: string;
  size: number;
  kind: PreviewKind;
  sheet_name: string | null;
  columns: string[];
  rows: { row_number: number; values: string[] }[];
  total_rows: number | null;
  text: string | null;
  page_count: number | null;
  truncated: boolean;
  security: PreviewSecurity;
};

type ModelReceipt = { called: boolean; model: string; elapsed_ms: number; output_used: boolean };
type HarnessFinding = { title: string; detail: string; file_refs: string[] };
type HarnessResult = { summary: string; findings: HarnessFinding[]; follow_ups: string[]; review_required: boolean };
type HarnessServerEvent = { sequence: number; event_name: string; occurred_at?: string; message?: string };

type LoopContract = {
  contract_version: string;
  goal: string;
  scope_mode: "whole_workspace";
  allowed_file_refs: string[];
  completion_criteria: string[];
  max_rounds: number;
  max_files_per_round: number;
  max_model_calls: number;
  deadline_seconds: number;
  external_action: "none";
};

type LoopBudget = {
  max_rounds: number;
  max_files_per_round: number;
  max_model_calls: number;
  deadline_seconds: number;
  rounds_used: number;
  files_verified: number;
  model_calls_used: number;
  elapsed_ms: number;
  stop_reason: string | null;
};

type EvidenceGap = {
  gap_id: string;
  label: string;
  detail: string;
  candidate_file_refs: string[];
};

type LoopNextStep = {
  decision: "pending" | "next_round" | "completed" | "budget_exhausted" | "waiting_input" | "user_stopped" | "failed";
  reason: string;
  next_question: string | null;
  candidate_file_refs: string[];
};

type LoopRound = {
  round_number: number;
  status: "running" | "completed" | "stopped" | "failed";
  phase: LoopPhase;
  question: string;
  steer_instruction: string | null;
  input_file_refs: string[];
  plan: HarnessPlanNode[];
  plan_summary: string | null;
  selection_reason: string | null;
  model_receipt: ModelReceipt | null;
  result: HarnessResult | null;
  analysis_receipt: ModelReceipt | null;
  verified_file_refs: string[];
  evidence_gaps: EvidenceGap[];
  next_step: LoopNextStep | null;
};

type LoopBrief = {
  outcome: "completed" | "bounded" | "user_stopped";
  summary: string;
  verified_file_refs: string[];
  unresolved_gaps: EvidenceGap[];
  rounds_completed: number;
  external_action: "none";
};

export type HarnessPlanNode = {
  node_id: string;
  label: string;
  description: string;
  depends_on: string[];
  source_refs: string[];
  tool: string;
  needs_human: boolean;
  side_effect: "none" | "run_workspace_write" | "external_action";
};

export type HarnessRun = {
  run_id: string;
  workspace_id: string;
  status: string;
  version: number;
  last_event_sequence: number;
  instruction: string;
  source_documents: HarnessFile[];
  contract: LoopContract;
  budget: LoopBudget;
  rounds: LoopRound[];
  current_round: number;
  control_state: "running" | "pause_requested" | "paused" | "stop_requested" | "stopped";
  brief: LoopBrief | null;
  plan: HarnessPlanNode[];
  plan_summary?: string;
  selection_reason?: string;
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
  workspaceTitle: string;
  instruction: string | null;
  runStatus: string | null;
  connection: ConnectionState;
  planningReceipt: ModelReceipt | null;
  analysisReceipt: ModelReceipt | null;
  events: HarnessActivityItem[];
  resultReady: boolean;
  contract: LoopContract | null;
  budget: LoopBudget | null;
  rounds: LoopRound[];
  currentRound: number;
  controlState: HarnessRun["control_state"] | null;
  brief: LoopBrief | null;
  error: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010";
const HEADERS = { "Content-Type": "application/json", "X-User-Id": "demo_user" };
const NAMED_EVENTS = [
  "workspace_index",
  "round_started",
  "planning_started",
  "planning_completed",
  "plan_validation_rejected",
  "plan_validation",
  "ready_to_execute",
  "analysis_started",
  "analysis_completed",
  "result_validation",
  "evidence_gate",
  "control_pause_recorded",
  "control_paused",
  "control_resume_recorded",
  "control_steer_recorded",
  "control_steer_applied",
  "control_stop_recorded",
  "loop_committed",
  "loop_budget_stopped",
  "loop_stopped",
  "harness_failed",
];
const TERMINAL_EVENTS = new Set(["ready_to_execute", "loop_committed", "loop_budget_stopped", "loop_stopped", "harness_failed"]);
const TERMINAL_STATUSES = new Set(["ready_to_execute", "completed", "stopped", "failed"]);
const TASK_EXAMPLES = [
  "研究整个资料库，找出跨文件值得继续推进的问题，并提出有证据依据的下一步任务。",
  "核对资料库中可能互相矛盾的信息，说明影响并提出下一步核查任务。",
  "查找影响近期工作的变更、风险和待办，并逐条引用文件依据。",
];

function asText(value: unknown, fallback = "") { return typeof value === "string" ? value : fallback; }
function asStrings(value: unknown) { return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : []; }
function asNumber(value: unknown, fallback = 0) { return typeof value === "number" && Number.isFinite(value) ? value : fallback; }
function formatSize(value: number) {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}
function randomKey() {
  return `workspace-${Date.now()}-${globalThis.crypto?.randomUUID?.() ?? Math.random().toString(16).slice(2)}`;
}

async function fetchWithTimeout(input: RequestInfo | URL, init: RequestInit = {}, timeoutMs = 8_000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try { return await fetch(input, { ...init, signal: controller.signal }); }
  finally { window.clearTimeout(timer); }
}

function normalizeFile(value: unknown): HarnessFile | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const kind = asText(raw.preview_kind);
  const fileRef = asText(raw.file_ref);
  if (!fileRef || !["table", "document", "pdf", "text", "unavailable"].includes(kind)) return null;
  return {
    file_ref: fileRef,
    folder_id: asText(raw.folder_id),
    display_label: asText(raw.display_label, "公开办公文件"),
    display_group: asText(raw.display_group, "办公资料"),
    display_path: asText(raw.display_path, "办公资料/文件"),
    display_summary: asText(raw.display_summary, "公开办公文件"),
    extension: asText(raw.extension, "FILE"),
    mime: asText(raw.mime, "application/octet-stream"),
    size: asNumber(raw.size),
    preview_kind: kind as PreviewKind,
    preview_available: raw.preview_available === true,
  };
}

function normalizeWorkspace(value: unknown): HarnessWorkspace | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (raw.workspace_id !== "forte-public-office" || !Array.isArray(raw.folders)) return null;
  const folders = raw.folders.flatMap((item): HarnessFolder[] => {
    if (!item || typeof item !== "object") return [];
    const folder = item as Record<string, unknown>;
    const files = Array.isArray(folder.files)
      ? folder.files.map(normalizeFile).filter((file): file is HarnessFile => file !== null)
      : [];
    const availability = folder.availability === "task_only_requires_external_system"
      ? "task_only_requires_external_system"
      : "local_input_bundle";
    return [{
      folder_id: asText(folder.folder_id),
      display_label: asText(folder.display_label, "办公资料"),
      display_summary: asText(folder.display_summary, "公开办公输入资料"),
      availability,
      external_dependency_label: asText(folder.external_dependency_label) || null,
      file_count: asNumber(folder.file_count, files.length),
      total_bytes: asNumber(folder.total_bytes),
      files,
    }];
  });
  return {
    workspace_id: "forte-public-office",
    title: asText(raw.title, "FORTE 公开办公资料库"),
    dataset_label: asText(raw.dataset_label, "FORTE 公开办公基准数据"),
    dataset_version: asText(raw.dataset_version, "固定公开版本"),
    source_label: asText(raw.source_label, "AGI-Eval-Official/FORTE"),
    license: asText(raw.license, "Apache-2.0"),
    data_boundary: asText(raw.data_boundary, "只读访问公开输入文件"),
    file_count: asNumber(raw.file_count),
    folder_count: asNumber(raw.folder_count, folders.length),
    previewable_file_count: asNumber(raw.previewable_file_count),
    folders,
  };
}

function normalizePreview(value: unknown): HarnessPreview | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const kind = asText(raw.kind);
  if (!asText(raw.file_ref) || !["table", "document", "pdf", "text", "unavailable"].includes(kind)) return null;
  const rows = Array.isArray(raw.rows) ? raw.rows.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const row = item as Record<string, unknown>;
    return typeof row.row_number === "number" && Array.isArray(row.values)
      ? [{ row_number: row.row_number, values: asStrings(row.values) }]
      : [];
  }) : [];
  const securityRaw = raw.security && typeof raw.security === "object"
    ? raw.security as Record<string, unknown>
    : {};
  return {
    workspace_id: asText(raw.workspace_id),
    file_ref: asText(raw.file_ref),
    folder_id: asText(raw.folder_id),
    display_label: asText(raw.display_label),
    display_group: asText(raw.display_group),
    display_path: asText(raw.display_path),
    display_summary: asText(raw.display_summary),
    mime: asText(raw.mime),
    size: asNumber(raw.size),
    kind: kind as PreviewKind,
    sheet_name: asText(raw.sheet_name) || null,
    columns: asStrings(raw.columns),
    rows,
    total_rows: typeof raw.total_rows === "number" ? raw.total_rows : null,
    text: typeof raw.text === "string" ? raw.text : null,
    page_count: typeof raw.page_count === "number" ? raw.page_count : null,
    truncated: raw.truncated === true,
    security: {
      integrity_verified: securityRaw.integrity_verified === true,
      read_only: securityRaw.read_only === true,
      active_content_executed: securityRaw.active_content_executed === true,
      external_resources_loaded: securityRaw.external_resources_loaded === true,
      notes: asStrings(securityRaw.notes),
    },
  };
}

function normalizeReceipt(value: unknown): ModelReceipt | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  return {
    called: raw.called === true,
    model: asText(raw.model),
    elapsed_ms: asNumber(raw.elapsed_ms),
    output_used: raw.output_used === true,
  };
}

function normalizeResult(value: unknown): HarnessResult | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const findings = Array.isArray(raw.findings) ? raw.findings.flatMap((item) => {
    if (!item || typeof item !== "object") return [];
    const finding = item as Record<string, unknown>;
    const title = asText(finding.title); const detail = asText(finding.detail);
    const fileRefs = asStrings(finding.file_refs);
    return title && detail && fileRefs.length ? [{ title, detail, file_refs: fileRefs }] : [];
  }) : [];
  const summary = asText(raw.summary);
  return summary && findings.length
    ? { summary, findings, follow_ups: asStrings(raw.follow_ups), review_required: raw.review_required === true }
    : null;
}

function normalizePlan(value: unknown) {
  const raw = value && typeof value === "object" ? value as Record<string, unknown> : null;
  const units = Array.isArray(raw?.units) ? raw.units.flatMap((item): HarnessPlanNode[] => {
    if (!item || typeof item !== "object") return [];
    const unit = item as Record<string, unknown>;
    const nodeId = asText(unit.unit_id);
    if (!nodeId) return [];
    const sideEffect = asText(unit.side_effect);
    return [{
      node_id: nodeId,
      label: asText(unit.title, "工作单元"),
      description: asText(unit.objective),
      depends_on: asStrings(unit.depends_on),
      source_refs: asStrings(unit.input_file_refs),
      tool: asText(unit.tool),
      needs_human: unit.requires_human_gate === true,
      side_effect: ["run_workspace_write", "external_action"].includes(sideEffect)
        ? sideEffect as HarnessPlanNode["side_effect"]
        : "none",
    }];
  }) : [];
  return {
    units,
    summary: raw ? asText(raw.summary) || null : null,
    selectionReason: raw ? asText(raw.selection_reason) || null : null,
  };
}

function normalizeGap(value: unknown): EvidenceGap | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const gapId = asText(raw.gap_id);
  const label = asText(raw.label);
  const detail = asText(raw.detail);
  return gapId && label && detail
    ? { gap_id: gapId, label, detail, candidate_file_refs: asStrings(raw.candidate_file_refs) }
    : null;
}

function normalizeLoopRound(value: unknown): LoopRound | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const roundNumber = asNumber(raw.round_number);
  const phase = asText(raw.phase);
  const status = asText(raw.status);
  if (!roundNumber || !["observe", "plan", "act", "verify", "evidence_gate", "commit"].includes(phase)) return null;
  const plan = normalizePlan(raw.plan);
  const nextRaw = raw.next_step && typeof raw.next_step === "object" ? raw.next_step as Record<string, unknown> : null;
  const decision = asText(nextRaw?.decision, "pending") as LoopNextStep["decision"];
  const nextStep = nextRaw ? {
    decision,
    reason: asText(nextRaw.reason),
    next_question: asText(nextRaw.next_question) || null,
    candidate_file_refs: asStrings(nextRaw.candidate_file_refs),
  } : null;
  return {
    round_number: roundNumber,
    status: ["completed", "stopped", "failed"].includes(status) ? status as LoopRound["status"] : "running",
    phase: phase as LoopPhase,
    question: asText(raw.question, "核对本轮允许资料"),
    steer_instruction: asText(raw.steer_instruction) || null,
    input_file_refs: asStrings(raw.input_file_refs),
    plan: plan.units,
    plan_summary: plan.summary,
    selection_reason: plan.selectionReason,
    model_receipt: normalizeReceipt(raw.model_receipt),
    result: normalizeResult(raw.result),
    analysis_receipt: normalizeReceipt(raw.analysis_receipt),
    verified_file_refs: asStrings(raw.verified_file_refs),
    evidence_gaps: Array.isArray(raw.evidence_gaps)
      ? raw.evidence_gaps.map(normalizeGap).filter((item): item is EvidenceGap => item !== null)
      : [],
    next_step: nextStep,
  };
}

function activityItem(event: HarnessServerEvent): HarnessActivityItem {
  const labels: Record<string, string> = {
    workspace_index: "已建立整个资料库索引",
    planning_started: "规划模型开始组织任务",
    planning_completed: "规划模型返回工作计划",
    plan_validation_rejected: "候选计划未通过，正在受控重试",
    plan_validation: "服务端校验工作计划",
    ready_to_execute: "工作计划已准备",
    analysis_started: "分析模型开始读取内容",
    analysis_completed: "分析模型返回初步结果",
    result_validation: "服务端核对文件引用",
    round_started: "新一轮开始",
    evidence_gate: "证据门决定下一步",
    control_pause_recorded: "暂停请求已记录",
    control_paused: "已在安全点暂停",
    control_resume_recorded: "已恢复继续运行",
    control_steer_recorded: "方向指令已记录",
    control_steer_applied: "方向指令已应用",
    control_stop_recorded: "停止请求已记录",
    loop_committed: "只读任务简报已提交",
    loop_budget_stopped: "已在预算边界停止",
    loop_stopped: "已按你的要求停止",
    harness_failed: "本轮已安全停止",
  };
  const tone = event.event_name === "harness_failed" || event.event_name === "plan_validation_rejected" || event.event_name.includes("stopped") ? "warning"
    : event.event_name.includes("planning") || event.event_name.includes("analysis") ? "model"
      : event.event_name.includes("validation") || TERMINAL_EVENTS.has(event.event_name) ? "success" : "neutral";
  return {
    sequence: event.sequence,
    label: labels[event.event_name] ?? "服务端状态已更新",
    detail: event.message ?? "本轮状态来自服务端回执。",
    occurred_at: event.occurred_at,
    tone,
  };
}

function normalizeRun(value: unknown): HarnessRun | null {
  if (!value || typeof value !== "object") return null;
  const outer = value as Record<string, unknown>;
  const raw = outer.run && typeof outer.run === "object" ? outer.run as Record<string, unknown> : outer;
  const runId = asText(raw.run_id); const workspaceId = asText(raw.workspace_id);
  if (!runId || workspaceId !== "forte-public-office") return null;
  const plan = normalizePlan(raw.plan);
  const serverEvents = Array.isArray(raw.events) ? raw.events.flatMap((item): HarnessServerEvent[] => {
    if (!item || typeof item !== "object") return [];
    const event = item as Record<string, unknown>;
    return typeof event.sequence === "number" && asText(event.event_name)
      ? [{
          sequence: event.sequence,
          event_name: asText(event.event_name),
          occurred_at: asText(event.occurred_at) || undefined,
          message: asText(event.message) || undefined,
        }]
      : [];
  }) : [];
  const sourceDocuments = Array.isArray(raw.source_documents)
    ? raw.source_documents.flatMap((item): HarnessFile[] => {
        if (!item || typeof item !== "object") return [];
        const document = item as Record<string, unknown>;
        const fileRef = asText(document.file_ref);
        return fileRef ? [{
          file_ref: fileRef,
          folder_id: asText(document.folder_id),
          display_label: asText(document.display_label, "公开办公文件"),
          display_group: asText(document.display_group, "办公资料"),
          display_path: asText(document.display_path),
          display_summary: asText(document.display_summary, "公开办公文件"),
          extension: "FILE",
          mime: "application/octet-stream",
          size: 0,
          preview_kind: "unavailable",
          preview_available: false,
        }] : [];
      })
    : [];
  const contractRaw = raw.contract && typeof raw.contract === "object" ? raw.contract as Record<string, unknown> : {};
  const budgetRaw = raw.budget && typeof raw.budget === "object" ? raw.budget as Record<string, unknown> : {};
  const maxRounds = asNumber(contractRaw.max_rounds, asNumber(budgetRaw.max_rounds, 3));
  const maxFilesPerRound = asNumber(contractRaw.max_files_per_round, asNumber(budgetRaw.max_files_per_round, 4));
  const maxModelCalls = asNumber(contractRaw.max_model_calls, asNumber(budgetRaw.max_model_calls, 6));
  const deadlineSeconds = asNumber(contractRaw.deadline_seconds, asNumber(budgetRaw.deadline_seconds, 120));
  const rounds = Array.isArray(raw.rounds)
    ? raw.rounds.map(normalizeLoopRound).filter((item): item is LoopRound => item !== null)
    : [];
  const briefRaw = raw.brief && typeof raw.brief === "object" ? raw.brief as Record<string, unknown> : null;
  const brief = briefRaw ? {
    outcome: (["bounded", "user_stopped"].includes(asText(briefRaw.outcome)) ? asText(briefRaw.outcome) : "completed") as LoopBrief["outcome"],
    summary: asText(briefRaw.summary),
    verified_file_refs: asStrings(briefRaw.verified_file_refs),
    unresolved_gaps: Array.isArray(briefRaw.unresolved_gaps)
      ? briefRaw.unresolved_gaps.map(normalizeGap).filter((item): item is EvidenceGap => item !== null)
      : [],
    rounds_completed: asNumber(briefRaw.rounds_completed),
    external_action: "none" as const,
  } : null;
  const controlState = asText(raw.control_state);
  return {
    run_id: runId,
    workspace_id: workspaceId,
    status: asText(raw.status, "queued"),
    version: asNumber(raw.version, 1),
    last_event_sequence: asNumber(raw.last_event_sequence),
    instruction: asText(raw.instruction),
    source_documents: sourceDocuments,
    contract: {
      contract_version: asText(contractRaw.contract_version, "agent-control-loop.v1"),
      goal: asText(contractRaw.goal, asText(raw.instruction)),
      scope_mode: "whole_workspace",
      allowed_file_refs: asStrings(contractRaw.allowed_file_refs),
      completion_criteria: asStrings(contractRaw.completion_criteria),
      max_rounds: maxRounds,
      max_files_per_round: maxFilesPerRound,
      max_model_calls: maxModelCalls,
      deadline_seconds: deadlineSeconds,
      external_action: "none",
    },
    budget: {
      max_rounds: asNumber(budgetRaw.max_rounds, maxRounds),
      max_files_per_round: asNumber(budgetRaw.max_files_per_round, maxFilesPerRound),
      max_model_calls: asNumber(budgetRaw.max_model_calls, maxModelCalls),
      deadline_seconds: asNumber(budgetRaw.deadline_seconds, deadlineSeconds),
      rounds_used: asNumber(budgetRaw.rounds_used),
      files_verified: asNumber(budgetRaw.files_verified),
      model_calls_used: asNumber(budgetRaw.model_calls_used),
      elapsed_ms: asNumber(budgetRaw.elapsed_ms),
      stop_reason: asText(budgetRaw.stop_reason) || null,
    },
    rounds,
    current_round: asNumber(raw.current_round),
    control_state: (["pause_requested", "paused", "stop_requested", "stopped"].includes(controlState) ? controlState : "running") as HarnessRun["control_state"],
    brief,
    plan: plan.units,
    plan_summary: plan.summary ?? undefined,
    selection_reason: plan.selectionReason ?? undefined,
    model_receipt: normalizeReceipt(raw.model_receipt),
    analysis_receipt: normalizeReceipt(raw.analysis_receipt),
    result: normalizeResult(raw.result),
    validation_errors: asStrings(raw.validation_errors),
    events: serverEvents.map(activityItem).sort((a, b) => a.sequence - b.sequence),
  };
}

function toolLabel(tool: string) {
  const labels: Record<string, string> = {
    "file.read": "读取文件",
    "table.inspect": "检查表格",
    "artifact.write": "整理本轮成果",
    "evidence.verify": "核对引用",
  };
  return labels[tool] ?? "受控办公工具";
}

const LOOP_PHASES: { key: LoopPhase; label: string }[] = [
  { key: "observe", label: "读取" },
  { key: "plan", label: "规划" },
  { key: "act", label: "分析" },
  { key: "verify", label: "核对" },
  { key: "evidence_gate", label: "证据门" },
  { key: "commit", label: "提交" },
];

function gateLabel(decision: LoopNextStep["decision"] | undefined) {
  const labels: Record<LoopNextStep["decision"], string> = {
    pending: "等待服务端决定",
    next_round: "继续下一轮",
    completed: "完成条件已满足",
    budget_exhausted: "到达预算边界",
    waiting_input: "等待人工输入",
    user_stopped: "用户已停止",
    failed: "本轮未通过校验",
  };
  return labels[decision ?? "pending"];
}

function Receipt({ receipt, label }: { receipt: ModelReceipt | null; label: string }) {
  if (!receipt) return null;
  const status = !receipt.called ? "未调用" : receipt.output_used ? "已采用" : "未采用";
  const explanation = !receipt.called
    ? "本轮没有发起模型请求"
    : receipt.output_used
      ? "模型返回内容已通过服务端校验并进入下一步"
      : "模型已经返回，但没有通过服务端校验，因此未进入下一步";
  return <div className="trace-receipt">
    <IconSparkles aria-hidden="true" />
    <div><strong>{label}</strong><span>{receipt.called ? `${receipt.model} · ${(receipt.elapsed_ms / 1000).toFixed(1)} 秒` : "模型未调用"}</span></div>
    <b className={receipt.output_used ? "is-used" : "is-rejected"} title={explanation}>{status}</b>
  </div>;
}

export function HarnessActivityPane({ state }: { state: HarnessActivityState | null }) {
  if (!state) return <section className="trace-pane is-empty">
    <IconRoute aria-hidden="true" /><h2>Agent Control Loop</h2><p>任务开始后，这里会显示每轮读了什么、为什么继续，以及何时需要你介入。</p>
  </section>;
  const latestRound = state.rounds.at(-1) ?? null;
  const phaseIndex = latestRound ? LOOP_PHASES.findIndex((item) => item.key === latestRound.phase) : -1;
  const visibleEvents = state.events.slice(-5);
  const connectionLabel = state.connection === "live" ? "实时"
    : state.connection === "available" ? "可用"
      : state.connection === "reconnecting" ? "重连"
        : state.connection === "offline" ? "离线" : "连接";
  return <section className="trace-pane" aria-labelledby="trace-title">
    <header>
      <div className="trace-avatar"><IconSparkles aria-hidden="true" /></div>
      <div><span>可核对的执行路径</span><h2 id="trace-title">Agent Control Loop</h2></div>
      <b className={`is-${state.connection}`}><i />{connectionLabel}</b>
    </header>
    {state.instruction && <div className="trace-task"><span>任务目标</span><p>{state.instruction}</p></div>}
    {state.budget && <div className="trace-loop-facts" aria-label="循环预算">
      <span><b>{state.currentRound || 0}/{state.budget.max_rounds}</b>轮次</span>
      <span><b>{state.budget.files_verified}</b>文件已核对</span>
      <span><b>{state.budget.model_calls_used}/{state.budget.max_model_calls}</b>模型调用</span>
      <span><b>{Math.ceil(Math.max(0, state.budget.deadline_seconds * 1000 - state.budget.elapsed_ms) / 1000)}</b>秒剩余</span>
    </div>}
    {latestRound && <section className="trace-current-round" aria-label={`第 ${latestRound.round_number} 轮`}>
      <header><span>第 {latestRound.round_number} 轮</span><b>{gateLabel(latestRound.next_step?.decision)}</b></header>
      <ol>{LOOP_PHASES.slice(0, 5).map((phase, index) => <li key={phase.key} className={index < phaseIndex || latestRound.status === "completed" ? "is-complete" : index === phaseIndex ? "is-active" : ""}><span>{index < phaseIndex || latestRound.status === "completed" ? <IconCheck aria-hidden="true" /> : index + 1}</span><b>{phase.label}</b></li>)}</ol>
      {latestRound.evidence_gaps[0] && <p><IconAlertTriangle aria-hidden="true" />{latestRound.evidence_gaps[0].label}</p>}
    </section>}
    <div className="trace-receipts">
      <Receipt receipt={state.planningReceipt} label="规划模型" />
      <Receipt receipt={state.analysisReceipt} label="分析模型" />
    </div>
    <ol className="trace-list" aria-live="polite">
      {visibleEvents.length ? visibleEvents.map((item) => <li key={item.sequence} className={`is-${item.tone}`}>
        <span>{item.tone === "model" ? <IconSparkles aria-hidden="true" /> : item.tone === "success" ? <IconCheck aria-hidden="true" /> : item.tone === "warning" ? <IconAlertTriangle aria-hidden="true" /> : <IconCircleDot aria-hidden="true" />}</span>
        <div><strong>{item.label}</strong><p>{item.detail}</p>{item.occurred_at && <small>{new Date(item.occurred_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}</small>}</div>
      </li>) : <li><span><IconClock aria-hidden="true" /></span><div><strong>等待任务</strong><p>你只需给出目标，Agent 会在整个资料库中自行寻找证据。</p></div></li>}
    </ol>
    {state.events.length > visibleEvents.length && <details className="trace-history"><summary>查看全部 {state.events.length} 条服务端轨迹</summary><ol>{state.events.map((item) => <li key={item.sequence}><b>{item.label}</b><span>{item.detail}</span></li>)}</ol></details>}
    {state.brief && <footer className={state.brief.outcome === "completed" ? "is-success" : "is-warning"}><IconCircleCheck aria-hidden="true" /><span>{state.brief.summary}</span></footer>}
    {state.error && <footer className="is-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{state.error}</span></footer>}
  </section>;
}
export function HarnessWorkbench({ onActivityChange }: { onActivityChange?: (state: HarnessActivityState | null) => void }) {
  const [workspace, setWorkspace] = useState<HarnessWorkspace | null>(null);
  const [activeFileRef, setActiveFileRef] = useState("");
  const [preview, setPreview] = useState<HarnessPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [instruction, setInstruction] = useState("");
  const [maxRounds, setMaxRounds] = useState(3);
  const [maxFilesPerRound, setMaxFilesPerRound] = useState(6);
  const [maxModelCalls, setMaxModelCalls] = useState(6);
  const [deadlineSeconds, setDeadlineSeconds] = useState(120);
  const [fileSearch, setFileSearch] = useState("");
  const [fileTypeFilter, setFileTypeFilter] = useState<FileTypeFilter>("ALL");
  const [view, setView] = useState<WorkspaceView>("data");
  const [run, setRun] = useState<HarnessRun | null>(null);
  const [workspaceStatus, setWorkspaceStatus] = useState<WorkspaceStatus>("checking");
  const [workspaceError, setWorkspaceError] = useState("");
  const [starting, setStarting] = useState(false);
  const [controlBusy, setControlBusy] = useState<LoopCommand | null>(null);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<ConnectionState>("connecting");
  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<number | undefined>(undefined);
  const requestRef = useRef(0);
  const previewRequestRef = useRef(0);
  const generationRef = useRef(0);
  const runRef = useRef<HarnessRun | null>(null);
  const lastSequenceRef = useRef(0);
  const startCommandRef = useRef<{ signature: string; key: string } | null>(null);
  const controlCommandRef = useRef<{ signature: string; key: string } | null>(null);

  const allFiles = useMemo(() => workspace?.folders.flatMap((folder) => folder.files) ?? [], [workspace]);
  const activeFile = allFiles.find((file) => file.file_ref === activeFileRef) ?? null;
  const availableFileTypes = useMemo(() => {
    return Array.from(new Set(allFiles.map((file) => file.extension))).sort((left, right) => left.localeCompare(right));
  }, [allFiles]);
  const filteredFiles = useMemo(() => {
    const query = fileSearch.trim().toLocaleLowerCase("zh-CN");
    return allFiles.filter((file) => {
      if (fileTypeFilter !== "ALL" && file.extension !== fileTypeFilter) return false;
      return !query || `${file.display_label} ${file.display_path} ${file.display_summary} ${file.extension}`.toLocaleLowerCase("zh-CN").includes(query);
    });
  }, [allFiles, fileSearch, fileTypeFilter]);

  function closeTransport() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    window.clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = undefined;
  }

  function applySnapshot(snapshot: HarnessRun, generation: number) {
    if (generation !== generationRef.current) return false;
    const current = runRef.current;
    if (current && current.run_id !== snapshot.run_id) return false;
    if (snapshot.last_event_sequence < lastSequenceRef.current || (current && snapshot.version < current.version)) return false;
    runRef.current = snapshot;
    lastSequenceRef.current = Math.max(lastSequenceRef.current, snapshot.last_event_sequence);
    setRun(snapshot);
    if (snapshot.events.length) setConnection(TERMINAL_STATUSES.has(snapshot.status) ? "available" : "live");
    return true;
  }

  async function refreshRun(runId: string, generation: number) {
    const response = await fetch(`${API_BASE}/v1/harness/runs/${encodeURIComponent(runId)}`, { headers: HEADERS });
    if (!response.ok) throw new Error("无法读取最新任务状态");
    const snapshot = normalizeRun(await response.json());
    if (!snapshot) throw new Error("任务状态格式无效");
    return applySnapshot(snapshot, generation) ? snapshot : runRef.current;
  }

  function connectEvents(runId: string, generation: number, after: number) {
    closeTransport();
    if (generation !== generationRef.current) return;
    setConnection("connecting");
    const source = new EventSource(`${API_BASE}/v1/harness/runs/${encodeURIComponent(runId)}/events?after=${after}`);
    eventSourceRef.current = source;
    source.onopen = () => { if (generation === generationRef.current) setConnection("live"); };
    for (const eventName of NAMED_EVENTS) {
      source.addEventListener(eventName, () => {
        if (generation !== generationRef.current) return;
        void refreshRun(runId, generation).then((snapshot) => {
          if (snapshot && TERMINAL_EVENTS.has(eventName)) {
            closeTransport();
            setConnection("available");
          }
        }).catch(() => setConnection("reconnecting"));
      });
    }
    source.onerror = () => {
      source.close();
      if (eventSourceRef.current === source) eventSourceRef.current = null;
      if (generation !== generationRef.current || TERMINAL_STATUSES.has(runRef.current?.status ?? "")) return;
      setConnection("reconnecting");
      reconnectTimerRef.current = window.setTimeout(async () => {
        try {
          const snapshot = await refreshRun(runId, generation);
          if (snapshot && !TERMINAL_STATUSES.has(snapshot.status)) connectEvents(runId, generation, snapshot.last_event_sequence);
          else setConnection("available");
        } catch {
          if (generation === generationRef.current) connectEvents(runId, generation, lastSequenceRef.current);
        }
      }, 800);
    };
  }

  async function loadWorkspace() {
    const requestId = ++requestRef.current;
    setWorkspaceStatus("checking"); setWorkspaceError(""); setConnection("connecting");
    try {
      const response = await fetchWithTimeout(`${API_BASE}/v1/harness/workspace`, { headers: HEADERS });
      if (!response.ok) throw new Error(response.status === 503 ? "办公资料库完整性校验未通过" : "办公资料库暂时无法读取");
      const normalized = normalizeWorkspace(await response.json());
      if (!normalized || normalized.file_count !== normalized.folders.reduce((total, folder) => total + folder.files.length, 0)) throw new Error("办公资料库返回内容不完整");
      if (requestId !== requestRef.current) return;
      setWorkspace(normalized); setWorkspaceStatus("online"); setConnection("available");
      const firstFolder = normalized.folders.find((folder) => folder.files.length > 0);
      const firstFile = firstFolder?.files[0];
      setActiveFileRef((current) => current || firstFile?.file_ref || "");
    } catch (caught) {
      if (requestId !== requestRef.current) return;
      const message = caught instanceof Error ? caught.message : "办公资料库暂时无法读取";
      setWorkspace(null); setWorkspaceStatus("unavailable"); setWorkspaceError(message); setConnection("offline");
    }
  }

  useEffect(() => { void loadWorkspace(); return closeTransport; }, []);

  useEffect(() => {
    if (!activeFileRef) { setPreview(null); return; }
    const requestId = ++previewRequestRef.current;
    setPreviewLoading(true); setPreviewError("");
    void fetch(`${API_BASE}/v1/harness/workspace/files/${encodeURIComponent(activeFileRef)}`, { headers: HEADERS })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 503 ? "文件完整性校验未通过" : "文件预览暂时不可用");
        const normalized = normalizePreview(await response.json());
        if (!normalized) throw new Error("文件预览格式无效");
        if (requestId === previewRequestRef.current) setPreview(normalized);
      })
      .catch((caught) => {
        if (requestId === previewRequestRef.current) {
          setPreview(null); setPreviewError(caught instanceof Error ? caught.message : "文件预览暂时不可用");
        }
      })
      .finally(() => { if (requestId === previewRequestRef.current) setPreviewLoading(false); });
  }, [activeFileRef]);

  useEffect(() => {
    onActivityChange?.({
      workspaceTitle: workspace?.title ?? "FORTE 公开办公资料库",
      instruction: run?.instruction ?? null,
      runStatus: run?.status ?? null,
      connection,
      planningReceipt: run?.model_receipt ?? null,
      analysisReceipt: run?.analysis_receipt ?? null,
      events: run?.events ?? [],
      resultReady: Boolean(run?.result),
      contract: run?.contract ?? null,
      budget: run?.budget ?? null,
      rounds: run?.rounds ?? [],
      currentRound: run?.current_round ?? 0,
      controlState: run?.control_state ?? null,
      brief: run?.brief ?? null,
      error: error || run?.validation_errors[0] || null,
    });
  }, [workspace, run, connection, error, onActivityChange]);

  function openFile(file: HarnessFile) {
    setActiveFileRef(file.file_ref); setView("data");
  }

  async function startTask(suggestedInstruction?: string) {
    const taskInstruction = suggestedInstruction?.trim() || instruction.trim();
    if (!workspace || taskInstruction.length < 3) return;
    if (suggestedInstruction) setInstruction(taskInstruction);
    const signature = JSON.stringify({
      instruction: taskInstruction,
      loop: { maxRounds, maxFilesPerRound, maxModelCalls, deadlineSeconds },
    });
    const command = startCommandRef.current?.signature === signature
      ? startCommandRef.current
      : { signature, key: randomKey() };
    startCommandRef.current = command;
    setStarting(true); setError(""); closeTransport();
    const generation = generationRef.current + 1;
    generationRef.current = generation; runRef.current = null; lastSequenceRef.current = 0; setRun(null);
    try {
      const response = await fetch(`${API_BASE}/v1/harness/runs`, {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({
          workspace_id: workspace.workspace_id,
          idempotency_key: command.key,
          expected_version: 1,
          instruction: taskInstruction,
          loop: {
            max_rounds: maxRounds,
            max_files_per_round: maxFilesPerRound,
            max_model_calls: maxModelCalls,
            deadline_seconds: deadlineSeconds,
          },
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(asText((payload as Record<string, unknown>).detail, "任务没有启动"));
      const snapshot = normalizeRun(payload);
      if (!snapshot || !applySnapshot(snapshot, generation)) throw new Error("任务回执格式无效");
      setView("loop");
      if (!TERMINAL_STATUSES.has(snapshot.status)) connectEvents(snapshot.run_id, generation, snapshot.last_event_sequence);
      else setConnection("available");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "任务没有启动");
      setConnection("available");
    } finally { setStarting(false); }
  }

  async function controlLoop(command: LoopCommand, steerInstruction?: string) {
    const current = runRef.current;
    if (!current || TERMINAL_STATUSES.has(current.status)) return false;
    const normalizedInstruction = steerInstruction?.trim() || undefined;
    const signature = JSON.stringify({ command, instruction: normalizedInstruction, runId: current.run_id });
    const controlCommand = controlCommandRef.current?.signature === signature
      ? controlCommandRef.current
      : { signature, key: `control-${randomKey()}` };
    controlCommandRef.current = controlCommand;
    setControlBusy(command); setError("");
    try {
      const response = await fetch(`${API_BASE}/v1/harness/runs/${encodeURIComponent(current.run_id)}/controls`, {
        method: "POST",
        headers: HEADERS,
        body: JSON.stringify({
          command,
          idempotency_key: controlCommand.key,
          expected_version: current.version,
          instruction: normalizedInstruction,
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 409) await refreshRun(current.run_id, generationRef.current).catch(() => null);
        throw new Error(asText((payload as Record<string, unknown>).detail, "控制命令没有被服务端接受"));
      }
      const snapshot = normalizeRun(payload);
      if (!snapshot || !applySnapshot(snapshot, generationRef.current)) throw new Error("控制回执格式无效");
      controlCommandRef.current = null;
      if (!eventSourceRef.current && !TERMINAL_STATUSES.has(snapshot.status)) {
        connectEvents(snapshot.run_id, generationRef.current, snapshot.last_event_sequence);
      }
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "控制命令没有被服务端接受");
      return false;
    } finally {
      setControlBusy(null);
    }
  }

  if (workspaceStatus !== "online" || !workspace) return <div className={`data-workbench-empty ${workspaceStatus === "unavailable" ? "is-error" : ""}`}>
    {workspaceStatus === "checking" ? <IconLoader2 aria-hidden="true" /> : <IconAlertTriangle aria-hidden="true" />}
    <h1>{workspaceStatus === "checking" ? "正在核对办公资料库" : "办公资料库暂时无法读取"}</h1>
    <p>{workspaceStatus === "checking" ? "服务端正在校验公开文件清单、大小与完整性。" : workspaceError}</p>
    {workspaceStatus === "unavailable" && <button type="button" onClick={() => void loadWorkspace()}><IconRefresh aria-hidden="true" />重新读取</button>}
  </div>;

  const runActive = Boolean(run && !TERMINAL_STATUSES.has(run.status));

  return <main className="data-workbench">
    <header className="data-workbench-header">
      <div><span>FORTE 公开办公数据</span><h1>办公资料库</h1><p>像文件管理器一样自由查看资料；下达目标后，Agent 会从整个资料库自主检索证据。</p></div>
      <div className="data-workbench-status">
        <b className={`is-${connection}`}><i />{connection === "offline" ? "服务离线" : connection === "reconnecting" ? "正在恢复" : "资料可用"}</b>
        <button type="button" className="icon-action" title="重新核对资料库" aria-label="重新核对资料库" onClick={() => void loadWorkspace()}><IconRefresh aria-hidden="true" /></button>
      </div>
    </header>
    <div className="workspace-facts" aria-label="资料库信息">
      <span><strong>{workspace.file_count}</strong> 份文件统一检索</span>
      <span><strong>{workspace.previewable_file_count}</strong> 份可安全预览</span>
      <span><strong>只读</strong> 不改原文件</span>
      <span><strong>{workspace.license}</strong> 公开许可</span>
    </div>
    <div className="data-workbench-grid">
      <aside className="dataset-browser" aria-label="FORTE 文件目录">
        <header>
          <div><IconDatabase aria-hidden="true" /><div><strong>全部文件</strong><span>办公资料库 / {workspace.file_count} 项</span></div></div>
          <label><IconSearch aria-hidden="true" /><input value={fileSearch} onChange={(event) => setFileSearch(event.target.value)} placeholder="查找文件" aria-label="查找文件" /></label>
          <nav className="file-type-filters" aria-label="按文件类型筛选">
            {["ALL", ...availableFileTypes].map((extension) => <button type="button" key={extension} className={fileTypeFilter === extension ? "is-active" : ""} onClick={() => setFileTypeFilter(extension)}>{extension === "ALL" ? "全部" : extension}</button>)}
          </nav>
        </header>
        <div className="file-manager-columns" aria-hidden="true"><span>名称</span><span>类型</span></div>
        <div className="file-manager-list" role="list">
          {filteredFiles.length ? filteredFiles.map((file) => <button type="button" role="listitem" key={file.file_ref} className={file.file_ref === activeFileRef ? "is-open" : ""} onClick={() => openFile(file)} title={file.display_path}>
            <IconFile aria-hidden="true" />
            <span><strong>{file.display_label}</strong><small>{file.display_summary}</small></span>
            <b>{file.extension}</b>
          </button>) : <p className="dataset-unavailable">没有符合当前筛选条件的文件。</p>}
        </div>
      </aside>
      <section className="data-task-surface">
        <section className="task-composer" aria-labelledby="task-composer-title">
          <div><span>研究整个资料库</span><h2 id="task-composer-title">你想让 Agent 找什么，或推进什么？</h2></div>
          <textarea value={instruction} disabled={runActive} onChange={(event) => setInstruction(event.target.value)} placeholder="例如：研究整个资料库，找出需要继续推动的工作，并逐条说明文件依据" aria-label="任务指令" />
          <details className="loop-contract-settings">
            <summary><IconAdjustments aria-hidden="true" />Agent Control Loop · 最多 {maxRounds} 轮 / {maxModelCalls} 次模型调用 / {deadlineSeconds} 秒</summary>
            <div>
              <label><span>最大轮次</span><input type="number" min="1" max="3" value={maxRounds} disabled={runActive} onChange={(event) => setMaxRounds(Math.max(1, Math.min(3, Number(event.target.value) || 1)))} /></label>
              <label><span>每轮文件</span><input type="number" min="1" max="8" value={maxFilesPerRound} disabled={runActive} onChange={(event) => setMaxFilesPerRound(Math.max(1, Math.min(8, Number(event.target.value) || 1)))} /></label>
              <label><span>模型调用</span><input type="number" min="2" max="6" value={maxModelCalls} disabled={runActive} onChange={(event) => setMaxModelCalls(Math.max(2, Math.min(6, Number(event.target.value) || 2)))} /></label>
              <label><span>时间上限</span><input type="number" min="20" max="300" step="10" value={deadlineSeconds} disabled={runActive} onChange={(event) => setDeadlineSeconds(Math.max(20, Math.min(300, Number(event.target.value) || 20)))} /></label>
            </div>
          </details>
          <div className="task-examples" aria-label="任务示例">{TASK_EXAMPLES.map((example) => <button type="button" key={example} disabled={runActive} onClick={() => setInstruction(example)}>{example}</button>)}</div>
          <footer>
            <div className="selection-summary"><IconSearch aria-hidden="true" /><span>{runActive ? `Agent 正在整个资料库中自主检索 · 每轮最多 ${run?.contract.max_files_per_round ?? maxFilesPerRound} 份` : `整个资料库已纳入检索范围 · Agent 每轮自主选择最多 ${maxFilesPerRound} 份`}</span></div>
            <button type="button" onClick={() => void startTask()} disabled={runActive || starting || instruction.trim().length < 3}>{starting ? <IconLoader2 aria-hidden="true" /> : <IconSend aria-hidden="true" />}{starting ? "正在启动" : runActive ? "当前 Loop 运行中" : "启动 Control Loop"}</button>
          </footer>
        </section>
        <nav className="workspace-tabs" aria-label="工作区视图">
          <button type="button" className={view === "data" ? "is-active" : ""} onClick={() => setView("data")}><IconFileDescription aria-hidden="true" />预览</button>
          <button type="button" className={view === "loop" ? "is-active" : ""} onClick={() => setView("loop")}><IconRoute aria-hidden="true" />Agent 路径{run?.rounds.length ? <b>{run.rounds.length}</b> : null}</button>
          <button type="button" className={view === "result" ? "is-active" : ""} onClick={() => setView("result")}><IconCircleCheck aria-hidden="true" />发现与建议{run?.result ? <b>{run.result.findings.length}</b> : null}</button>
        </nav>
        <div className="workspace-content">
          {view === "data" && <FilePreview preview={preview} file={activeFile} loading={previewLoading} error={previewError} />}
          {view === "loop" && <LoopView run={run} files={allFiles} controlBusy={controlBusy} onControl={controlLoop} />}
          {view === "result" && <ResultView result={run?.result ?? null} files={allFiles} onOpenFile={openFile} onStartTask={startTask} starting={starting} />}
        </div>
        <details className="workspace-boundary"><summary><IconShieldCheck aria-hidden="true" />数据与执行边界</summary><p>{workspace.data_boundary} Agent 可以检索整个资料库，但每轮只读取服务端校验通过且受预算约束的文件；本轮不会修改原文件或执行外部动作。</p></details>
        {error && <div className="workspace-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{error}</span></div>}
      </section>
    </div>
  </main>;
}

function FilePreview({ preview, file, loading, error }: { preview: HarnessPreview | null; file: HarnessFile | null; loading: boolean; error: string }) {
  if (!file) return <div className="file-preview-empty"><IconFile aria-hidden="true" /><h2>从文件列表打开一份资料</h2><p>浏览文件不会限制 Agent 的检索范围；任务启动后由 Agent 自己选择相关证据。</p></div>;
  if (loading) return <div className="file-preview-empty"><IconLoader2 aria-hidden="true" /><h2>正在安全读取</h2><p>服务端正在核对完整性并生成只读预览。</p></div>;
  if (error || !preview) return <div className="file-preview-empty is-error"><IconAlertTriangle aria-hidden="true" /><h2>文件预览不可用</h2><p>{error || "没有收到可用的预览。"}</p></div>;
  return <article className="file-preview">
    <header><div><span>办公资料库</span><h2>{preview.display_label}</h2><p>{preview.display_path}</p></div><div className="file-meta"><b>{file.extension}</b><span>{formatSize(preview.size)}</span>{preview.page_count !== null && <span>{preview.page_count} 页</span>}{preview.total_rows !== null && <span>{preview.total_rows} 行</span>}</div></header>
    {preview.kind === "table" ? <div className="table-preview"><table><thead><tr><th className="row-number">#</th>{preview.columns.map((column, index) => <th key={`${column}:${index}`}>{column || `列 ${index + 1}`}</th>)}</tr></thead><tbody>{preview.rows.map((row) => <tr key={row.row_number}><td className="row-number">{row.row_number}</td>{preview.columns.map((_, index) => <td key={index}>{row.values[index] ?? ""}</td>)}</tr>)}</tbody></table></div> : <pre className="document-preview">{preview.text || "此文件没有可提取的文本层。"}</pre>}
    <footer className="preview-security"><IconShieldCheck aria-hidden="true" /><div><strong>安全预览</strong><span>{preview.security.notes.join(" · ")}</span>{preview.truncated && <span>当前仅显示部分内容</span>}</div></footer>
  </article>;
}

function LoopView({
  run,
  files,
  controlBusy,
  onControl,
}: {
  run: HarnessRun | null;
  files: HarnessFile[];
  controlBusy: LoopCommand | null;
  onControl: (command: LoopCommand, instruction?: string) => Promise<boolean>;
}) {
  const [selectedRoundNumber, setSelectedRoundNumber] = useState(1);
  const [steerDraft, setSteerDraft] = useState("");
  useEffect(() => {
    if (run?.current_round) setSelectedRoundNumber(run.current_round);
  }, [run?.current_round, run?.rounds.length]);

  if (!run) return <div className="workspace-placeholder"><IconRoute aria-hidden="true" /><h2>Agent Control Loop 尚未启动</h2><p>提交目标后，Agent 会先搜索整个资料库，再公开每轮选了什么、为什么选、得到什么和下一步怎么走。</p></div>;

  const selectedRound = run.rounds.find((item) => item.round_number === selectedRoundNumber) ?? run.rounds.at(-1) ?? null;
  const terminal = TERMINAL_STATUSES.has(run.status);
  const canResume = run.control_state === "paused" || run.control_state === "pause_requested";
  const canPause = !terminal && run.control_state === "running";
  const canSteer = !terminal && ![ "stop_requested", "stopped" ].includes(run.control_state);
  const fileLabel = (fileRef: string) => files.find((file) => file.file_ref === fileRef)?.display_label ?? "允许范围内的文件";

  return <section className="loop-view" aria-labelledby="loop-view-title">
    <header className="loop-contract">
      <div><span>Agent Control Loop</span><h2 id="loop-view-title">{run.contract.goal}</h2></div>
      <div className="loop-budget">
        <span><b>{run.budget.rounds_used}/{run.budget.max_rounds}</b>轮</span>
        <span><b>{run.budget.files_verified}</b>文件已核对</span>
        <span><b>{run.budget.model_calls_used}/{run.budget.max_model_calls}</b>调用</span>
        <span><b>{Math.ceil(run.budget.elapsed_ms / 1000)}</b>秒</span>
      </div>
    </header>
    <section className="loop-controls" aria-label="人工控制">
      <div className="loop-control-actions">
        <button type="button" onClick={() => void onControl(canResume ? "resume" : "pause")} disabled={controlBusy !== null || terminal || (!canResume && !canPause)}>
          {canResume ? <IconPlayerPlay aria-hidden="true" /> : <IconPlayerPause aria-hidden="true" />}
          {controlBusy === "pause" || controlBusy === "resume" ? "正在提交" : canResume ? "继续" : "暂停"}
        </button>
        <button type="button" className="is-stop" onClick={() => void onControl("stop")} disabled={controlBusy !== null || terminal}><IconPlayerStop aria-hidden="true" />结束并保留现有结果</button>
      </div>
      <form onSubmit={async (event) => {
        event.preventDefault();
        if (!steerDraft.trim()) return;
        if (await onControl("steer", steerDraft)) setSteerDraft("");
      }}>
        <label htmlFor="loop-steer">调整下一轮方向</label>
        <div><input id="loop-steer" value={steerDraft} onChange={(event) => setSteerDraft(event.target.value)} placeholder="例如：下一轮优先核对付款条件" disabled={!canSteer || controlBusy !== null} /><button type="submit" disabled={!canSteer || controlBusy !== null || steerDraft.trim().length < 3}><IconArrowRight aria-hidden="true" /><span>记录</span></button></div>
      </form>
      {run.control_state === "pause_requested" && <p>暂停请求已记录，当前模型调用结束后会在安全点暂停。</p>}
      {run.control_state === "paused" && <p>Loop 已暂停，现有轮次、引用和预算都已保留。</p>}
      {run.control_state === "stop_requested" && <p>正在到达停止安全点，不会启动新的模型调用。</p>}
    </section>
    <nav className="loop-round-tabs" aria-label="研究轮次">
      {run.rounds.length ? run.rounds.map((round) => <button type="button" key={round.round_number} className={round.round_number === selectedRound?.round_number ? "is-active" : ""} onClick={() => setSelectedRoundNumber(round.round_number)}>
        <span>{round.status === "completed" ? <IconCheck aria-hidden="true" /> : round.round_number}</span>
        <b>第 {round.round_number} 轮</b>
        <small>{round.next_step ? gateLabel(round.next_step.decision) : LOOP_PHASES.find((phase) => phase.key === round.phase)?.label}</small>
      </button>) : <span>服务端正在建立第一轮。</span>}
    </nav>
    {selectedRound && <article className="loop-round-detail">
      <header><div><span>本轮问题</span><h3>{selectedRound.question}</h3></div><b>{gateLabel(selectedRound.next_step?.decision)}</b></header>
      <ol className="loop-phase-rail">
        {LOOP_PHASES.slice(0, 5).map((phase, index) => {
          const activeIndex = LOOP_PHASES.findIndex((item) => item.key === selectedRound.phase);
          const complete = index < activeIndex || selectedRound.status === "completed";
          return <li key={phase.key} className={complete ? "is-complete" : index === activeIndex ? "is-active" : ""}><span>{complete ? <IconCheck aria-hidden="true" /> : index + 1}</span><b>{phase.label}</b></li>;
        })}
      </ol>
      {selectedRound.input_file_refs.length > 0 && <section className="loop-round-files"><span>Agent 本轮自主选择</span>{selectedRound.selection_reason && <p>{selectedRound.selection_reason}</p>}<div>{selectedRound.input_file_refs.map((ref) => <b key={ref}>{fileLabel(ref)}</b>)}</div></section>}
      {selectedRound.plan.length > 0 && <details className="loop-plan" open={selectedRound.status === "running"}>
        <summary>服务端已采用的本轮计划 · {selectedRound.plan.length} 个工作单元</summary>
        <ol>{selectedRound.plan.map((node, index) => <li key={node.node_id}><span>{index + 1}</span><div><b>{node.label}</b><p>{node.description}</p></div></li>)}</ol>
      </details>}
      {selectedRound.result && <section className="loop-round-result"><span>本轮核对结果</span><h3>{selectedRound.result.summary}</h3><p>{selectedRound.result.findings.length} 条发现，引用 {selectedRound.verified_file_refs.length} 份文件。</p></section>}
      {selectedRound.evidence_gaps.length > 0 && <section className="loop-gap"><IconAlertTriangle aria-hidden="true" /><div><span>证据缺口</span><h3>{selectedRound.evidence_gaps[0].label}</h3><p>{selectedRound.evidence_gaps[0].detail}</p></div></section>}
      {selectedRound.next_step && <footer className={selectedRound.next_step.decision === "completed" ? "is-complete" : "is-next"}><div><span>服务端决定</span><strong>{gateLabel(selectedRound.next_step.decision)}</strong><p>{selectedRound.next_step.reason}</p></div>{selectedRound.next_step.decision === "next_round" && <IconArrowRight aria-hidden="true" />}</footer>}
    </article>}
    {run.brief && <section className={`loop-brief is-${run.brief.outcome}`}><IconCircleCheck aria-hidden="true" /><div><span>任务简报</span><h3>{run.brief.summary}</h3><p>外部动作：未发生 · 结果仍需人工复核</p></div></section>}
  </section>;
}
function ResultView({
  result,
  files,
  onOpenFile,
  onStartTask,
  starting,
}: {
  result: HarnessResult | null;
  files: HarnessFile[];
  onOpenFile: (file: HarnessFile) => void;
  onStartTask: (instruction: string) => Promise<void>;
  starting: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!result) return <div className="workspace-placeholder"><IconClock aria-hidden="true" /><h2>任务简报尚未形成</h2><p>Agent Control Loop 完成只读分析并通过文件引用校验后，简报会出现在这里。</p></div>;
  const visibleFindings = expanded ? result.findings : result.findings.slice(0, 3);
  return <article className="result-view"><header><IconCircleCheck aria-hidden="true" /><div><span>资料库研究结果 · 待复核</span><h2>{result.summary}</h2></div></header><div className="result-findings">{visibleFindings.map((finding, index) => <section key={`${finding.title}:${index}`}><b>{index + 1}</b><div><h3>{finding.title}</h3><p>{finding.detail}</p><footer>{finding.file_refs.map((ref) => {
    const file = files.find((item) => item.file_ref === ref);
    return file ? <button type="button" key={ref} onClick={() => onOpenFile(file)}><IconFile aria-hidden="true" />{file.display_label}</button> : null;
  })}</footer></div></section>)}</div>{result.findings.length > 3 && <button type="button" className="result-expand" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}><IconChevronDown className={expanded ? "is-open" : ""} aria-hidden="true" />{expanded ? "收起详细发现" : `查看其余 ${result.findings.length - 3} 条发现`}</button>}{result.follow_ups.length > 0 && <section className="result-proposals" aria-labelledby="result-proposals-title"><header><span>Agent 建议的下一步</span><h3 id="result-proposals-title">由你确认后，才会成为新的 Control Loop</h3></header>{result.follow_ups.map((item, index) => <article key={`${item}:${index}`}><div><b>建议 {index + 1}</b><p>{item}</p></div><button type="button" disabled={starting} onClick={() => void onStartTask(item)}><IconPlayerPlay aria-hidden="true" />{starting ? "正在启动" : "确认并启动"}</button></article>)}</section>}<footer><IconShieldCheck aria-hidden="true" />这些建议由模型基于本轮已读取资料生成，尚未逐项验证；只有你点击确认后才会启动新任务，本轮没有修改原文件或执行外部动作。</footer></article>;
}
