"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconAdjustments,
  IconCheck,
  IconChevronDown,
  IconChevronRight,
  IconCircleCheck,
  IconCircleDot,
  IconClock,
  IconDatabase,
  IconEye,
  IconFile,
  IconFileDescription,
  IconFolder,
  IconFolderOpen,
  IconGitCommit,
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
  IconX,
} from "@tabler/icons-react";

type ConnectionState = "connecting" | "available" | "live" | "reconnecting" | "offline";
type WorkspaceStatus = "checking" | "online" | "unavailable";
type WorkspaceView = "data" | "loop" | "result";
type FileTypeFilter = string;
type PreviewKind = "table" | "document" | "pdf" | "text" | "unavailable";
type LoopPhase = "observe" | "plan" | "act" | "verify" | "evidence_gate" | "commit";
type LoopCommand = "pause" | "resume" | "steer" | "stop" | "rollback";
type LoopControlOptions = { instruction?: string; branchId?: string; artifactVersion?: number };
type EvidenceRole = "expected" | "observed" | "support" | "contradiction" | "context";
type EvidenceAnchor = {
  file_ref: string;
  role: EvidenceRole;
  label: string;
  locator_kind: "text_lines" | "table_rows";
  start: number;
  end: number;
  excerpt: string;
};

type WorkspaceTreeFolder = {
  path: string;
  label: string;
  summary: string;
  availability: HarnessFolder["availability"];
  files: HarnessFile[];
  folders: WorkspaceTreeFolder[];
  fileCount: number;
};

type EvidenceReviewRequest = {
  reviewKey: string;
  kind: "finding" | "gap" | "proposal";
  eyebrow: string;
  title: string;
  detail: string;
  status: string;
  roundNumber: number | null;
  branchTitle: string | null;
  fileRefs: string[];
  anchors: EvidenceAnchor[];
  serverFact: string;
  boundary: string;
};

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
type HarnessFinding = { title: string; detail: string; file_refs: string[]; evidence_anchors: EvidenceAnchor[] };
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
  branch_id: string | null;
  label: string;
  detail: string;
  candidate_file_refs: string[];
};

type LoopNextStep = {
  decision: "pending" | "next_round" | "completed" | "budget_exhausted" | "waiting_input" | "user_stopped" | "failed";
  reason: string;
  next_question: string | null;
  candidate_file_refs: string[];
  candidate_branch_ids: string[];
};

type LoopRound = {
  round_number: number;
  status: "running" | "completed" | "stopped" | "failed";
  phase: LoopPhase;
  question: string;
  steer_instruction: string | null;
  input_file_refs: string[];
  branch_ids: string[];
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

type LoopBranch = {
  branch_id: string;
  unit_id: string;
  round_number: number;
  parent_branch_id: string | null;
  title: string;
  objective: string;
  depends_on: string[];
  input_file_refs: string[];
  verified_file_refs: string[];
  missing_file_refs: string[];
  status: "running" | "completed" | "waiting_input" | "stopped" | "failed";
  requires_human_gate: boolean;
  created_at: string;
  updated_at: string;
};

type LoopBrief = {
  outcome: "completed" | "bounded" | "user_stopped";
  summary: string;
  verified_file_refs: string[];
  unresolved_gaps: EvidenceGap[];
  rounds_completed: number;
  external_action: "none";
};

type ArtifactVersion = {
  artifact_id: string;
  version: number;
  title: string;
  kind: "evidence_brief";
  status: "draft" | "verified" | "committed";
  round_number: number;
  summary: string;
  findings: HarnessFinding[];
  follow_ups: string[];
  evidence_gaps: EvidenceGap[];
  source_file_refs: string[];
  finding_count: number;
  parent_version: number | null;
  created_at: string;
  review_required: true;
  external_action: "none";
};

type LoopCommit = {
  commit_id: string;
  artifact_id: string;
  artifact_version: number;
  operation: "commit" | "rollback";
  parent_commit_id: string | null;
  summary: string;
  committed_at: string;
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
  branches: LoopBranch[];
  active_branch_id: string | null;
  artifact_versions: ArtifactVersion[];
  commits: LoopCommit[];
  last_commit: LoopCommit | null;
  recovered: boolean;
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
const RUN_SESSION_KEY = "office-agent:forte-public-office:active-run";
const NAMED_EVENTS = [
  "workspace_index",
  "checkpoint_recovered",
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

function splitDisplayPath(path: string) {
  return path.split("/").map((part) => part.trim()).filter(Boolean);
}

function fileAncestorPaths(file: HarnessFile) {
  const parts = splitDisplayPath(file.display_path).slice(0, -1);
  return parts.map((_, index) => parts.slice(0, index + 1).join("/"));
}

function buildWorkspaceTree(workspace: HarnessWorkspace) {
  return workspace.folders.map((folder): WorkspaceTreeFolder => {
    const root: WorkspaceTreeFolder = {
      path: folder.display_label,
      label: folder.display_label,
      summary: folder.display_summary,
      availability: folder.availability,
      files: [],
      folders: [],
      fileCount: folder.files.length,
    };
    for (const file of folder.files) {
      const parts = splitDisplayPath(file.display_path);
      const nestedParts = parts[0] === folder.display_label || parts[0] === file.display_group
        ? parts.slice(1, -1)
        : parts.slice(0, -1);
      let parent = root;
      for (const part of nestedParts) {
        const childPath = `${parent.path}/${part}`;
        let child = parent.folders.find((candidate) => candidate.path === childPath);
        if (!child) {
          child = {
            path: childPath,
            label: part,
            summary: "资料子目录",
            availability: folder.availability,
            files: [],
            folders: [],
            fileCount: 0,
          };
          parent.folders.push(child);
        }
        child.fileCount += 1;
        parent = child;
      }
      parent.files.push(file);
    }
    return root;
  });
}

function filterWorkspaceTree(node: WorkspaceTreeFolder, query: string, extension: FileTypeFilter, ancestorMatches = false): WorkspaceTreeFolder | null {
  const normalizedQuery = query.trim().toLocaleLowerCase("zh-CN");
  const folderMatches = !normalizedQuery || `${node.label} ${node.path} ${node.summary}`.toLocaleLowerCase("zh-CN").includes(normalizedQuery);
  const includeDescendants = ancestorMatches || folderMatches;
  const files = node.files.filter((file) => {
    if (extension !== "ALL" && file.extension !== extension) return false;
    if (includeDescendants) return true;
    return `${file.display_label} ${file.display_path} ${file.display_summary} ${file.extension}`.toLocaleLowerCase("zh-CN").includes(normalizedQuery);
  });
  const folders = node.folders
    .map((folder) => filterWorkspaceTree(folder, query, extension, includeDescendants))
    .filter((folder): folder is WorkspaceTreeFolder => folder !== null);
  if (!files.length && !folders.length && !(folderMatches && node.fileCount === 0 && extension === "ALL")) return null;
  return { ...node, files, folders };
}

function uniqueFileRefs(refs: string[]) {
  return Array.from(new Set(refs));
}

function findingReviewRequest(finding: HarnessFinding, index: number, roundNumber: number | null): EvidenceReviewRequest {
  return {
    reviewKey: `finding:${roundNumber ?? "final"}:${index}:${finding.title}`,
    kind: "finding",
    eyebrow: "Agent 发现",
    title: finding.title,
    detail: finding.detail,
    status: "待人工复核",
    roundNumber,
    branchTitle: null,
    fileRefs: uniqueFileRefs([...finding.file_refs, ...finding.evidence_anchors.map((anchor) => anchor.file_ref)]),
    anchors: finding.evidence_anchors,
    serverFact: finding.evidence_anchors.length
      ? `服务端已把 ${finding.evidence_anchors.length} 处原文片段唯一定位到本轮安全预览，并核对文件范围。`
      : "相关 file_ref 已通过本轮允许范围与引用成员关系校验，但旧结果没有精确位置。",
    boundary: "高亮位置由服务端从逐字引用解析，只证明原文位置和引用成员关系；结论是否成立仍由你复核。",
  };
}

function gapReviewRequest(gap: EvidenceGap, index: number, roundNumber: number, branchTitle: string | null): EvidenceReviewRequest {
  return {
    reviewKey: `gap:${roundNumber}:${gap.gap_id}:${index}`,
    kind: "gap",
    eyebrow: "Evidence Gate",
    title: gap.label,
    detail: gap.detail,
    status: "证据不足",
    roundNumber,
    branchTitle,
    fileRefs: uniqueFileRefs(gap.candidate_file_refs),
    anchors: [],
    serverFact: "服务端 Evidence Gate 已保留缺口，并阻止受影响分支在缺少证据时继续提交。",
    boundary: "候选文件只是下一步核对范围；在用户确认或 Agent 完成下一轮前，系统不会把缺口包装成已解决事实。",
  };
}

function branchReviewRequest(branch: LoopBranch, gaps: EvidenceGap[]): EvidenceReviewRequest {
  const gap = gaps.find((candidate) => candidate.branch_id === branch.branch_id);
  if (gap) return gapReviewRequest(gap, gaps.indexOf(gap), branch.round_number, branch.title);
  return {
    reviewKey: `branch:${branch.branch_id}`,
    kind: "gap",
    eyebrow: "待处理分支",
    title: `${branch.title}仍缺少证据`,
    detail: branch.objective,
    status: "等待你决定",
    roundNumber: branch.round_number,
    branchTitle: branch.title,
    fileRefs: uniqueFileRefs(branch.missing_file_refs),
    anchors: [],
    serverFact: "服务端 Snapshot 将该分支标记为 waiting_input，并保留了 missing_file_refs。",
    boundary: "这些文件是分支当前缺少或待核对的引用，不代表问题已经成立。",
  };
}

function proposalReviewRequest(proposal: string, index: number, result: HarnessResult, roundNumber: number | null): EvidenceReviewRequest {
  return {
    reviewKey: `proposal:${roundNumber ?? "final"}:${index}:${proposal}`,
    kind: "proposal",
    eyebrow: "Agent 下一步建议",
    title: `建议 ${index + 1}`,
    detail: proposal,
    status: "尚未逐项验证",
    roundNumber,
    branchTitle: null,
    fileRefs: uniqueFileRefs(result.findings.flatMap((finding) => finding.file_refs)),
    anchors: [],
    serverFact: "该建议来自本轮已读取资料和已形成的发现；只有用户确认后，服务端才会创建新的独立 Run。",
    boundary: "当前协议没有为每条 follow_up 单独绑定引用。下方文件是本轮结果上下文，不应被理解为这条建议的直接证据。",
  };
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

function normalizeEvidenceAnchor(value: unknown): EvidenceAnchor | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const fileRef = asText(raw.file_ref);
  const role = asText(raw.role);
  const locatorKind = asText(raw.locator_kind);
  const start = asNumber(raw.start);
  const end = asNumber(raw.end);
  const label = asText(raw.label);
  const excerpt = asText(raw.excerpt);
  if (
    !fileRef
    || !["expected", "observed", "support", "contradiction", "context"].includes(role)
    || !["text_lines", "table_rows"].includes(locatorKind)
    || start < 1
    || end < start
    || !label
    || !excerpt
  ) return null;
  return {
    file_ref: fileRef,
    role: role as EvidenceRole,
    label,
    locator_kind: locatorKind as EvidenceAnchor["locator_kind"],
    start,
    end,
    excerpt,
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
    const anchors = Array.isArray(finding.evidence_anchors)
      ? finding.evidence_anchors.map(normalizeEvidenceAnchor).filter((anchor): anchor is EvidenceAnchor => anchor !== null)
      : [];
    return title && detail && fileRefs.length ? [{ title, detail, file_refs: fileRefs, evidence_anchors: anchors }] : [];
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
    ? { gap_id: gapId, branch_id: asText(raw.branch_id) || null, label, detail, candidate_file_refs: asStrings(raw.candidate_file_refs) }
    : null;
}

function normalizeBranch(value: unknown): LoopBranch | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const branchId = asText(raw.branch_id);
  const status = asText(raw.status);
  if (!branchId || !["running", "completed", "waiting_input", "stopped", "failed"].includes(status)) return null;
  return {
    branch_id: branchId,
    unit_id: asText(raw.unit_id),
    round_number: asNumber(raw.round_number, 1),
    parent_branch_id: asText(raw.parent_branch_id) || null,
    title: asText(raw.title, "任务分支"),
    objective: asText(raw.objective),
    depends_on: asStrings(raw.depends_on),
    input_file_refs: asStrings(raw.input_file_refs),
    verified_file_refs: asStrings(raw.verified_file_refs),
    missing_file_refs: asStrings(raw.missing_file_refs),
    status: status as LoopBranch["status"],
    requires_human_gate: raw.requires_human_gate === true,
    created_at: asText(raw.created_at),
    updated_at: asText(raw.updated_at),
  };
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
    candidate_branch_ids: asStrings(nextRaw.candidate_branch_ids),
  } : null;
  return {
    round_number: roundNumber,
    status: ["completed", "stopped", "failed"].includes(status) ? status as LoopRound["status"] : "running",
    phase: phase as LoopPhase,
    question: asText(raw.question, "核对本轮允许资料"),
    steer_instruction: asText(raw.steer_instruction) || null,
    input_file_refs: asStrings(raw.input_file_refs),
    branch_ids: asStrings(raw.branch_ids),
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
    checkpoint_recovered: "已从服务端检查点恢复",
    planning_started: "规划模型开始组织任务",
    planning_completed: "规划模型返回工作计划",
    plan_validation_rejected: "候选计划未通过，正在受控重试",
    plan_validation: "服务端校验工作计划",
    ready_to_execute: "工作计划已准备",
    analysis_started: "分析模型开始读取内容",
    analysis_completed: "分析模型返回初步结果",
    analysis_validation_rejected: "原文位置未通过，正在受控重试",
    result_validation: "服务端核对引用与原文位置",
    round_started: "新一轮开始",
    evidence_gate: "证据门决定下一步",
    control_pause_recorded: "暂停请求已记录",
    control_paused: "已在安全点暂停",
    control_resume_recorded: "已恢复继续运行",
    control_steer_recorded: "方向指令已记录",
    control_steer_applied: "方向指令已应用",
    control_stop_recorded: "停止请求已记录",
    loop_committed: "只读任务简报已提交",
    artifact_version_restored: "已恢复历史成果版本",
    loop_budget_stopped: "已在预算边界停止",
    loop_stopped: "已按你的要求停止",
    harness_failed: "本轮已安全停止",
  };
  const tone = event.event_name === "harness_failed" || event.event_name === "plan_validation_rejected" || event.event_name === "analysis_validation_rejected" || event.event_name.includes("stopped") ? "warning"
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

function normalizeArtifactVersion(value: unknown): ArtifactVersion | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  const artifactId = asText(raw.artifact_id);
  if (!artifactId || !["draft", "verified", "committed"].includes(status)) return null;
  const findings = Array.isArray(raw.findings) ? raw.findings.flatMap((item): HarnessFinding[] => {
    if (!item || typeof item !== "object") return [];
    const finding = item as Record<string, unknown>;
    const title = asText(finding.title); const detail = asText(finding.detail); const refs = asStrings(finding.file_refs);
    const anchors = Array.isArray(finding.evidence_anchors)
      ? finding.evidence_anchors.map(normalizeEvidenceAnchor).filter((anchor): anchor is EvidenceAnchor => anchor !== null)
      : [];
    return title && detail && refs.length ? [{ title, detail, file_refs: refs, evidence_anchors: anchors }] : [];
  }) : [];
  return {
    artifact_id: artifactId,
    version: asNumber(raw.version, 1),
    title: asText(raw.title, "任务证据简报"),
    kind: "evidence_brief",
    status: status as ArtifactVersion["status"],
    round_number: asNumber(raw.round_number, asNumber(raw.version, 1)),
    summary: asText(raw.summary),
    findings,
    follow_ups: asStrings(raw.follow_ups),
    evidence_gaps: Array.isArray(raw.evidence_gaps)
      ? raw.evidence_gaps.map(normalizeGap).filter((item): item is EvidenceGap => item !== null)
      : [],
    source_file_refs: asStrings(raw.source_file_refs),
    finding_count: asNumber(raw.finding_count),
    parent_version: typeof raw.parent_version === "number" ? raw.parent_version : null,
    created_at: asText(raw.created_at),
    review_required: true,
    external_action: "none",
  };
}

function normalizeCommit(value: unknown): LoopCommit | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const commitId = asText(raw.commit_id);
  const artifactId = asText(raw.artifact_id);
  if (!commitId || !artifactId) return null;
  return {
    commit_id: commitId,
    artifact_id: artifactId,
    artifact_version: asNumber(raw.artifact_version, 1),
    operation: asText(raw.operation) === "rollback" ? "rollback" : "commit",
    parent_commit_id: asText(raw.parent_commit_id) || null,
    summary: asText(raw.summary),
    committed_at: asText(raw.committed_at),
    external_action: "none",
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
  const artifactVersions = Array.isArray(raw.artifact_versions)
    ? raw.artifact_versions.map(normalizeArtifactVersion).filter((item): item is ArtifactVersion => item !== null)
    : [];
  const branches = Array.isArray(raw.branches)
    ? raw.branches.map(normalizeBranch).filter((item): item is LoopBranch => item !== null)
    : [];
  const commits = Array.isArray(raw.commits)
    ? raw.commits.map(normalizeCommit).filter((item): item is LoopCommit => item !== null)
    : [];
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
    branches,
    active_branch_id: asText(raw.active_branch_id) || null,
    artifact_versions: artifactVersions,
    commits,
    last_commit: normalizeCommit(raw.last_commit),
    recovered: serverEvents.some((event) => event.event_name === "checkpoint_recovered"),
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

function branchStatusLabel(status: LoopBranch["status"]) {
  return {
    running: "正在处理",
    completed: "已核对",
    waiting_input: "等你决定",
    stopped: "已停止",
    failed: "未通过",
  }[status];
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

function treeFileCount(node: WorkspaceTreeFolder): number {
  return node.files.length + node.folders.reduce((total, folder) => total + treeFileCount(folder), 0);
}

function WorkspaceTreeNode({
  node,
  depth,
  activeFileRef,
  expandedPaths,
  filterCollapsedPaths,
  forceExpanded,
  onToggle,
  onOpenFile,
}: {
  node: WorkspaceTreeFolder;
  depth: number;
  activeFileRef: string;
  expandedPaths: Set<string>;
  filterCollapsedPaths: Set<string>;
  forceExpanded: boolean;
  onToggle: (path: string) => void;
  onOpenFile: (file: HarnessFile) => void;
}) {
  const expanded = forceExpanded ? !filterCollapsedPaths.has(node.path) : expandedPaths.has(node.path);
  const visibleCount = treeFileCount(node);
  const hasChildren = node.files.length > 0 || node.folders.length > 0;
  return <li className="workspace-tree-folder" role="none">
    <button
      type="button"
      className="workspace-tree-folder-row"
      role="treeitem"
      aria-level={depth + 1}
      aria-expanded={expanded}
      aria-label={`${expanded ? "收起" : "展开"}文件夹 ${node.path}`}
      onClick={() => onToggle(node.path)}
      style={{ paddingLeft: `${10 + depth * 17}px` }}
    >
      <IconChevronRight className={expanded ? "is-open" : ""} aria-hidden="true" />
      {expanded ? <IconFolderOpen aria-hidden="true" /> : <IconFolder aria-hidden="true" />}
      <span>{node.label}</span>
      <b>{visibleCount}</b>
    </button>
    {expanded && <ul role="group">
      {node.folders.map((folder) => <WorkspaceTreeNode
        key={folder.path}
        node={folder}
        depth={depth + 1}
        activeFileRef={activeFileRef}
        expandedPaths={expandedPaths}
        filterCollapsedPaths={filterCollapsedPaths}
        forceExpanded={forceExpanded}
        onToggle={onToggle}
        onOpenFile={onOpenFile}
      />)}
      {node.files.map((file) => <li key={file.file_ref} role="none">
        <button
          type="button"
          className={`workspace-tree-file${file.file_ref === activeFileRef ? " is-open" : ""}`}
          role="treeitem"
          aria-level={depth + 2}
          aria-label={`打开 ${file.display_path}`}
          title={file.display_path}
          onClick={() => onOpenFile(file)}
          style={{ paddingLeft: `${31 + depth * 17}px` }}
        >
          <IconFile aria-hidden="true" />
          <span>{file.display_label}</span>
          <b>{file.extension}</b>
        </button>
      </li>)}
      {!hasChildren && <li className="workspace-tree-empty">{node.availability === "task_only_requires_external_system" ? "公开仓库未提供本地输入" : "空目录"}</li>}
    </ul>}
  </li>;
}

const EVIDENCE_ROLE_LABELS: Record<EvidenceRole, string> = {
  expected: "设计预期",
  observed: "实际观测",
  support: "支持证据",
  contradiction: "矛盾证据",
  context: "相关上下文",
};

function evidenceLocationLabel(anchor: EvidenceAnchor, file: HarnessFile | undefined) {
  const range = anchor.start === anchor.end ? `${anchor.start}` : `${anchor.start}-${anchor.end}`;
  if (anchor.locator_kind === "table_rows") return `数据第 ${range} 行`;
  if (file?.preview_kind === "text") return `第 ${range} 行`;
  return `安全预览第 ${range} 行`;
}

function EvidenceReviewDialog({
  request,
  files,
  onClose,
  onOpenFile,
}: {
  request: EvidenceReviewRequest;
  files: HarnessFile[];
  onClose: () => void;
  onOpenFile: (file: HarnessFile) => void;
}) {
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const reviewFiles = useMemo(() => request.fileRefs
    .map((ref) => files.find((file) => file.file_ref === ref))
    .filter((file): file is HarnessFile => file !== undefined), [files, request.fileRefs]);
  const reviewAnchors = useMemo(() => request.anchors.filter((anchor) => files.some((file) => file.file_ref === anchor.file_ref)), [files, request.anchors]);
  const [activeAnchorIndex, setActiveAnchorIndex] = useState(reviewAnchors.length ? 0 : -1);
  const [selectedFileRef, setSelectedFileRef] = useState(reviewAnchors[0]?.file_ref ?? reviewFiles[0]?.file_ref ?? "");
  const [preview, setPreview] = useState<HarnessPreview | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const selectedFile = reviewFiles.find((file) => file.file_ref === selectedFileRef) ?? null;
  const activeAnchor = activeAnchorIndex >= 0 && reviewAnchors[activeAnchorIndex]?.file_ref === selectedFileRef
    ? reviewAnchors[activeAnchorIndex]
    : null;

  useEffect(() => {
    setActiveAnchorIndex(reviewAnchors.length ? 0 : -1);
    setSelectedFileRef(reviewAnchors[0]?.file_ref ?? reviewFiles[0]?.file_ref ?? "");
    closeButtonRef.current?.focus();
  }, [request.reviewKey, reviewAnchors, reviewFiles]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!selectedFileRef) { setPreview(null); setPreviewError(""); return; }
    let current = true;
    setPreviewLoading(true); setPreviewError("");
    void fetch(`${API_BASE}/v1/harness/workspace/files/${encodeURIComponent(selectedFileRef)}`, { headers: HEADERS })
      .then(async (response) => {
        if (!response.ok) throw new Error(response.status === 503 ? "文件完整性校验未通过" : "文件预览暂时不可用");
        const normalized = normalizePreview(await response.json());
        if (!normalized) throw new Error("文件预览格式无效");
        if (current) setPreview(normalized);
      })
      .catch((caught) => {
        if (current) { setPreview(null); setPreviewError(caught instanceof Error ? caught.message : "文件预览暂时不可用"); }
      })
      .finally(() => { if (current) setPreviewLoading(false); });
    return () => { current = false; };
  }, [selectedFileRef]);

  const tone = request.kind === "gap" ? "warning" : request.kind === "proposal" ? "proposal" : "finding";
  const selectAnchor = (index: number) => {
    const anchor = reviewAnchors[index];
    if (!anchor) return;
    setActiveAnchorIndex(index);
    setSelectedFileRef(anchor.file_ref);
  };
  const selectFile = (fileRef: string) => {
    setSelectedFileRef(fileRef);
    setActiveAnchorIndex(reviewAnchors.findIndex((anchor) => anchor.file_ref === fileRef));
  };
  return <div className="evidence-review-backdrop" role="presentation">
    <section className={`evidence-review-page is-${tone}`} role="dialog" aria-modal="true" aria-labelledby="evidence-review-title">
      <header className="evidence-review-header">
        <div><IconGitCommit aria-hidden="true" /><div><span>问题审查页</span><h2 id="evidence-review-title">{request.title}</h2></div></div>
        <button ref={closeButtonRef} type="button" className="icon-action" onClick={onClose} aria-label="关闭问题审查页" title="关闭"><IconX aria-hidden="true" /></button>
      </header>
      <div className="evidence-review-layout">
        <aside className="evidence-review-history" aria-label="审查记录">
          <header><span>{request.eyebrow}</span><b className={`is-${tone}`}>{request.status}</b></header>
          <dl>
            {request.roundNumber !== null && <><dt>发生位置</dt><dd>第 {request.roundNumber} 轮{request.branchTitle ? ` / ${request.branchTitle}` : ""}</dd></>}
            <dt>关联资料</dt><dd>{reviewFiles.length} 份</dd>
          </dl>
          <ol>
            <li><span><IconGitCommit aria-hidden="true" /></span><div><b>Agent 提出</b><p>{request.kind === "proposal" ? "形成一条待确认的下一步建议" : request.kind === "gap" ? "发现证据缺口并停止受影响分支" : "形成一条待复核发现"}</p></div></li>
            <li><span><IconShieldCheck aria-hidden="true" /></span><div><b>服务端记录</b><p>{request.serverFact}</p></div></li>
            <li className="is-current"><span><IconEye aria-hidden="true" /></span><div><b>等待你核对</b><p>对照右侧原始资料，判断 Agent 描述是否成立。</p></div></li>
          </ol>
          <footer><IconAlertTriangle aria-hidden="true" /><p>{request.boundary}</p></footer>
        </aside>
        <main className="evidence-review-main">
          <section className="evidence-review-claim">
            <span>Agent 判断</span>
            <h3>{request.title}</h3>
            <p>{request.detail}</p>
          </section>
          {reviewAnchors.length > 0 ? <section className="evidence-review-pinpoint" aria-labelledby="evidence-pinpoint-title">
            <header><div><span>证据定位</span><h3 id="evidence-pinpoint-title">点一处，原文立即跳到对应行</h3></div><b>{reviewAnchors.length} 处已定位</b></header>
            <div className="evidence-anchor-map">
              {reviewAnchors.map((anchor, index) => {
                const file = files.find((item) => item.file_ref === anchor.file_ref);
                return <button
                  type="button"
                  key={`${anchor.file_ref}:${anchor.locator_kind}:${anchor.start}:${anchor.end}:${index}`}
                  className={`evidence-anchor-item is-${anchor.role}${index === activeAnchorIndex ? " is-active" : ""}`}
                  onClick={() => selectAnchor(index)}
                  aria-label={`定位证据 ${index + 1}：${anchor.label}`}
                >
                  <b>{index + 1}</b>
                  <span><small>{EVIDENCE_ROLE_LABELS[anchor.role]}</small><strong>{anchor.label}</strong><em>{file?.display_label ?? "允许范围内文件"} · {evidenceLocationLabel(anchor, file)}</em><q>{anchor.excerpt}</q></span>
                </button>;
              })}
              <div className="evidence-anchor-conclusion"><IconArrowRight aria-hidden="true" /><span>Agent 据此提出上方判断，等待你确认语义是否成立</span></div>
            </div>
          </section> : <div className="evidence-review-unlocated"><IconAlertTriangle aria-hidden="true" /><p><b>当前只能定位到文件</b><span>{request.kind === "finding" ? "这是旧结果或服务端未找到唯一原文片段，系统不会伪造高亮。" : "该记录没有逐段证据锚点，请按关联文件或下一轮候选范围核对。"}</span></p></div>}
          <section className="evidence-review-source" aria-label="相关资料">
            <header><div><span>相关资料</span><h3>{reviewAnchors.length ? "已标出具体位置，也可切换查看整份文件" : "点击文件，直接对照实际内容"}</h3></div><b>{reviewFiles.length} 份</b></header>
            {reviewFiles.length > 0 ? <div className="evidence-review-files">{reviewFiles.map((file) => { const anchorCount = reviewAnchors.filter((anchor) => anchor.file_ref === file.file_ref).length; return <button type="button" key={file.file_ref} className={file.file_ref === selectedFileRef ? "is-active" : ""} onClick={() => selectFile(file.file_ref)}><IconFile aria-hidden="true" /><span><b>{file.display_label}</b><small>{file.display_path}{anchorCount ? ` · ${anchorCount} 处定位` : ""}</small></span></button>; })}</div> : <p className="evidence-review-no-source">当前服务端事实没有提供可打开的关联文件。系统不会用静态示例补齐。</p>}
          </section>
          <section className="evidence-review-preview" aria-label="资料原文预览">
            <FilePreview preview={preview} file={selectedFile} loading={previewLoading} error={previewError} anchor={activeAnchor} />
            {selectedFile && <button type="button" className="evidence-review-open-workspace" onClick={() => { onClose(); onOpenFile(selectedFile); }}><IconArrowRight aria-hidden="true" />回到资料库中打开</button>}
          </section>
        </main>
      </div>
    </section>
  </div>;
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
  const [expandedFolderPaths, setExpandedFolderPaths] = useState<Set<string>>(() => new Set());
  const [filterCollapsedPaths, setFilterCollapsedPaths] = useState<Set<string>>(() => new Set());
  const [reviewRequest, setReviewRequest] = useState<EvidenceReviewRequest | null>(null);
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
  const restoreAttemptedRef = useRef(false);

  const allFiles = useMemo(() => workspace?.folders.flatMap((folder) => folder.files) ?? [], [workspace]);
  const activeFile = allFiles.find((file) => file.file_ref === activeFileRef) ?? null;
  const availableFileTypes = useMemo(() => {
    return Array.from(new Set(allFiles.map((file) => file.extension))).sort((left, right) => left.localeCompare(right));
  }, [allFiles]);
  const workspaceTree = useMemo(() => workspace ? buildWorkspaceTree(workspace) : [], [workspace]);
  const filteredWorkspaceTree = useMemo(() => workspaceTree
    .map((folder) => filterWorkspaceTree(folder, fileSearch, fileTypeFilter))
    .filter((folder): folder is WorkspaceTreeFolder => folder !== null), [workspaceTree, fileSearch, fileTypeFilter]);
  const visibleFileCount = useMemo(() => filteredWorkspaceTree.reduce((total, folder) => total + treeFileCount(folder), 0), [filteredWorkspaceTree]);
  const forceTreeExpanded = Boolean(fileSearch.trim() || fileTypeFilter !== "ALL");

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
    window.sessionStorage.setItem(RUN_SESSION_KEY, snapshot.run_id);
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
      if (firstFile) setExpandedFolderPaths((current) => current.size ? current : new Set(fileAncestorPaths(firstFile)));
    } catch (caught) {
      if (requestId !== requestRef.current) return;
      const message = caught instanceof Error ? caught.message : "办公资料库暂时无法读取";
      setWorkspace(null); setWorkspaceStatus("unavailable"); setWorkspaceError(message); setConnection("offline");
    }
  }

  async function restoreLatestRun() {
    if (restoreAttemptedRef.current) return;
    restoreAttemptedRef.current = true;
    try {
      let snapshot: HarnessRun | null = null;
      const storedRunId = window.sessionStorage.getItem(RUN_SESSION_KEY);
      if (storedRunId) {
        const response = await fetch(`${API_BASE}/v1/harness/runs/${encodeURIComponent(storedRunId)}`, { headers: HEADERS });
        if (response.ok) snapshot = normalizeRun(await response.json());
        else if (response.status === 404) window.sessionStorage.removeItem(RUN_SESSION_KEY);
      }
      if (!snapshot) {
        const response = await fetch(`${API_BASE}/v1/harness/runs?limit=10`, { headers: HEADERS });
        if (response.ok) {
          const payload = await response.json() as { runs?: unknown[] };
          const candidates = Array.isArray(payload.runs)
            ? payload.runs.map(normalizeRun).filter((item): item is HarnessRun => item !== null)
            : [];
          snapshot = candidates.find((item) => !TERMINAL_STATUSES.has(item.status)) ?? null;
        }
      }
      if (!snapshot) return;
      const generation = generationRef.current + 1;
      generationRef.current = generation;
      runRef.current = null;
      lastSequenceRef.current = 0;
      if (!applySnapshot(snapshot, generation)) return;
      setInstruction(snapshot.instruction);
      setView(snapshot.result && TERMINAL_STATUSES.has(snapshot.status) ? "result" : "loop");
      if (!TERMINAL_STATUSES.has(snapshot.status)) {
        connectEvents(snapshot.run_id, generation, snapshot.last_event_sequence);
      }
    } catch {
      setConnection("available");
    }
  }

  useEffect(() => { void loadWorkspace(); return closeTransport; }, []);

  useEffect(() => { setFilterCollapsedPaths(new Set()); }, [fileSearch, fileTypeFilter]);

  useEffect(() => {
    if (workspaceStatus === "online") void restoreLatestRun();
  }, [workspaceStatus]);

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
    setExpandedFolderPaths((current) => {
      const next = new Set(current);
      for (const path of fileAncestorPaths(file)) next.add(path);
      return next;
    });
    setActiveFileRef(file.file_ref); setView("data");
  }

  function toggleFolder(path: string) {
    if (forceTreeExpanded) {
      setFilterCollapsedPaths((current) => {
        const next = new Set(current);
        if (next.has(path)) next.delete(path);
        else next.add(path);
        return next;
      });
      return;
    }
    setExpandedFolderPaths((current) => {
      const next = new Set(current);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
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

  async function controlLoop(command: LoopCommand, options: LoopControlOptions = {}) {
    const current = runRef.current;
    if (!current || (TERMINAL_STATUSES.has(current.status) && command !== "rollback")) return false;
    const normalizedInstruction = options.instruction?.trim() || undefined;
    const signature = JSON.stringify({ command, instruction: normalizedInstruction, branchId: options.branchId, artifactVersion: options.artifactVersion, runId: current.run_id });
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
          branch_id: options.branchId,
          artifact_version: options.artifactVersion,
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
          <div><IconDatabase aria-hidden="true" /><div><strong>文件目录</strong><span>办公资料库 / {workspace.folder_count} 个目录</span></div></div>
          <label><IconSearch aria-hidden="true" /><input value={fileSearch} onChange={(event) => setFileSearch(event.target.value)} placeholder="搜索文件或目录" aria-label="搜索文件或目录" /></label>
          <nav className="file-type-filters" aria-label="按文件类型筛选">
            {["ALL", ...availableFileTypes].map((extension) => <button type="button" key={extension} className={fileTypeFilter === extension ? "is-active" : ""} onClick={() => setFileTypeFilter(extension)}>{extension === "ALL" ? "全部" : extension}</button>)}
          </nav>
        </header>
        <div className="file-manager-columns" aria-hidden="true"><span>目录 / 文件</span><span>{forceTreeExpanded ? `${visibleFileCount} 个结果` : `${workspace.file_count} 份文件`}</span></div>
        {filteredWorkspaceTree.length ? <ul className="workspace-tree" role="tree" aria-label="办公资料库目录树">
          {filteredWorkspaceTree.map((folder) => <WorkspaceTreeNode
            key={folder.path}
            node={folder}
            depth={0}
            activeFileRef={activeFileRef}
            expandedPaths={expandedFolderPaths}
            filterCollapsedPaths={filterCollapsedPaths}
            forceExpanded={forceTreeExpanded}
            onToggle={toggleFolder}
            onOpenFile={openFile}
          />)}
        </ul> : <p className="dataset-unavailable">没有符合当前筛选条件的文件或目录。</p>}
      </aside>
      <section className="data-task-surface">
        <section className="task-composer" aria-labelledby="task-composer-title">
          <div><span>研究整个资料库</span><h2 id="task-composer-title">你想让 Agent 找什么，或推进什么？</h2></div>
          {run?.recovered && <div className="checkpoint-restored"><IconRefresh aria-hidden="true" /><span><b>服务端检查点已恢复</b> 未完成的模型调用没有重放，你可以检查轨迹后继续。</span></div>}
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
          {view === "loop" && <LoopView run={run} files={allFiles} controlBusy={controlBusy} onControl={controlLoop} onReview={setReviewRequest} />}
          {view === "result" && <ResultView result={run?.result ?? null} artifacts={run?.artifact_versions ?? []} commit={run?.last_commit ?? null} files={allFiles} onOpenFile={openFile} onReview={setReviewRequest} onStartTask={startTask} starting={starting} />}
        </div>
        <details className="workspace-boundary"><summary><IconShieldCheck aria-hidden="true" />数据与执行边界</summary><p>{workspace.data_boundary} Agent 可以检索整个资料库，但每轮只读取服务端校验通过且受预算约束的文件；本轮不会修改原文件或执行外部动作。</p></details>
        {error && <div className="workspace-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{error}</span></div>}
      </section>
    </div>
    {reviewRequest && <EvidenceReviewDialog request={reviewRequest} files={allFiles} onClose={() => setReviewRequest(null)} onOpenFile={openFile} />}
  </main>;
}

function FilePreview({ preview, file, loading, error, anchor = null }: { preview: HarnessPreview | null; file: HarnessFile | null; loading: boolean; error: string; anchor?: EvidenceAnchor | null }) {
  const focusNodeRef = useRef<HTMLElement | null>(null);
  useEffect(() => {
    if (!anchor || !preview || anchor.file_ref !== preview.file_ref) return;
    const frame = window.requestAnimationFrame(() => {
      const node = focusNodeRef.current;
      const container = node?.closest<HTMLElement>(".table-preview, .document-preview");
      if (!node || !container) return;
      const nodeBox = node.getBoundingClientRect();
      const containerBox = container.getBoundingClientRect();
      container.scrollTop += nodeBox.top - containerBox.top - (container.clientHeight - nodeBox.height) / 2;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [anchor, preview]);
  if (!file) return <div className="file-preview-empty"><IconFile aria-hidden="true" /><h2>从文件列表打开一份资料</h2><p>浏览文件不会限制 Agent 的检索范围；任务启动后由 Agent 自己选择相关证据。</p></div>;
  if (loading) return <div className="file-preview-empty"><IconLoader2 aria-hidden="true" /><h2>正在安全读取</h2><p>服务端正在核对完整性并生成只读预览。</p></div>;
  if (error || !preview) return <div className="file-preview-empty is-error"><IconAlertTriangle aria-hidden="true" /><h2>文件预览不可用</h2><p>{error || "没有收到可用的预览。"}</p></div>;
  const activeAnchor = anchor?.file_ref === preview.file_ref ? anchor : null;
  const textLines = (preview.text || "此文件没有可提取的文本层。").split("\n");
  return <article className="file-preview">
    <header><div><span>办公资料库</span><h2>{preview.display_label}</h2><p>{preview.display_path}</p></div><div className="file-meta"><b>{file.extension}</b><span>{formatSize(preview.size)}</span>{preview.page_count !== null && <span>{preview.page_count} 页</span>}{preview.total_rows !== null && <span>{preview.total_rows} 行</span>}</div></header>
    {activeAnchor && <div className="evidence-preview-locator" role="status"><IconEye aria-hidden="true" /><span><b>正在核对：{activeAnchor.label}</b><small>{evidenceLocationLabel(activeAnchor, file)} · 服务端已匹配原文</small></span></div>}
    {preview.kind === "table" ? <div className="table-preview"><table><thead><tr><th className="row-number">#</th>{preview.columns.map((column, index) => <th key={`${column}:${index}`}>{column || `列 ${index + 1}`}</th>)}</tr></thead><tbody>{preview.rows.map((row) => { const focused = activeAnchor?.locator_kind === "table_rows" && row.row_number >= activeAnchor.start && row.row_number <= activeAnchor.end; return <tr key={row.row_number} className={focused ? "is-evidence-focus" : ""} data-evidence-focus={focused ? "true" : undefined} ref={focused && row.row_number === activeAnchor?.start ? (node) => { focusNodeRef.current = node; } : undefined}><td className="row-number">{row.row_number}</td>{preview.columns.map((_, index) => <td key={index}>{row.values[index] ?? ""}</td>)}</tr>; })}</tbody></table></div> : activeAnchor?.locator_kind === "text_lines" ? <div className="document-preview is-annotated" role="document">{textLines.map((line, index) => { const lineNumber = index + 1; const focused = lineNumber >= activeAnchor.start && lineNumber <= activeAnchor.end; return <div key={lineNumber} className={`document-line${focused ? " is-evidence-focus" : ""}`} data-evidence-focus={focused ? "true" : undefined} ref={focused && lineNumber === activeAnchor.start ? (node) => { focusNodeRef.current = node; } : undefined}><span>{lineNumber}</span><code>{line || " "}</code>{focused && lineNumber === activeAnchor.start && <b>{EVIDENCE_ROLE_LABELS[activeAnchor.role]}</b>}</div>; })}</div> : <pre className="document-preview">{preview.text || "此文件没有可提取的文本层。"}</pre>}
    <footer className="preview-security"><IconShieldCheck aria-hidden="true" /><div><strong>安全预览</strong><span>{preview.security.notes.join(" · ")}</span>{preview.truncated && <span>当前仅显示部分内容</span>}</div></footer>
  </article>;
}

function LoopView({
  run,
  files,
  controlBusy,
  onControl,
  onReview,
}: {
  run: HarnessRun | null;
  files: HarnessFile[];
  controlBusy: LoopCommand | null;
  onControl: (command: LoopCommand, options?: LoopControlOptions) => Promise<boolean>;
  onReview: (request: EvidenceReviewRequest) => void;
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
  const waitingForBranch = run.status === "waiting_input";
  const canPause = !terminal && run.control_state === "running";
  const canSteer = !terminal && ![ "stop_requested", "stopped" ].includes(run.control_state);
  const fileLabel = (fileRef: string) => files.find((file) => file.file_ref === fileRef)?.display_label ?? "允许范围内的文件";
  const roundBranches = selectedRound ? run.branches.filter((branch) => selectedRound.branch_ids.includes(branch.branch_id)) : [];
  const currentArtifactVersion = run.last_commit?.artifact_version ?? null;

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
        <button type="button" onClick={() => void onControl(canResume ? "resume" : "pause")} disabled={controlBusy !== null || terminal || waitingForBranch || (!canResume && !canPause)}>
          {canResume ? <IconPlayerPlay aria-hidden="true" /> : <IconPlayerPause aria-hidden="true" />}
          {waitingForBranch ? "请选择待处理分支" : controlBusy === "pause" || controlBusy === "resume" ? "正在提交" : canResume ? "继续" : "暂停"}
        </button>
        <button type="button" className="is-stop" onClick={() => void onControl("stop")} disabled={controlBusy !== null || terminal}><IconPlayerStop aria-hidden="true" />结束并保留现有结果</button>
      </div>
      <form onSubmit={async (event) => {
        event.preventDefault();
        if (!steerDraft.trim()) return;
        if (await onControl("steer", { instruction: steerDraft })) setSteerDraft("");
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
      {roundBranches.length > 0 && <section className="loop-branches" aria-label={`第 ${selectedRound.round_number} 轮任务分支`}>
        <header><div><span>任务分支现场</span><h3>{roundBranches.length} 条分支，分别保留证据状态</h3></div><b>{roundBranches.filter((branch) => branch.status === "completed").length}/{roundBranches.length} 已核对</b></header>
        <ol>{roundBranches.map((branch, index) => <li key={branch.branch_id} className={`is-${branch.status}${run.active_branch_id === branch.branch_id ? " is-selected" : ""}`}>
          <span>{branch.status === "completed" ? <IconCheck aria-hidden="true" /> : index + 1}</span>
          <div><header><b>{branch.title}</b><small>{branchStatusLabel(branch.status)}</small></header><p>{branch.objective}</p><footer><span>{branch.input_file_refs.length} 份资料</span>{branch.depends_on.length > 0 && <span>{branch.depends_on.length} 条前序依赖</span>}{branch.parent_branch_id && <span>续自上一轮</span>}{branch.missing_file_refs.length > 0 && <strong>缺 {branch.missing_file_refs.length} 份引用</strong>}</footer></div>
          {branch.status === "waiting_input" && waitingForBranch && <div className="loop-branch-actions"><button type="button" className="is-review" onClick={() => onReview(branchReviewRequest(branch, selectedRound.evidence_gaps))}><IconEye aria-hidden="true" />查看问题</button><button type="button" onClick={() => void onControl("resume", { branchId: branch.branch_id })} disabled={!canResume || controlBusy !== null}><IconPlayerPlay aria-hidden="true" />{controlBusy === "resume" ? "正在启动" : "继续此分支"}</button></div>}
        </li>)}</ol>
      </section>}
      {selectedRound.result && <section className="loop-round-result"><span>本轮核对结果</span><h3>{selectedRound.result.summary}</h3><p>{selectedRound.result.findings.length} 条发现，引用 {selectedRound.verified_file_refs.length} 份文件。</p>{selectedRound.result.findings.length > 0 && <div className="loop-review-links">{selectedRound.result.findings.map((finding, index) => <button type="button" key={`${finding.title}:${index}`} onClick={() => onReview(findingReviewRequest(finding, index, selectedRound.round_number))}><IconEye aria-hidden="true" />核对：{finding.title}</button>)}</div>}</section>}
      {selectedRound.evidence_gaps.length > 0 && <section className="loop-gap"><IconAlertTriangle aria-hidden="true" /><div><span>证据缺口</span><h3>{selectedRound.evidence_gaps.length} 条分支尚未完成</h3><p>点击缺口即可查看具体描述、候选文件和原始内容；只有你确认的分支会进入下一轮。</p><div className="loop-review-links">{selectedRound.evidence_gaps.map((gap, index) => {
        const branchTitle = roundBranches.find((branch) => branch.branch_id === gap.branch_id)?.title ?? null;
        return <button type="button" key={gap.gap_id} onClick={() => onReview(gapReviewRequest(gap, index, selectedRound.round_number, branchTitle))}><IconEye aria-hidden="true" />{gap.label}</button>;
      })}</div></div></section>}
      {selectedRound.next_step && <footer className={selectedRound.next_step.decision === "completed" ? "is-complete" : "is-next"}><div><span>服务端决定</span><strong>{gateLabel(selectedRound.next_step.decision)}</strong><p>{selectedRound.next_step.reason}</p></div>{selectedRound.next_step.decision === "waiting_input" ? <b>选择上方分支继续</b> : selectedRound.next_step.decision === "next_round" ? <IconArrowRight aria-hidden="true" /> : null}</footer>}
    </article>}
    {run.artifact_versions.length > 0 && <section className="artifact-evolution" aria-label="成果版本">
      <header><div><span>不可变成果历史</span><h3>每轮形成一个可追溯版本</h3></div><b>{currentArtifactVersion ? `当前 v${currentArtifactVersion}` : "尚未提交"}</b></header>
      <ol>{run.artifact_versions.map((artifact) => <li key={`${artifact.artifact_id}:${artifact.version}`} className={currentArtifactVersion === artifact.version ? "is-current" : ""}><span>v{artifact.version}</span><div><b>{currentArtifactVersion === artifact.version ? "当前版本" : artifact.status === "verified" ? "已核对" : "阶段草稿"}</b><p>第 {artifact.round_number} 轮 · {artifact.finding_count} 条发现 · {artifact.source_file_refs.length} 份引用</p></div>{terminal && currentArtifactVersion !== artifact.version && <button type="button" title={`恢复为成果版本 v${artifact.version}`} onClick={() => void onControl("rollback", { artifactVersion: artifact.version })} disabled={controlBusy !== null}><IconRefresh aria-hidden="true" />{controlBusy === "rollback" ? "恢复中" : "恢复"}</button>}</li>)}</ol>
      {run.last_commit && <footer><IconCircleCheck aria-hidden="true" /><span>{run.last_commit.summary}</span><b>{run.commits.length} 次提交记录</b></footer>}
    </section>}
    {run.brief && <section className={`loop-brief is-${run.brief.outcome}`}><IconCircleCheck aria-hidden="true" /><div><span>任务简报</span><h3>{run.brief.summary}</h3><p>外部动作：未发生 · 结果仍需人工复核</p></div></section>}
  </section>;
}
function ResultView({
  result,
  artifacts,
  commit,
  files,
  onOpenFile,
  onReview,
  onStartTask,
  starting,
}: {
  result: HarnessResult | null;
  artifacts: ArtifactVersion[];
  commit: LoopCommit | null;
  files: HarnessFile[];
  onOpenFile: (file: HarnessFile) => void;
  onReview: (request: EvidenceReviewRequest) => void;
  onStartTask: (instruction: string) => Promise<void>;
  starting: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!result) return <div className="workspace-placeholder"><IconClock aria-hidden="true" /><h2>任务简报尚未形成</h2><p>Agent Control Loop 完成只读分析并通过文件引用校验后，简报会出现在这里。</p></div>;
  const visibleFindings = expanded ? result.findings : result.findings.slice(0, 3);
  const latestRoundNumber = artifacts.at(-1)?.round_number ?? null;
  return <article className="result-view">
    <header><IconCircleCheck aria-hidden="true" /><div><span>{commit ? `任务证据简报 v${commit.artifact_version} · ${commit.operation === "rollback" ? "已恢复" : "已提交"}` : artifacts.length ? `任务证据简报 v${artifacts.at(-1)?.version} · 待证据门` : "资料库研究结果 · 待复核"}</span><h2>{result.summary}</h2></div></header>
    <div className="result-findings">{visibleFindings.map((finding, index) => {
      const findingArtifact = artifacts.find((artifact) => artifact.findings.some((candidate) => candidate.title === finding.title && candidate.detail === finding.detail));
      return <section key={`${finding.title}:${index}`}>
        <b>{index + 1}</b>
        <div><h3>{finding.title}</h3><p>{finding.detail}</p><footer>
          <button type="button" className="is-review" onClick={() => onReview(findingReviewRequest(finding, index, findingArtifact?.round_number ?? null))}><IconEye aria-hidden="true" />打开审查页</button>
          {finding.file_refs.map((ref) => {
            const file = files.find((item) => item.file_ref === ref);
            return file ? <button type="button" key={ref} onClick={() => onOpenFile(file)}><IconFile aria-hidden="true" />{file.display_label}</button> : null;
          })}
        </footer></div>
      </section>;
    })}</div>
    {result.findings.length > 3 && <button type="button" className="result-expand" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}><IconChevronDown className={expanded ? "is-open" : ""} aria-hidden="true" />{expanded ? "收起详细发现" : `查看其余 ${result.findings.length - 3} 条发现`}</button>}
    {result.follow_ups.length > 0 && <section className="result-proposals" aria-labelledby="result-proposals-title">
      <header><span>Agent 建议的下一步</span><h3 id="result-proposals-title">先看形成依据，再决定是否启动新的 Control Loop</h3></header>
      {result.follow_ups.map((item, index) => <article key={`${item}:${index}`}><div><b>建议 {index + 1}</b><p>{item}</p></div><div className="result-proposal-actions"><button type="button" className="is-review" onClick={() => onReview(proposalReviewRequest(item, index, result, latestRoundNumber))}><IconEye aria-hidden="true" />查看形成依据</button><button type="button" disabled={starting} onClick={() => void onStartTask(item)}><IconPlayerPlay aria-hidden="true" />{starting ? "正在启动" : "确认并启动"}</button></div></article>)}
    </section>}
    <footer><IconShieldCheck aria-hidden="true" />这些建议由模型基于本轮已读取资料生成，尚未逐项验证；只有你点击确认后才会启动新任务，本轮没有修改原文件或执行外部动作。</footer>
  </article>;
}
