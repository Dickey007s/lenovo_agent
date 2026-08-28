"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
  IconDownload,
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
type LoopCommand = "pause" | "resume" | "steer" | "stop" | "rollback" | "decision";
type LoopControlOptions = {
  instruction?: string;
  branchId?: string;
  artifactVersion?: number;
  decisionAction?: "accept" | "decline" | "defer" | "cancel";
  findingId?: string;
  resolutionId?: string;
  selectedOptionId?: FindingDecisionOption["option_id"];
  selectedCandidateId?: string;
  decisionRequestId?: string;
  sourceRevision?: string;
  feedback?: string;
};
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
type EvidenceCandidate = {
  candidate_id: string;
  file_ref: string;
  locator_kind: EvidenceAnchor["locator_kind"];
  start: number;
  end: number;
  excerpt: string;
  source_revision?: string | null;
  context_before?: string | null;
  context_after?: string | null;
};
type DecisionRequest = {
  request_id: string;
  finding_id: string;
  resolution_id: string | null;
  branch_id: string | null;
  source_revision: string | null;
  expected_version: number | null;
  idempotency_ref: string | null;
  candidate_ids: string[];
  consequence: string;
  state: "pending" | "deferred" | "accepted" | "declined" | "cancelled" | "rejected" | null;
};
type EvidenceResolution = {
  resolution_id: string;
  finding_id: string;
  finding_title: string;
  fact_summary: string | null;
  impact: string | null;
  branch_id: string | null;
  file_ref: string;
  role: EvidenceRole;
  label: string;
  query_excerpt: string;
  status: "exact" | "ambiguous" | "unavailable" | "stale" | "rejected";
  reason: string;
  candidates: EvidenceCandidate[];
  selected_candidate_id: string | null;
  source_revision?: string | null;
  decision_request?: DecisionRequest | null;
  decision_status?: "pending" | "deferred" | "accepted" | "declined" | "cancelled" | "rejected" | null;
};
type FindingDecisionOption = {
  option_id: "A" | "B" | "C";
  label: string;
  meaning: string;
  agent_next_step: string;
  next_instruction: string;
  affected_branch_ids: string[];
  required_file_refs: string[];
  estimated_additional_rounds: number;
  external_action: "none";
};
type FindingReview = {
  requires_human_decision: boolean;
  question: string;
  why_human: string;
  options: FindingDecisionOption[];
  recommended_option_id: FindingDecisionOption["option_id"] | null;
  recommendation_reason: string;
  after_confirmation: string;
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
  kind: "finding" | "gap" | "proposal" | "resolution";
  eyebrow: string;
  title: string;
  detail: string;
  factSummary: string | null;
  impact: string | null;
  review: FindingReview | null;
  status: string;
  roundNumber: number | null;
  branchTitle: string | null;
  fileRefs: string[];
  anchors: EvidenceAnchor[];
  findingId: string | null;
  affectedBranchIds: string[];
  resolution: EvidenceResolution | null;
  decisionRecord: DecisionRecord | null;
  decisionRequest: DecisionRequest | null;
  serverFact: string;
  boundary: string;
  gapRecovery: GapRecoveryContext | null;
};

type GapRecoveryContext = {
  cause: "analysis_output" | "source_location" | "evidence_missing";
  branchId: string | null;
  branchTitle: string;
  branchObjective: string;
  attemptedFileRefs: string[];
  verifiedFileRefs: string[];
  analysisCalled: boolean;
  analysisOutputUsed: boolean;
  mode: "resume_branch" | "new_run" | "inspect_only";
  nextInstruction: string;
  newRunInstruction: string;
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
type HarnessFinding = {
  finding_id: string | null;
  affected_branch_ids: string[];
  title: string;
  detail: string;
  fact_summary: string | null;
  impact: string | null;
  file_refs: string[];
  evidence_anchors: EvidenceAnchor[];
  evidence_resolutions: EvidenceResolution[];
  decision_request: DecisionRequest | null;
  review: FindingReview | null;
};
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
  recovery_kind: "source_location" | "analysis_output" | null;
  evidence_resolutions: EvidenceResolution[];
  decision_requests: DecisionRequest[];
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

type ArtifactCheck = {
  check_id: string;
  label: string;
  passed: boolean;
  detail: string;
};

type WorkspaceArtifact = {
  artifact_id: string;
  capability_id: string;
  scenario_id: string;
  title: string;
  file_name: string;
  media_type: "text/csv" | "text/markdown" | "application/zip" | "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  size: number;
  version: number;
  round_number: number;
  source_file_refs: string[];
  validator_id: string;
  verifier_status: "passed" | "failed";
  checks: ArtifactCheck[];
  summary: string;
  covered_period: string | null;
  statistic_basis: string | null;
  purpose: string | null;
  record_count: number | null;
  download_path: string;
  created_at: string;
  original_inputs_modified: false;
  review_required: true;
  external_action: "none";
};

type EffectReceipt = {
  receipt_id: string;
  capability_id: string;
  scenario_id: string;
  status: "passed" | "failed" | "blocked_external_boundary" | "unsupported_local_capability";
  state: string;
  action: string;
  observation: string;
  cost: string;
  result: string;
  source_file_refs: string[];
  artifact_ids: string[];
  prohibited_side_effects: string[];
  created_at: string;
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

type DecisionRecord = {
  decision_id: string;
  action: "accept" | "decline" | "defer" | "cancel";
  finding_id: string;
  resolution_id: string | null;
  branch_id: string | null;
  selected_option_id: FindingDecisionOption["option_id"] | null;
  selected_candidate_id: string | null;
  feedback: string | null;
  idempotency_ref: string | null;
  recorded_at: string;
  accepted_task_version: number;
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
  decision_records: DecisionRecord[];
  decision_requests: DecisionRequest[];
  branches: LoopBranch[];
  active_branch_id: string | null;
  artifact_versions: ArtifactVersion[];
  workspace_artifacts: WorkspaceArtifact[];
  effect_receipts: EffectReceipt[];
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
  eventName: string;
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
  verifiedEffectReady: boolean;
  passedArtifactChecks: number;
  totalArtifactChecks: number;
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
  "analysis_structure_rejected",
  "analysis_validation_rejected",
  "analysis_scope_filtered",
  "decision_gate_suppressed",
  "analysis_partial_adopted",
  "analysis_recovery_required",
  "evidence_disambiguation_required",
  "partial_artifact_saved",
  "decision_requested",
  "decision_recorded",
  "branch_resumed_from_checkpoint",
  "deterministic_office_tool_started",
  "run_workspace_artifact_written",
  "deterministic_verification_completed",
  "scenario_effect_bounded",
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

function normalizeDecisionRequest(value: unknown): DecisionRequest | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const requestId = asText(raw.decision_request_id || raw.request_id);
  const findingId = asText(raw.finding_id);
  if (!requestId || !findingId) return null;
  const expectedVersion = typeof raw.expected_version === "number"
    ? raw.expected_version
    : typeof raw.accepted_task_version === "number" ? raw.accepted_task_version : null;
  const rawCandidateIds = asStrings(raw.candidate_ids);
  const candidateIds = rawCandidateIds.length
    ? rawCandidateIds
    : Array.isArray(raw.candidates)
      ? raw.candidates.flatMap((candidate) => candidate && typeof candidate === "object" ? [asText((candidate as Record<string, unknown>).candidate_id)] : []).filter(Boolean)
      : [];
  return {
    request_id: requestId,
    finding_id: findingId,
    resolution_id: asText(raw.resolution_id) || null,
    branch_id: asText(raw.branch_id) || null,
    source_revision: asText(raw.source_revision || raw.sourceRevision) || null,
    expected_version: expectedVersion,
    idempotency_ref: asText(raw.idempotency_ref) || null,
    candidate_ids: candidateIds,
    consequence: asText(raw.consequence || raw.after_confirmation || raw.next_step, "只重跑受影响分支，不修改源文件，不执行外部动作。"),
    state: normalizeDecisionState(raw.state || raw.decision_status || raw.status),
  };
}

function normalizeDecisionState(value: unknown): DecisionRequest["state"] {
  const state = asText(value).toLowerCase();
  if (state === "open") return "pending";
  if (state === "canceled") return "cancelled";
  return ["pending", "deferred", "accepted", "declined", "cancelled", "rejected"].includes(state)
    ? state as DecisionRequest["state"]
    : null;
}
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

type EvidenceGapGroup = {
  groupKey: string;
  gaps: EvidenceGap[];
  candidateFileRefs: string[];
};

function groupEvidenceGaps(gaps: EvidenceGap[]): EvidenceGapGroup[] {
  const groups = new Map<string, EvidenceGapGroup>();
  for (const gap of gaps) {
    const candidateFileRefs = uniqueFileRefs(gap.candidate_file_refs).sort();
    const normalizedDetail = gap.detail.trim().replace(/\s+/g, " ");
    const groupKey = candidateFileRefs.length > 0
      ? `sources:${candidateFileRefs.join(",")}|detail:${normalizedDetail}`
      : `gap:${gap.gap_id}`;
    const existing = groups.get(groupKey);
    if (existing) existing.gaps.push(gap);
    else groups.set(groupKey, { groupKey, gaps: [gap], candidateFileRefs });
  }
  return [...groups.values()];
}

function uniqueDecisionRequests(requests: DecisionRequest[]) {
  return Array.from(new Map(requests.map((request) => [request.request_id, request])).values());
}

function findingReviewRequest(finding: HarnessFinding, index: number, roundNumber: number | null, decisions: DecisionRecord[] = [], decisionRequests: DecisionRequest[] = []): EvidenceReviewRequest {
  const decisionRecord = [...decisions].reverse().find((item) => item.finding_id === finding.finding_id && item.resolution_id === null) ?? null;
  return {
    reviewKey: `finding:${roundNumber ?? "final"}:${index}:${finding.title}`,
    kind: "finding",
    eyebrow: "Agent 发现",
    title: finding.title,
    detail: finding.detail,
    factSummary: finding.fact_summary,
    impact: finding.impact,
    review: finding.review,
    status: "待人工复核",
    roundNumber,
    branchTitle: null,
    fileRefs: uniqueFileRefs([...finding.file_refs, ...finding.evidence_anchors.map((anchor) => anchor.file_ref)]),
    anchors: finding.evidence_anchors,
    findingId: finding.finding_id,
    affectedBranchIds: finding.affected_branch_ids,
    resolution: null,
    decisionRecord,
    decisionRequest: finding.decision_request ?? decisionRequests.find((item) => item.finding_id === finding.finding_id) ?? null,
    serverFact: finding.evidence_anchors.length
      ? `服务端已把 ${finding.evidence_anchors.length} 处原文片段唯一定位到本轮安全预览，并核对文件范围。`
      : "相关 file_ref 已通过本轮允许范围与引用成员关系校验，但旧结果没有精确位置。",
    boundary: "高亮位置由服务端从逐字引用解析，只证明原文位置和引用成员关系；结论是否成立仍由你复核。",
    gapRecovery: null,
  };
}

function buildGapRecoveryContext(run: HarnessRun, round: LoopRound, branch: LoopBranch | null, gap: EvidenceGap): GapRecoveryContext {
  const cause = round.next_step?.recovery_kind ?? "evidence_missing";
  const branchTitle = branch?.title ?? "当前证据分支";
  const branchObjective = branch?.objective ?? gap.detail;
  const attemptedFileRefs = uniqueFileRefs(branch?.input_file_refs.length ? branch.input_file_refs : gap.candidate_file_refs);
  const verifiedFileRefs = uniqueFileRefs(branch?.verified_file_refs ?? []);
  const terminal = TERMINAL_STATUSES.has(run.status);
  const mode = terminal
    ? "new_run"
    : run.status === "waiting_input" && branch?.status === "waiting_input"
      ? "resume_branch"
      : "inspect_only";
  const nextInstruction = cause === "analysis_output"
    ? `只重试“${branchTitle}”分支。重新读取相关文件，把结果整理为可校验的事实、影响和逐字引用；若仍无法形成结构，请明确缺少的字段、版本或记录。`
    : cause === "source_location"
      ? `只重试“${branchTitle}”分支。为每条候选结论寻找更长、唯一且可逐字匹配的原文；若找不到，保留缺口并说明缺少什么。`
      : `只重试“${branchTitle}”分支，围绕“${branchObjective}”补齐可唯一定位的原文证据。`;
  const newRunInstruction = [
    run.instruction,
    `续办分支：${branchTitle}`,
    `本次只聚焦“${branchObjective}”。请从整个资料库自主重新检索所需证据，不受上次候选文件限制。`,
    nextInstruction,
    "边界：只读分析，不修改原文件，不执行外部动作。",
  ].join("\n");
  return {
    cause,
    branchId: branch?.branch_id ?? gap.branch_id,
    branchTitle,
    branchObjective,
    attemptedFileRefs,
    verifiedFileRefs,
    analysisCalled: Boolean(round.analysis_receipt?.called),
    analysisOutputUsed: Boolean(round.analysis_receipt?.output_used),
    mode,
    nextInstruction,
    newRunInstruction,
  };
}

function gapReviewRequest(gap: EvidenceGap, index: number, round: LoopRound, branch: LoopBranch | null, run: HarnessRun): EvidenceReviewRequest {
  const recovery = buildGapRecoveryContext(run, round, branch, gap);
  const factSummary = recovery.cause === "analysis_output"
    ? "Agent 已读取候选文件并调用分析模型，但返回内容没有通过结构校验，因此没有形成可核对结论。"
    : recovery.cause === "source_location"
      ? "Agent 已形成候选内容，但服务端无法把候选原文唯一定位到文件中的具体位置。"
      : "Agent 尚未为这个分支形成通过服务端校验的逐字引用。";
  return {
    reviewKey: `gap:${round.round_number}:${gap.gap_id}:${index}`,
    kind: "gap",
    eyebrow: "Agent 执行缺口",
    title: `Agent 尚未完成：${recovery.branchTitle}`,
    detail: gap.detail,
    factSummary,
    impact: `只影响“${recovery.branchTitle}”分支。它不表示源文件有错，也不会撤销其他已完成分支或已有成果。`,
    review: null,
    status: recovery.mode === "new_run" ? "旧 Run 已结束" : "可恢复",
    roundNumber: round.round_number,
    branchTitle: recovery.branchTitle,
    fileRefs: uniqueFileRefs([...gap.candidate_file_refs, ...recovery.attemptedFileRefs]),
    anchors: [],
    findingId: null,
    affectedBranchIds: gap.branch_id ? [gap.branch_id] : [],
    resolution: null,
    decisionRecord: null,
    decisionRequest: null,
    serverFact: recovery.analysisCalled
      ? `分析模型已经调用，服务端${recovery.analysisOutputUsed ? "采用了可核对部分" : "未采用未通过校验的返回内容"}；候选文件和分支状态均已保留。`
      : "服务端尚未采用任何分析结果；候选文件和分支状态均已保留。",
    boundary: "这是一条 Agent 执行缺口，不是文件修改请求。没有服务端 Evidence Anchor 时系统不会伪造行号，也不要求你在表格里猜答案。",
    gapRecovery: recovery,
  };
}

function branchReviewRequest(branch: LoopBranch, gaps: EvidenceGap[], round: LoopRound, run: HarnessRun): EvidenceReviewRequest {
  const gap = gaps.find((candidate) => candidate.branch_id === branch.branch_id);
  const fallbackGap: EvidenceGap = gap ?? {
    gap_id: `gap-${branch.branch_id.slice(-12)}`,
    branch_id: branch.branch_id,
    label: `“${branch.title}”尚未形成可核对证据`,
    detail: branch.objective,
    candidate_file_refs: branch.missing_file_refs,
  };
  return gapReviewRequest(fallbackGap, gap ? gaps.indexOf(gap) : 0, round, branch, run);
}

function proposalReviewRequest(proposal: string, index: number, result: HarnessResult, roundNumber: number | null): EvidenceReviewRequest {
  return {
    reviewKey: `proposal:${roundNumber ?? "final"}:${index}:${proposal}`,
    kind: "proposal",
    eyebrow: "Agent 下一步建议",
    title: `建议 ${index + 1}`,
    detail: proposal,
    factSummary: null,
    impact: null,
    review: null,
    status: "尚未逐项验证",
    roundNumber,
    branchTitle: null,
    fileRefs: uniqueFileRefs(result.findings.flatMap((finding) => finding.file_refs)),
    anchors: [],
    findingId: null,
    affectedBranchIds: [],
    resolution: null,
    decisionRecord: null,
    decisionRequest: null,
    serverFact: "该建议来自本轮已读取资料和已形成的发现；只有用户确认后，服务端才会创建新的独立 Run。",
    boundary: "当前协议没有为每条 follow_up 单独绑定引用。下方文件是本轮结果上下文，不应被理解为这条建议的直接证据。",
    gapRecovery: null,
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

function normalizeEvidenceCandidate(value: unknown): EvidenceCandidate | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const candidateId = asText(raw.candidate_id);
  const fileRef = asText(raw.file_ref);
  const locatorKind = asText(raw.locator_kind);
  const start = asNumber(raw.start);
  const end = asNumber(raw.end);
  const excerpt = asText(raw.excerpt);
  if (!candidateId || !fileRef || !["text_lines", "table_rows"].includes(locatorKind) || start < 1 || end < start || !excerpt) return null;
  return {
    candidate_id: candidateId,
    file_ref: fileRef,
    locator_kind: locatorKind as EvidenceCandidate["locator_kind"],
    start,
    end,
    excerpt,
    source_revision: asText(raw.source_revision || raw.sourceRevision) || null,
    context_before: asText(raw.context_before) || null,
    context_after: asText(raw.context_after) || null,
  };
}

function normalizeEvidenceResolution(value: unknown): EvidenceResolution | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  const role = asText(raw.role);
  const resolutionId = asText(raw.resolution_id);
  const findingId = asText(raw.finding_id);
  const fileRef = asText(raw.file_ref);
  if (!resolutionId || !findingId || !fileRef || !["exact", "ambiguous", "unavailable", "stale", "rejected"].includes(status) || !["expected", "observed", "support", "contradiction", "context"].includes(role)) return null;
  return {
    resolution_id: resolutionId,
    finding_id: findingId,
    finding_title: asText(raw.finding_title, "待核对发现"),
    fact_summary: asText(raw.fact_summary) || null,
    impact: asText(raw.impact) || null,
    branch_id: asText(raw.branch_id) || null,
    file_ref: fileRef,
    role: role as EvidenceRole,
    label: asText(raw.label, "候选原文"),
    query_excerpt: asText(raw.query_excerpt),
    status: status as EvidenceResolution["status"],
    reason: asText(raw.reason, "证据位置需要人工核对。"),
    candidates: Array.isArray(raw.candidates)
      ? raw.candidates.map(normalizeEvidenceCandidate).filter((item): item is EvidenceCandidate => item !== null)
      : [],
    selected_candidate_id: asText(raw.selected_candidate_id) || null,
    source_revision: asText(raw.source_revision || raw.sourceRevision) || null,
    decision_request: normalizeDecisionRequest(raw.decision_request) ?? (Array.isArray(raw.decision_requests) ? raw.decision_requests.map(normalizeDecisionRequest).find((item): item is DecisionRequest => item !== null) ?? null : null),
    decision_status: normalizeDecisionState(raw.decision_status || raw.decisionState),
  };
}

function resolutionReviewRequest(
  resolution: EvidenceResolution,
  roundNumber: number,
  branchTitle: string | null,
  decisions: DecisionRecord[],
  decisionRequests: DecisionRequest[] = [],
): EvidenceReviewRequest {
  const anchors = resolution.candidates.map((candidate): EvidenceAnchor => ({
    file_ref: candidate.file_ref,
    role: resolution.role,
    label: resolution.label,
    locator_kind: candidate.locator_kind,
    start: candidate.start,
    end: candidate.end,
    excerpt: candidate.excerpt,
  }));
  return {
    reviewKey: `resolution:${roundNumber}:${resolution.resolution_id}`,
    kind: "resolution",
    eyebrow: "证据定位待确认",
    title: resolution.finding_title,
    detail: resolution.reason,
    factSummary: resolution.fact_summary,
    impact: resolution.impact,
    review: null,
    status: resolution.status === "ambiguous" ? "需要选择原文位置" : "没有找到原文位置",
    roundNumber,
    branchTitle,
    fileRefs: uniqueFileRefs([resolution.file_ref, ...resolution.candidates.map((candidate) => candidate.file_ref)]),
    anchors,
    findingId: resolution.finding_id,
    affectedBranchIds: resolution.branch_id ? [resolution.branch_id] : [],
    resolution,
    decisionRecord: [...decisions].reverse().find((item) => item.resolution_id === resolution.resolution_id) ?? null,
    decisionRequest: resolution.decision_request ?? decisionRequests.find((item) => item.resolution_id === resolution.resolution_id || item.finding_id === resolution.finding_id) ?? null,
    serverFact: resolution.status === "ambiguous"
      ? `服务端找到 ${resolution.candidates.length} 个真实位置，但不能替用户判断哪一个支撑当前结论。`
      : "服务端没有在本轮安全预览中找到该候选片段，受影响分支已暂停，其他结果保持不变。",
    boundary: "选择候选只确认原文位置，不等于批准结论；继续后只重跑受影响分支，且不会修改文件或执行外部动作。",
    gapRecovery: null,
  };
}

function normalizeFindingReview(value: unknown): FindingReview | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const options = Array.isArray(raw.options) ? raw.options.flatMap((item): FindingDecisionOption[] => {
    if (!item || typeof item !== "object") return [];
    const option = item as Record<string, unknown>;
    const optionId = asText(option.option_id);
    const label = asText(option.label);
    const meaning = asText(option.meaning);
    const agentNextStep = asText(option.agent_next_step);
    const nextInstruction = asText(option.next_instruction);
    if (!["A", "B", "C"].includes(optionId) || !label || !meaning || !agentNextStep || !nextInstruction) return [];
    return [{
      option_id: optionId as FindingDecisionOption["option_id"],
      label,
      meaning,
      agent_next_step: agentNextStep,
      next_instruction: nextInstruction,
      affected_branch_ids: asStrings(option.affected_branch_ids),
      required_file_refs: asStrings(option.required_file_refs),
      estimated_additional_rounds: asNumber(option.estimated_additional_rounds, 1),
      external_action: "none",
    }];
  }) : [];
  const question = asText(raw.question);
  const whyHuman = asText(raw.why_human);
  const recommendationReason = asText(raw.recommendation_reason);
  const afterConfirmation = asText(raw.after_confirmation);
  if (!question || !whyHuman || !recommendationReason || !afterConfirmation) return null;
  const recommended = asText(raw.recommended_option_id);
  return {
    requires_human_decision: raw.requires_human_decision === true,
    question,
    why_human: whyHuman,
    options,
    recommended_option_id: ["A", "B", "C"].includes(recommended)
      ? recommended as FindingDecisionOption["option_id"]
      : null,
    recommendation_reason: recommendationReason,
    after_confirmation: afterConfirmation,
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
    return title && detail && fileRefs.length ? [{
      finding_id: asText(finding.finding_id) || null,
      affected_branch_ids: asStrings(finding.affected_branch_ids),
      title,
      detail,
      fact_summary: asText(finding.fact_summary) || null,
      impact: asText(finding.impact) || null,
      file_refs: fileRefs,
      evidence_anchors: anchors,
      evidence_resolutions: Array.isArray(finding.evidence_resolutions)
        ? finding.evidence_resolutions.map(normalizeEvidenceResolution).filter((item): item is EvidenceResolution => item !== null)
        : [],
      decision_request: normalizeDecisionRequest(finding.decision_request) ?? (Array.isArray(finding.decision_requests) ? finding.decision_requests.map(normalizeDecisionRequest).find((item): item is DecisionRequest => item !== null) ?? null : null),
      review: normalizeFindingReview(finding.review),
    }] : [];
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
  const nextStep: LoopNextStep | null = nextRaw ? {
    decision,
    reason: asText(nextRaw.reason),
    next_question: asText(nextRaw.next_question) || null,
    candidate_file_refs: asStrings(nextRaw.candidate_file_refs),
    candidate_branch_ids: asStrings(nextRaw.candidate_branch_ids),
    recovery_kind: ["source_location", "analysis_output"].includes(asText(nextRaw.recovery_kind))
      ? asText(nextRaw.recovery_kind) as LoopNextStep["recovery_kind"]
      : null,
    evidence_resolutions: Array.isArray(nextRaw.evidence_resolutions)
      ? nextRaw.evidence_resolutions.map(normalizeEvidenceResolution).filter((item): item is EvidenceResolution => item !== null)
      : [],
    decision_requests: Array.isArray(nextRaw.decision_requests)
      ? nextRaw.decision_requests.map(normalizeDecisionRequest).filter((item): item is DecisionRequest => item !== null)
      : [],
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
    analysis_structure_rejected: "分析格式未通过，正在受控重试",
    analysis_validation_rejected: "原文位置未通过，正在受控重试",
    analysis_scope_filtered: "已过滤任务范围外的候选发现",
    decision_gate_suppressed: "已取消没有矛盾证据的人工阻塞",
    analysis_partial_adopted: "仅采用可定位的发现",
    analysis_recovery_required: "需要缩小范围后继续",
    evidence_disambiguation_required: "需要你选择原文位置",
    partial_artifact_saved: "已保留可核对成果",
    decision_requested: "需要人工决定处理口径",
    decision_recorded: "人工决定已写入回执",
    branch_resumed_from_checkpoint: "仅恢复受影响分支",
    deterministic_office_tool_started: "确定性办公工具开始处理",
    run_workspace_artifact_written: "真实成果文件已生成",
    deterministic_verification_completed: "成果已通过确定性检查",
    scenario_effect_bounded: "场景效果在能力边界停止",
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
  const tone = event.event_name === "harness_failed" || event.event_name === "plan_validation_rejected" || event.event_name === "analysis_structure_rejected" || event.event_name === "analysis_validation_rejected" || event.event_name === "analysis_recovery_required" || event.event_name === "evidence_disambiguation_required" || event.event_name === "scenario_effect_bounded" || event.event_name.includes("stopped") ? "warning"
    : ["analysis_scope_filtered", "decision_gate_suppressed"].includes(event.event_name) ? "success"
      : event.event_name.includes("planning") || event.event_name.includes("analysis") ? "model"
      : event.event_name.includes("validation") || TERMINAL_EVENTS.has(event.event_name) ? "success" : "neutral";
  return {
    sequence: event.sequence,
    eventName: event.event_name,
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
    return title && detail && refs.length ? [{
      finding_id: asText(finding.finding_id) || null,
      affected_branch_ids: asStrings(finding.affected_branch_ids),
      title,
      detail,
      fact_summary: asText(finding.fact_summary) || null,
      impact: asText(finding.impact) || null,
      file_refs: refs,
      evidence_anchors: anchors,
      evidence_resolutions: Array.isArray(finding.evidence_resolutions)
        ? finding.evidence_resolutions.map(normalizeEvidenceResolution).filter((item): item is EvidenceResolution => item !== null)
        : [],
      decision_request: normalizeDecisionRequest(finding.decision_request) ?? (Array.isArray(finding.decision_requests) ? finding.decision_requests.map(normalizeDecisionRequest).find((item): item is DecisionRequest => item !== null) ?? null : null),
      review: normalizeFindingReview(finding.review),
    }] : [];
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

function normalizeArtifactCheck(value: unknown): ArtifactCheck | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const checkId = asText(raw.check_id);
  const label = asText(raw.label);
  const detail = asText(raw.detail);
  if (!checkId || !label || !detail || typeof raw.passed !== "boolean") return null;
  return { check_id: checkId, label, passed: raw.passed, detail };
}

function normalizeWorkspaceArtifact(value: unknown): WorkspaceArtifact | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const artifactId = asText(raw.artifact_id);
  const mediaType = asText(raw.media_type);
  const verifierStatus = asText(raw.verifier_status);
  if (!artifactId || !["text/csv", "text/markdown", "application/zip", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"].includes(mediaType) || !["passed", "failed"].includes(verifierStatus)) return null;
  const checks = Array.isArray(raw.checks)
    ? raw.checks.map(normalizeArtifactCheck).filter((item): item is ArtifactCheck => item !== null)
    : [];
  return {
    artifact_id: artifactId,
    capability_id: asText(raw.capability_id),
    scenario_id: asText(raw.scenario_id),
    title: asText(raw.title, "运行成果"),
    file_name: asText(raw.file_name, "运行成果"),
    media_type: mediaType as WorkspaceArtifact["media_type"],
    size: asNumber(raw.size),
    version: asNumber(raw.version, 1),
    round_number: asNumber(raw.round_number, 1),
    source_file_refs: asStrings(raw.source_file_refs),
    validator_id: asText(raw.validator_id),
    verifier_status: verifierStatus as WorkspaceArtifact["verifier_status"],
    checks,
    summary: asText(raw.summary),
    covered_period: asText(raw.covered_period) || null,
    statistic_basis: asText(raw.statistic_basis) || null,
    purpose: asText(raw.purpose) || null,
    record_count: typeof raw.record_count === "number" && Number.isInteger(raw.record_count) && raw.record_count >= 0 ? raw.record_count : null,
    download_path: asText(raw.download_path),
    created_at: asText(raw.created_at),
    original_inputs_modified: false,
    review_required: true,
    external_action: "none",
  };
}

function normalizeEffectReceipt(value: unknown): EffectReceipt | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const receiptId = asText(raw.receipt_id);
  const status = asText(raw.status);
  if (!receiptId || !["passed", "failed", "blocked_external_boundary", "unsupported_local_capability"].includes(status)) return null;
  return {
    receipt_id: receiptId,
    capability_id: asText(raw.capability_id),
    scenario_id: asText(raw.scenario_id),
    status: status as EffectReceipt["status"],
    state: asText(raw.state),
    action: asText(raw.action),
    observation: asText(raw.observation),
    cost: asText(raw.cost),
    result: asText(raw.result),
    source_file_refs: asStrings(raw.source_file_refs),
    artifact_ids: asStrings(raw.artifact_ids),
    prohibited_side_effects: asStrings(raw.prohibited_side_effects),
    created_at: asText(raw.created_at),
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

function normalizeDecisionRecord(value: unknown): DecisionRecord | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const decisionId = asText(raw.decision_id);
  const action = asText(raw.action);
  const findingId = asText(raw.finding_id);
  if (!decisionId || !findingId || !["accept", "decline", "defer", "cancel"].includes(action)) return null;
  const optionId = asText(raw.selected_option_id);
  return {
    decision_id: decisionId,
    action: action as DecisionRecord["action"],
    finding_id: findingId,
    resolution_id: asText(raw.resolution_id) || null,
    branch_id: asText(raw.branch_id) || null,
    selected_option_id: ["A", "B", "C"].includes(optionId) ? optionId as FindingDecisionOption["option_id"] : null,
    selected_candidate_id: asText(raw.selected_candidate_id) || null,
    feedback: asText(raw.feedback) || null,
    idempotency_ref: asText(raw.idempotency_ref) || null,
    recorded_at: asText(raw.recorded_at),
    accepted_task_version: asNumber(raw.accepted_task_version),
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
  const maxRounds = asNumber(contractRaw.max_rounds, asNumber(budgetRaw.max_rounds, 12));
  const maxFilesPerRound = asNumber(contractRaw.max_files_per_round, asNumber(budgetRaw.max_files_per_round, 16));
  const maxModelCalls = asNumber(contractRaw.max_model_calls, asNumber(budgetRaw.max_model_calls, 30));
  const deadlineSeconds = asNumber(contractRaw.deadline_seconds, asNumber(budgetRaw.deadline_seconds, 7200));
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
  const workspaceArtifacts = Array.isArray(raw.workspace_artifacts)
    ? raw.workspace_artifacts.map(normalizeWorkspaceArtifact).filter((item): item is WorkspaceArtifact => item !== null)
    : [];
  const effectReceipts = Array.isArray(raw.effect_receipts)
    ? raw.effect_receipts.map(normalizeEffectReceipt).filter((item): item is EffectReceipt => item !== null)
    : [];
  const branches = Array.isArray(raw.branches)
    ? raw.branches.map(normalizeBranch).filter((item): item is LoopBranch => item !== null)
    : [];
  const commits = Array.isArray(raw.commits)
    ? raw.commits.map(normalizeCommit).filter((item): item is LoopCommit => item !== null)
    : [];
  const decisionRecords = Array.isArray(raw.decision_records)
    ? raw.decision_records.map(normalizeDecisionRecord).filter((item): item is DecisionRecord => item !== null)
    : [];
  const decisionRequests = Array.isArray(raw.decision_requests)
    ? raw.decision_requests.map(normalizeDecisionRequest).filter((item): item is DecisionRequest => item !== null)
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
    decision_records: decisionRecords,
    decision_requests: decisionRequests,
    branches,
    active_branch_id: asText(raw.active_branch_id) || null,
    artifact_versions: artifactVersions,
    workspace_artifacts: workspaceArtifacts,
    effect_receipts: effectReceipts,
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
  const terminalRecovery = state.runStatus === "stopped" && Boolean(latestRound?.next_step?.recovery_kind);
  const verifiedOutcomeWithAuditPending = Boolean(
    state.verifiedEffectReady
    && latestRound?.next_step?.decision === "waiting_input"
  );
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
      <header><span>第 {latestRound.round_number} 轮</span><b>{verifiedOutcomeWithAuditPending ? "成果可用，审计待补充" : gateLabel(latestRound.next_step?.decision)}</b></header>
      <ol>{LOOP_PHASES.slice(0, 5).map((phase, index) => <li key={phase.key} className={index < phaseIndex || latestRound.status === "completed" ? "is-complete" : index === phaseIndex ? "is-active" : ""}><span>{index < phaseIndex || latestRound.status === "completed" ? <IconCheck aria-hidden="true" /> : index + 1}</span><b>{phase.label}</b></li>)}</ol>
      {verifiedOutcomeWithAuditPending
        ? <p><IconAlertTriangle aria-hidden="true" />成果的 {state.passedArtifactChecks}/{state.totalArtifactChecks} 项检查已通过；仍有来源定位需要 Agent 补齐，不代表文件缺失。</p>
        : latestRound.evidence_gaps[0] && <p><IconAlertTriangle aria-hidden="true" />{latestRound.evidence_gaps[0].label}</p>}
    </section>}
    {latestRound?.next_step?.recovery_kind && <div className="trace-recovery-hint"><IconArrowRight aria-hidden="true" /><span><b>{verifiedOutcomeWithAuditPending ? "成果不受影响" : terminalRecovery ? "本次 Run 已结束" : "下一步已准备好"}</b>{verifiedOutcomeWithAuditPending ? "回到主区可下载成果；来源定位属于 Agent 的审计修复，不要求你修改文件。" : terminalRecovery ? "回到主区选择一个未完成分支，以它为目标创建新的独立 Run。" : "回到主区选择一个最小分支，可补充方向后继续。"}</span></div>}
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
    {state.error && <footer className="is-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span><b>{state.error}</b>{state.runStatus === "failed" && <small>主区已提供“缩小范围重新核对”，也可以直接编辑任务后重新运行。</small>}</span></footer>}
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

function evidenceLocationLabel(anchor: Pick<EvidenceAnchor, "locator_kind" | "start" | "end">, file: HarnessFile | undefined) {
  const range = anchor.start === anchor.end ? `${anchor.start}` : `${anchor.start}-${anchor.end}`;
  if (anchor.locator_kind === "table_rows") return `数据第 ${range} 行`;
  if (file?.preview_kind === "text") return `第 ${range} 行`;
  return `安全预览第 ${range} 行`;
}

function evidenceRevisionLabel(revision: string | null | undefined) {
  if (!revision) return "本轮安全预览版本未提供";
  return `源文件版本 ${revision.length > 14 ? `${revision.slice(0, 14)}…` : revision}`;
}

function resolutionStatusLabel(status: EvidenceResolution["status"]) {
  const labels: Record<EvidenceResolution["status"], string> = {
    exact: "已唯一定位",
    ambiguous: "多个位置匹配",
    unavailable: "未找到位置",
    stale: "源版本已变化",
    rejected: "候选被拒绝",
  };
  return labels[status];
}

function EvidenceReviewDialog({
  request,
  files,
  onClose,
  onOpenFile,
  onStartTask,
  onControl,
  starting,
  controlBusy,
}: {
  request: EvidenceReviewRequest;
  files: HarnessFile[];
  onClose: () => void;
  onOpenFile: (file: HarnessFile) => void;
  onStartTask: (instruction: string) => Promise<boolean>;
  onControl: (command: LoopCommand, options?: LoopControlOptions) => Promise<boolean>;
  starting: boolean;
  controlBusy: LoopCommand | null;
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
  const [selectedOptionId, setSelectedOptionId] = useState<FindingDecisionOption["option_id"] | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(request.resolution?.selected_candidate_id ?? null);
  const [showRecommendation, setShowRecommendation] = useState(false);
  const [sourceHintMode, setSourceHintMode] = useState(false);
  const [decisionFeedback, setDecisionFeedback] = useState("");
  const selectedFile = reviewFiles.find((file) => file.file_ref === selectedFileRef) ?? null;
  const activeAnchor = activeAnchorIndex >= 0 && reviewAnchors[activeAnchorIndex]?.file_ref === selectedFileRef
    ? reviewAnchors[activeAnchorIndex]
    : null;

  useEffect(() => {
    setActiveAnchorIndex(reviewAnchors.length ? 0 : -1);
    setSelectedFileRef(reviewAnchors[0]?.file_ref ?? reviewFiles[0]?.file_ref ?? "");
    setSelectedOptionId(null);
    setSelectedCandidateId(request.resolution?.selected_candidate_id ?? null);
    setShowRecommendation(false);
    setSourceHintMode(false);
    setDecisionFeedback("");
    closeButtonRef.current?.focus();
  }, [request.reviewKey, request.review, request.resolution, reviewAnchors, reviewFiles]);

  const deferAndClose = useCallback(async () => {
    const shouldRecordDefer = !request.decisionRecord
      && request.decisionRequest?.state !== "deferred"
      && Boolean(request.findingId)
      && (request.kind === "resolution" || Boolean(request.review?.requires_human_decision));
    onClose();
    if (!shouldRecordDefer || !request.findingId) return true;
    return onControl("decision", {
      decisionAction: "defer",
      findingId: request.findingId,
      resolutionId: request.resolution?.resolution_id,
      branchId: request.decisionRequest?.branch_id ?? request.resolution?.branch_id ?? request.affectedBranchIds[0],
      decisionRequestId: request.decisionRequest?.request_id,
      sourceRevision: request.decisionRequest?.source_revision || request.resolution?.source_revision || undefined,
      feedback: decisionFeedback,
    });
  }, [decisionFeedback, onClose, onControl, request.affectedBranchIds, request.decisionRecord, request.decisionRequest, request.findingId, request.kind, request.resolution, request.review?.requires_human_decision]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") void deferAndClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [deferAndClose]);

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
  const selectedOption = request.review?.options.find((option) => option.option_id === selectedOptionId) ?? null;
  const isAmbiguousResolution = request.kind === "resolution" && request.resolution?.status === "ambiguous";
  const isDirectRetryResolution = request.kind === "resolution"
    && request.resolution !== null
    && ["unavailable", "stale"].includes(request.resolution.status);
  const isDirectRetryGap = request.kind === "gap"
    && request.gapRecovery !== null
    && request.gapRecovery.mode !== "inspect_only"
    && ["source_location", "analysis_output"].includes(request.gapRecovery.cause);
  const dialogTitle = request.kind === "finding" && request.review?.requires_human_decision
    ? "需要你核对并决定下一步"
    : isAmbiguousResolution ? `从 ${request.resolution?.candidates.length ?? 0} 个原文位置中选 1 个`
    : isDirectRetryResolution ? `下一步：只重试“${request.branchTitle ?? "当前"}”分支`
    : request.kind === "resolution" ? "需要你确认原文位置"
    : isDirectRetryGap ? request.gapRecovery?.mode === "new_run"
      ? `下一步：用“${request.branchTitle ?? "当前"}”分支新建任务`
      : `下一步：只重试“${request.branchTitle ?? "当前"}”分支`
    : request.title;
  const startDecisionTask = async () => {
    if (!selectedOption || !request.findingId) return;
    const recorded = await onControl("decision", {
      decisionAction: "accept",
      findingId: request.findingId,
      branchId: request.decisionRequest?.branch_id ?? selectedOption.affected_branch_ids[0] ?? request.affectedBranchIds[0],
      selectedOptionId: selectedOption.option_id,
      decisionRequestId: request.decisionRequest?.request_id,
      sourceRevision: request.decisionRequest?.source_revision || undefined,
      feedback: decisionFeedback,
    });
    if (!recorded) return;
    const instruction = [
      selectedOption.next_instruction,
      `用户决定：${selectedOption.option_id} · ${selectedOption.label}。`,
      decisionFeedback.trim() ? `用户补充：${decisionFeedback.trim()}` : "",
    ].filter(Boolean).join("\n");
    if (await onStartTask(instruction)) onClose();
  };
  const declineFinding = async () => {
    if (!request.findingId) return;
    const recorded = await onControl("decision", {
      decisionAction: "decline",
      findingId: request.findingId,
      branchId: request.decisionRequest?.branch_id ?? request.resolution?.branch_id ?? request.affectedBranchIds[0],
      decisionRequestId: request.decisionRequest?.request_id,
      sourceRevision: request.decisionRequest?.source_revision || request.resolution?.source_revision || undefined,
      feedback: decisionFeedback,
    });
    if (recorded) onClose();
  };
  const cancelDecision = async () => {
    if (!request.findingId || (request.decisionRecord && request.decisionRecord.action !== "defer")) { onClose(); return; }
    const recorded = await onControl("decision", {
      decisionAction: "cancel",
      findingId: request.findingId,
      resolutionId: request.resolution?.resolution_id,
      branchId: request.resolution?.branch_id ?? request.affectedBranchIds[0],
      decisionRequestId: request.decisionRequest?.request_id,
      sourceRevision: request.decisionRequest?.source_revision || request.resolution?.source_revision || undefined,
      feedback: decisionFeedback,
    });
    if (recorded) onClose();
  };
  const resolveEvidence = async () => {
    const resolution = request.resolution;
    if (!resolution || !selectedCandidateId || !request.findingId) return;
    const candidate = resolution.candidates.find((item) => item.candidate_id === selectedCandidateId);
    if (!candidate) return;
    const recorded = await onControl("decision", {
      decisionAction: "accept",
      findingId: request.findingId,
      resolutionId: resolution.resolution_id,
      branchId: resolution.branch_id ?? undefined,
      selectedCandidateId,
      decisionRequestId: request.decisionRequest?.request_id,
      sourceRevision: request.decisionRequest?.source_revision || resolution.source_revision || candidate.source_revision || undefined,
      feedback: decisionFeedback,
    });
    if (!recorded) return;
    onClose();
  };
  const retryUnavailable = async () => {
    const resolution = request.resolution;
    if (!resolution || !request.findingId) return;
    const recorded = await onControl("decision", {
      decisionAction: "decline",
      findingId: request.findingId,
      resolutionId: resolution.resolution_id,
      branchId: resolution.branch_id ?? undefined,
      decisionRequestId: request.decisionRequest?.request_id,
      sourceRevision: request.decisionRequest?.source_revision || resolution.source_revision || undefined,
      feedback: decisionFeedback,
    });
    if (!recorded) return;
    const steered = await onControl("steer", {
      instruction: `当前候选原文无法定位。只重试受影响分支，优先寻找更长、唯一且可逐字核对的来源；找不到时明确保留缺口。${decisionFeedback.trim()}`,
    });
    if (!steered) return;
    if (resolution.branch_id) {
      const resumed = await onControl("resume", { branchId: resolution.branch_id });
      if (!resumed) return;
    }
    onClose();
  };
  const recoverGap = async () => {
    const recovery = request.gapRecovery;
    if (!recovery) return;
    if (recovery.mode === "resume_branch" && recovery.branchId) {
      if (decisionFeedback.trim()) {
        const steered = await onControl("steer", {
          instruction: `${recovery.nextInstruction}\n用户补充：${decisionFeedback.trim()}`,
        });
        if (!steered) return;
      }
      const resumed = await onControl("resume", { branchId: recovery.branchId });
      if (resumed) onClose();
      return;
    }
    if (recovery.mode === "new_run") {
      const instruction = [
        recovery.newRunInstruction,
        decisionFeedback.trim() ? `用户补充：${decisionFeedback.trim()}` : "",
      ].filter(Boolean).join("\n");
      if (await onStartTask(instruction)) onClose();
    }
  };
  const startStructuredReview = async () => {
    const instruction = `复核以下问题，逐条定位原文并给出需要人工决定的处理选项：${request.title}`;
    if (await onStartTask(instruction)) onClose();
  };
  return <div className="evidence-review-backdrop" role="presentation">
    <section className={`evidence-review-page is-${tone}`} role="dialog" aria-modal="true" aria-labelledby="evidence-review-title">
      <header className="evidence-review-header">
        <div><IconGitCommit aria-hidden="true" /><div><span>问题审查页</span><h2 id="evidence-review-title">{dialogTitle}</h2></div></div>
        <button ref={closeButtonRef} type="button" className="icon-action" onClick={() => void deferAndClose()} aria-label="关闭问题审查页" title="关闭并暂缓"><IconX aria-hidden="true" /></button>
      </header>
      <div className="evidence-review-layout">
        <aside className="evidence-review-history" aria-label="审查记录">
          <header><span>{request.eyebrow}</span><b className={`is-${tone}`}>{request.status}</b></header>
          <dl>
            {request.roundNumber !== null && <><dt>发生位置</dt><dd>第 {request.roundNumber} 轮{request.branchTitle ? ` / ${request.branchTitle}` : ""}</dd></>}
            <dt>关联资料</dt><dd>{reviewFiles.length} 份</dd>
          </dl>
          <ol>
            <li><span><IconGitCommit aria-hidden="true" /></span><div><b>{request.kind === "gap" ? "Agent 未完成" : "Agent 提出"}</b><p>{request.kind === "proposal" ? "形成一条待确认的下一步建议" : request.kind === "gap" ? "本轮没有交付可定位的证据，只停止受影响分支" : "形成一条待复核发现"}</p></div></li>
            <li><span><IconShieldCheck aria-hidden="true" /></span><div><b>服务端记录</b><p>{request.serverFact}</p></div></li>
            <li className="is-current"><span><IconEye aria-hidden="true" /></span><div><b>{request.kind === "gap" ? "选择恢复方式" : "等待你核对"}</b><p>{request.kind === "gap" ? "你不需要修改源文件；可直接让 Agent 只重试这个分支。" : "对照右侧原始资料，判断 Agent 描述是否成立。"}</p></div></li>
          </ol>
          <footer><IconAlertTriangle aria-hidden="true" /><p>{request.boundary}</p></footer>
        </aside>
        <main className="evidence-review-main">
          {request.kind !== "gap" && !isDirectRetryResolution && <section className={`evidence-review-claim${isAmbiguousResolution ? " is-ambiguous" : ""}`} aria-labelledby="review-summary-title">
            <header><span>{isAmbiguousResolution ? "下一步只做 1 件事" : "问题处置单"}</span><h3 id="review-summary-title">{isAmbiguousResolution ? `从 ${request.resolution?.candidates.length ?? 0} 个真实位置中选 1 个` : "先看事实，再看影响，最后决定下一步"}</h3></header>
            {isAmbiguousResolution ? <ol className="review-summary-steps">
              <li><b>1</b><div><span>为什么需要你</span><strong>同一段原文匹配到多个位置，Agent 不能替你选择。</strong></div></li>
              <li className="is-decision"><b>2</b><div><span>你只需要选什么</span><strong>从下方候选位置中选 1 个真实位置。</strong></div></li>
              <li><b>3</b><div><span>选完发生什么</span><strong>只重跑“{request.branchTitle || "当前"}”分支；不修改文件，不执行外部动作。</strong></div></li>
            </ol> : <ol className="review-summary-steps">
              <li><b>1</b><div><span>发生了什么</span><strong>{request.factSummary || request.title}</strong></div></li>
              <li><b>2</b><div><span>不处理的影响</span><strong>{request.impact || "影响尚未单独结构化，请先核对下方证据后再作判断。"}</strong></div></li>
              <li className={request.review?.requires_human_decision ? "is-decision" : ""}><b>3</b><div><span>现在需要谁做什么</span><strong>{request.review?.requires_human_decision ? "需要你选择处理口径，Agent 不会替你决定。" : request.review ? "无需业务裁决，但结果仍需人工复核。" : "这是旧结果，尚未生成结构化处置选项。"}</strong></div></li>
            </ol>}
            <details><summary>查看 Agent 的完整说明</summary><p>{request.detail}</p></details>
          </section>}
          {request.kind === "gap" && request.gapRecovery && <section className="evidence-gap-recovery" aria-labelledby="gap-recovery-title">
            <header><div><span>{request.gapRecovery.mode === "inspect_only" ? "当前只能查看" : "下一步只做 1 件事"}</span><h3 id="gap-recovery-title">{request.gapRecovery.mode === "inspect_only" ? "查看停下原因，暂不启动新调用" : request.gapRecovery.mode === "new_run" ? "用此分支新建任务继续" : "直接让 Agent 重试此分支"}</h3><p>{request.gapRecovery.mode === "inspect_only" ? "当前状态没有可证明的原地恢复入口。" : request.gapRecovery.mode === "new_run" ? "旧 Run 已结束，不能原地续跑。不需要修改文件，也不需要填写内容；点击后会创建一个只处理此分支的新任务。" : "不需要修改文件，也不需要填写内容。只有你点击后，Agent 才会继续。"}</p></div><b>{request.gapRecovery.mode === "inspect_only" ? "仅查看" : "推荐"}</b></header>
            <footer>{request.gapRecovery.mode !== "inspect_only" && <button type="button" className="is-primary" onClick={() => void recoverGap()} disabled={controlBusy !== null || starting}><IconRefresh aria-hidden="true" />{starting || controlBusy ? "正在提交" : request.gapRecovery.mode === "new_run" ? "新建任务，只续办此分支" : "继续任务，只重试此分支"}</button>}<button type="button" onClick={() => void deferAndClose()} disabled={controlBusy !== null || starting}>暂不处理此分支</button></footer>
            {request.gapRecovery.mode !== "inspect_only" && <details className="gap-extra-hint"><summary>我有额外线索</summary><label className="decision-feedback"><span>给 Agent 的线索（可选）</span><textarea value={decisionFeedback} onChange={(event) => setDecisionFeedback(event.target.value)} placeholder="例如：优先检查 F07、版本号和测试日期" /></label></details>}
          </section>}
          {isDirectRetryResolution && request.resolution && <section className="evidence-gap-recovery" aria-labelledby="resolution-retry-title">
            <header><div><span>下一步只做 1 件事</span><h3 id="resolution-retry-title">直接让 Agent 重试此分支</h3><p>不需要修改文件，也不需要填写内容。只有你点击后，Agent 才会继续。</p></div><b>推荐</b></header>
            <footer><button type="button" className="is-primary" disabled={controlBusy !== null} onClick={() => void retryUnavailable()}><IconRefresh aria-hidden="true" />继续任务，只重试此分支</button><button type="button" onClick={() => void deferAndClose()} disabled={controlBusy !== null}>暂不处理此分支</button></footer>
            <details className="gap-extra-hint"><summary>我有额外线索</summary><label className="decision-feedback"><span>给 Agent 的线索（可选）</span><textarea value={decisionFeedback} onChange={(event) => setDecisionFeedback(event.target.value)} placeholder="例如：同时核对版本号和测试日期" /></label></details>
          </section>}
          <details className={`evidence-workbench-disclosure${request.kind === "gap" || isDirectRetryResolution ? " is-gap" : ""}`} open={request.kind === "gap" || isDirectRetryResolution ? undefined : true}>
            <summary>{request.kind === "gap" || isDirectRetryResolution ? "为什么停下 / 查看相关文件" : "证据与资料"}</summary>
            {request.kind === "gap" && request.gapRecovery && <ol className="gap-recovery-facts">
              <li><b>1</b><span><strong>原本要确认</strong>{request.gapRecovery.branchObjective}</span></li>
              <li><b>2</b><span><strong>Agent 已尝试</strong>{request.gapRecovery.attemptedFileRefs.length} 份文件 · {request.gapRecovery.analysisCalled ? "模型已调用" : "尚未完成模型调用"} · {request.gapRecovery.analysisOutputUsed ? "可核对部分已保留" : "返回内容未采用"}</span></li>
              <li><b>3</b><span><strong>已经保留</strong>{request.gapRecovery.verifiedFileRefs.length} 份已核对来源、其他分支和已有成果版本均不回退。</span></li>
              <li><b>4</b><span><strong>不会发生</strong>不会要求你改源文件，也不会执行外部动作。</span></li>
            </ol>}
            <div className="evidence-review-workbench">
            <div className="evidence-review-index">
              {request.kind === "resolution" && request.resolution?.status !== "rejected" && request.resolution?.candidates.length ? <section className="evidence-review-pinpoint" aria-labelledby="evidence-pinpoint-title">
                <header><div><span>候选原文对照</span><h3 id="evidence-pinpoint-title">先比较真实位置，再选择要恢复的候选</h3><p className="evidence-revision-note">{evidenceRevisionLabel(request.resolution.source_revision || request.resolution.candidates[0]?.source_revision)} · 候选不会自动替你选择</p></div><b>{request.resolution.candidates.length} 个候选</b></header>
                <div className="evidence-anchor-map resolution-candidate-map">
                  {request.resolution.candidates.map((candidate, index) => {
                    const file = files.find((item) => item.file_ref === candidate.file_ref);
                    const anchorIndex = reviewAnchors.findIndex((anchor) => anchor.file_ref === candidate.file_ref && anchor.start === candidate.start && anchor.end === candidate.end && anchor.excerpt === candidate.excerpt);
                    const active = anchorIndex === activeAnchorIndex;
                    const selected = selectedCandidateId === candidate.candidate_id;
                    const difference = candidate.context_before || candidate.context_after
                      ? `上下文：${[candidate.context_before, candidate.context_after].filter(Boolean).join(" … ")}`
                      : `区别依据：${file?.display_label ?? "文件"} · ${evidenceLocationLabel(candidate, file)}`;
                    return <button
                      type="button"
                      key={candidate.candidate_id}
                      className={`evidence-anchor-item is-${request.resolution?.role ?? "context"}${active ? " is-active" : ""}${selected ? " is-chosen" : ""}`}
                      onClick={() => { if (anchorIndex >= 0) selectAnchor(anchorIndex); else setSelectedFileRef(candidate.file_ref); setSelectedCandidateId(candidate.candidate_id); }}
                      aria-label={`选择候选原文 ${index + 1}：${file?.display_label ?? "允许范围内文件"} ${evidenceLocationLabel(candidate, file)}`}
                    >
                      <b>{selected ? <IconCheck aria-hidden="true" /> : index + 1}</b>
                      <span><small>{resolutionStatusLabel(request.resolution?.status ?? "ambiguous")} · 候选 {index + 1}</small><strong>{file?.display_label ?? "允许范围内文件"} · {evidenceLocationLabel(candidate, file)}</strong><em>{evidenceRevisionLabel(candidate.source_revision || request.resolution?.source_revision)}</em><q>{candidate.excerpt}</q><small className="evidence-candidate-difference">{difference}</small></span>
                    </button>;
                  })}
                </div>
                {isAmbiguousResolution && <div className="resolution-choice-action" role="status"><span>{selectedCandidateId ? "已选 1 个位置。确认后只重跑这个分支。" : `请先从上方 ${request.resolution?.candidates.length ?? 0} 个位置中选 1 个。`}</span><button type="button" className="is-primary" disabled={!selectedCandidateId || controlBusy !== null} onClick={() => void resolveEvidence()}><IconPlayerPlay aria-hidden="true" />采用此位置并只重跑本分支</button></div>}
              </section> : reviewAnchors.length > 0 ? <section className="evidence-review-pinpoint" aria-labelledby="evidence-pinpoint-title">
                <header><div><span>证据定位</span><h3 id="evidence-pinpoint-title">选择一条，右侧打开真实文件并高亮对应位置</h3></div><b>{reviewAnchors.length} 处</b></header>
                <div className="evidence-anchor-map">
                  {reviewAnchors.map((anchor, index) => {
                    const file = files.find((item) => item.file_ref === anchor.file_ref);
                    return <button type="button" key={`${anchor.file_ref}:${anchor.locator_kind}:${anchor.start}:${anchor.end}:${index}`} className={`evidence-anchor-item is-${anchor.role}${index === activeAnchorIndex ? " is-active" : ""}`} onClick={() => selectAnchor(index)} aria-label={`定位证据 ${index + 1}：${anchor.label}`}>
                      <b>{index + 1}</b><span><small>{EVIDENCE_ROLE_LABELS[anchor.role]}</small><strong>{anchor.label}</strong><em>来自 {file?.display_label ?? "允许范围内文件"} · {evidenceLocationLabel(anchor, file)} · 服务端逐字匹配</em><q>{anchor.excerpt}</q></span>
                    </button>;
                  })}
                </div>
              </section> : <div className="evidence-review-unlocated"><IconAlertTriangle aria-hidden="true" /><p><b>{request.kind === "gap" ? "这里没有高亮，不是让你猜哪一行" : "当前只能定位到文件，不能定位到具体原文"}</b><span>{request.kind === "gap" ? "Agent 本轮没有交付可唯一定位的引用。源文件没有被判错，你也不需要代替 Agent 在文件中找答案。" : request.kind === "finding" ? "这是旧结果或服务端没有找到唯一片段；系统不会伪造行号或高亮。" : "该记录没有逐段证据锚点，请按关联文件或下一轮候选范围核对。"}</span></p></div>}
              <section className="evidence-review-source" aria-label="相关资料">
                <header><div><span>关联文件</span><h3>{reviewAnchors.length ? "每处证据都来自下列真实文件" : "点击文件查看完整内容"}</h3></div><b>{reviewFiles.length} 份</b></header>
                {reviewFiles.length > 0 ? <div className="evidence-review-files">{reviewFiles.map((file) => { const anchorCount = reviewAnchors.filter((anchor) => anchor.file_ref === file.file_ref).length; return <button type="button" key={file.file_ref} className={file.file_ref === selectedFileRef ? "is-active" : ""} onClick={() => selectFile(file.file_ref)}><IconFile aria-hidden="true" /><span><b>{file.display_label}</b><small>{file.display_path}{anchorCount ? ` · ${anchorCount} 处定位` : ""}</small></span></button>; })}</div> : <p className="evidence-review-no-source">当前服务端事实没有提供可打开的关联文件。系统不会用静态示例补齐。</p>}
              </section>
            </div>
            <section className="evidence-review-preview" aria-label="资料原文预览">
              {activeAnchor && selectedFile && <div className="active-evidence-callout"><span>正在核对第 {activeAnchorIndex + 1} 处</span><b>{selectedFile.display_label} · {evidenceLocationLabel(activeAnchor, selectedFile)}</b><q>{activeAnchor.excerpt}</q><small>下方黄色区域是这段内容在文件预览中的实际位置。</small></div>}
              {request.kind === "gap" && selectedFile && !activeAnchor && <div className="gap-preview-callout"><span>本轮尝试过的文件</span><b>{selectedFile.display_label}</b><small>下方展示原始内容，但不会高亮：服务端尚未收到可唯一定位的逐字引用。</small></div>}
              <FilePreview preview={preview} file={selectedFile} loading={previewLoading} error={previewError} anchor={activeAnchor} />
              {selectedFile && <button type="button" className="evidence-review-open-workspace" onClick={async () => { await deferAndClose(); onOpenFile(selectedFile); }}><IconArrowRight aria-hidden="true" />回到资料库中打开</button>}
            </section>
            </div>
          </details>
          {request.decisionRecord && <section className="decision-record-receipt" role="status">
            <IconCircleCheck aria-hidden="true" />
            <div><span>人工决定已记录 · v{request.decisionRecord.accepted_task_version}</span><b>{request.decisionRecord.action === "accept" ? "已接受" : request.decisionRecord.action === "decline" ? "已否决" : request.decisionRecord.action === "cancel" ? "已取消" : "已暂缓"}</b><p>回执 {request.decisionRecord.decision_id}{request.decisionRecord.idempotency_ref ? ` · 幂等 ${request.decisionRecord.idempotency_ref}` : ""} · 外部动作：无</p></div>
          </section>}
          {request.kind === "resolution" && request.resolution ? <details className={`resolution-audit-details${isAmbiguousResolution || isDirectRetryResolution ? " is-collapsed" : ""}`} open={isAmbiguousResolution || isDirectRetryResolution ? undefined : true}>
            <summary>{isAmbiguousResolution || isDirectRetryResolution ? "查看技术回执与其他处理方式" : "证据定位处理"}</summary>
            <section className="evidence-resolution-decision" aria-labelledby="resolution-decision-title">
            <header><div><span>证据定位状态</span><h3 id="resolution-decision-title">{request.resolution.status === "ambiguous" ? `${request.resolution.candidates.length} 个位置都匹配，需要你选择` : `${resolutionStatusLabel(request.resolution.status)}，需要决定恢复方式`}</h3><p>{request.resolution.reason}</p></div><b>{request.resolution.status === "ambiguous" ? `${request.resolution.candidates.length} 个候选` : resolutionStatusLabel(request.resolution.status)}</b></header>
            {request.decisionRequest && <dl className="decision-request-meta"><div><dt>待决编号</dt><dd>{request.decisionRequest.request_id}</dd></div><div><dt>基于版本</dt><dd>Run v{request.decisionRequest.expected_version ?? "当前"} · {evidenceRevisionLabel(request.decisionRequest.source_revision || request.resolution.source_revision)}</dd></div><div><dt>绑定对象</dt><dd>受影响分支 · {request.decisionRequest.candidate_ids.length || request.resolution.candidates.length} 个候选</dd></div></dl>}
            <ol className="resolution-impact-list">
              <li><b>1</b><span><strong>只影响哪里</strong>{request.branchTitle || "当前待处理分支"}</span></li>
              <li><b>2</b><span><strong>已经保留什么</strong>已完成分支、可核对发现和已有成果版本均不回退。</span></li>
              <li><b>3</b><span><strong>继续后做什么</strong>{request.resolution.status === "ambiguous" ? "从你选择的位置重新核对，只重跑受影响分支。" : "寻找更长且唯一的原文；仍找不到就保留缺口。"}</span></li>
              <li><b>4</b><span><strong>不会发生什么</strong>不会改原文件，不会调用外部业务系统。</span></li>
            </ol>
            {request.resolution.status === "ambiguous" && <p className="resolution-choice-status">{selectedCandidateId ? "已选择一个真实位置；请再确认是否从这里继续。" : "请先在上方候选原文中选择一个位置。"}</p>}
            <label className="decision-feedback"><span>{sourceHintMode ? "补充来源线索（可选，不要填写内部路径）" : "补充给重跑分支的反馈（可选）"}</span><textarea value={decisionFeedback} onChange={(event) => setDecisionFeedback(event.target.value)} placeholder={sourceHintMode ? "例如：优先查找与 F07 同一版本的兼容测试记录" : "例如：同时核对版本号和测试日期，不要只比较结论字段"} /></label>
            <footer>
              <div className="resolution-secondary-actions">
                <button type="button" onClick={() => void deferAndClose()} disabled={controlBusy !== null}>保留现有结果，稍后处理</button>
                <button type="button" onClick={() => setSourceHintMode(true)} disabled={controlBusy !== null || sourceHintMode}>补充来源</button>
                <button type="button" onClick={() => void cancelDecision()} disabled={controlBusy !== null}>取消这次待决</button>
                <button type="button" onClick={async () => { if (await onControl("stop")) onClose(); }} disabled={controlBusy !== null}><IconPlayerStop aria-hidden="true" />结束并保留</button>
              </div>
              {!isAmbiguousResolution && !isDirectRetryResolution && <button type="button" className="is-primary" disabled={controlBusy !== null} onClick={() => void retryUnavailable()}><IconRefresh aria-hidden="true" />继续任务，只重试此分支</button>}
            </footer>
            </section>
          </details> : null}
          {request.review?.requires_human_decision ? <section className="evidence-review-decision" aria-labelledby="review-decision-title">
            <header><div><span>需要你决断</span><h3 id="review-decision-title">{request.review.question}</h3><p>{request.review.why_human}</p></div><b>后续尚未执行</b></header>
            <div className="decision-options" role="radiogroup" aria-label="处理口径">
              {request.review.options.map((option) => <label key={option.option_id} className={selectedOptionId === option.option_id ? "is-selected" : ""}>
                <input type="radio" name="finding-decision" value={option.option_id} checked={selectedOptionId === option.option_id} onChange={() => setSelectedOptionId(option.option_id)} />
                <b>{option.option_id}</b>
                <span><strong>{option.label}{showRecommendation && request.review?.recommended_option_id === option.option_id ? " · Agent 推荐" : ""}</strong><small>{option.meaning}</small><em>确认后：{option.agent_next_step}</em><small className="decision-option-impact">影响 {option.affected_branch_ids.length || request.affectedBranchIds.length || 1} 个工作分支 · 需要 {option.required_file_refs.length || request.fileRefs.length} 份来源 · 预计最多 {Math.max(1, option.estimated_additional_rounds)} 轮 · 外部动作：无</small></span>
              </label>)}
            </div>
            {request.review.recommended_option_id && !showRecommendation && <div className="decision-recommendation-gate"><span><b>先形成你的判断</b><small>为避免 Agent 的解释先影响你的选择，推荐项默认隐藏。</small></span><button type="button" disabled={!selectedOptionId} onClick={() => setShowRecommendation(true)}><IconEye aria-hidden="true" />{selectedOptionId ? "对照 Agent 建议" : "先选择一个口径"}</button></div>}
            {request.review.recommended_option_id && showRecommendation && <p className="decision-reason"><b>Agent 推荐 {request.review.recommended_option_id}</b>{request.review.recommendation_reason}{selectedOptionId && selectedOptionId !== request.review.recommended_option_id ? ` 你的选择是 ${selectedOptionId}，系统不会替你改选。` : ""}</p>}
            <label className="decision-feedback"><span>补充给 Agent 的反馈（可选）</span><textarea value={decisionFeedback} onChange={(event) => setDecisionFeedback(event.target.value)} placeholder="例如：先以 PRD 为准，但把兼容测试的代码版本也核对清楚" /></label>
            <footer><div><IconShieldCheck aria-hidden="true" /><span><b>{request.review.after_confirmation}</b><small>决定会先写入当前 Run 的版本化回执；接受后才启动新的只读 Control Loop。</small></span></div><div className="decision-footer-actions"><button type="button" onClick={() => void deferAndClose()} disabled={controlBusy !== null}>暂缓处理</button><button type="button" onClick={() => void cancelDecision()} disabled={controlBusy !== null}>取消这次待决</button><button type="button" onClick={() => void declineFinding()} disabled={controlBusy !== null}>否决这条发现</button><button type="button" className="is-primary" disabled={!selectedOption || starting || controlBusy !== null} onClick={() => void startDecisionTask()}><IconPlayerPlay aria-hidden="true" />{starting || controlBusy === "decision" ? "正在记录" : "接受并交给 Agent"}</button></div></footer>
          </section> : request.kind === "finding" ? <section className="evidence-review-legacy">
            <IconAlertTriangle aria-hidden="true" /><div><b>{request.review ? "这条发现只需复核，不需要业务裁决" : "旧结果没有结构化处置选项"}</b><p>{request.review?.after_confirmation || "你仍可查看现有证据；重新核对后，Agent 会按新协议给出事实、影响和可确认的处理选项。"}</p></div>{!request.review && <button type="button" disabled={starting} onClick={() => void startStructuredReview()}><IconRefresh aria-hidden="true" />{starting ? "正在启动" : "重新核对并生成处置方案"}</button>}
          </section> : null}
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
  const [maxRounds, setMaxRounds] = useState(12);
  const [maxFilesPerRound, setMaxFilesPerRound] = useState(16);
  const [maxModelCalls, setMaxModelCalls] = useState(30);
  const [deadlineSeconds, setDeadlineSeconds] = useState(7200);
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
      verifiedEffectReady: Boolean(
        run?.effect_receipts.some((receipt) => receipt.status === "passed")
        && run.workspace_artifacts.length > 0
        && run.workspace_artifacts.every((artifact) => artifact.verifier_status === "passed")
      ),
      passedArtifactChecks: run?.workspace_artifacts.reduce((total, artifact) => total + artifact.checks.filter((check) => check.passed).length, 0) ?? 0,
      totalArtifactChecks: run?.workspace_artifacts.reduce((total, artifact) => total + artifact.checks.length, 0) ?? 0,
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
    if (!workspace || taskInstruction.length < 3) return false;
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
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "任务没有启动");
      setConnection("available");
      return false;
    } finally { setStarting(false); }
  }

  async function controlLoop(command: LoopCommand, options: LoopControlOptions = {}) {
    const current = runRef.current;
    if (!current || (TERMINAL_STATUSES.has(current.status) && !["rollback", "decision"].includes(command))) return false;
    const normalizedInstruction = options.instruction?.trim() || undefined;
    const normalizedFeedback = options.feedback?.trim() || undefined;
    const signature = JSON.stringify({ command, instruction: normalizedInstruction, branchId: options.branchId, artifactVersion: options.artifactVersion, decisionAction: options.decisionAction, findingId: options.findingId, resolutionId: options.resolutionId, selectedOptionId: options.selectedOptionId, selectedCandidateId: options.selectedCandidateId, decisionRequestId: options.decisionRequestId, sourceRevision: options.sourceRevision, feedback: normalizedFeedback, runId: current.run_id });
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
          decision_action: options.decisionAction,
          finding_id: options.findingId,
          resolution_id: options.resolutionId,
          selected_option_id: options.selectedOptionId,
          selected_candidate_id: options.selectedCandidateId,
          decision_request_id: options.decisionRequestId,
          source_revision: options.sourceRevision,
          feedback: normalizedFeedback,
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
              <label><span>最大轮次</span><input type="number" min="1" max="24" value={maxRounds} disabled={runActive} onChange={(event) => setMaxRounds(Math.max(1, Math.min(24, Number(event.target.value) || 1)))} /></label>
              <label><span>每轮文件</span><input type="number" min="1" max="24" value={maxFilesPerRound} disabled={runActive} onChange={(event) => setMaxFilesPerRound(Math.max(1, Math.min(24, Number(event.target.value) || 1)))} /></label>
              <label><span>模型调用</span><input type="number" min="2" max="60" value={maxModelCalls} disabled={runActive} onChange={(event) => setMaxModelCalls(Math.max(2, Math.min(60, Number(event.target.value) || 2)))} /></label>
              <label><span>Agent 执行时间</span><input type="number" min="20" max="14400" step="60" value={deadlineSeconds} disabled={runActive} onChange={(event) => setDeadlineSeconds(Math.max(20, Math.min(14400, Number(event.target.value) || 20)))} /></label>
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
          {view === "loop" && <LoopView run={run} files={allFiles} controlBusy={controlBusy} onControl={controlLoop} onReview={setReviewRequest} onStartTask={startTask} starting={starting} />}
          {view === "result" && <ResultView result={run?.result ?? null} artifacts={run?.artifact_versions ?? []} commit={run?.last_commit ?? null} decisions={run?.decision_records ?? []} decisionRequests={run?.decision_requests ?? []} files={allFiles} onOpenFile={openFile} onReview={setReviewRequest} onStartTask={startTask} starting={starting} />}
        </div>
        <details className="workspace-boundary"><summary><IconShieldCheck aria-hidden="true" />数据与执行边界</summary><p>{workspace.data_boundary} Agent 可以检索整个资料库，但每轮只读取服务端校验通过且受预算约束的文件；本轮不会修改原文件或执行外部动作。</p></details>
        {error && run?.status !== "failed" && <div className="workspace-error" role="alert"><IconAlertTriangle aria-hidden="true" /><span>{error}</span></div>}
      </section>
    </div>
    {reviewRequest && <EvidenceReviewDialog request={reviewRequest} files={allFiles} onClose={() => setReviewRequest(null)} onOpenFile={openFile} onStartTask={startTask} onControl={controlLoop} starting={starting} controlBusy={controlBusy} />}
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
  onStartTask,
  starting,
}: {
  run: HarnessRun | null;
  files: HarnessFile[];
  controlBusy: LoopCommand | null;
  onControl: (command: LoopCommand, options?: LoopControlOptions) => Promise<boolean>;
  onReview: (request: EvidenceReviewRequest) => void;
  onStartTask: (instruction: string) => Promise<boolean>;
  starting: boolean;
}) {
  const [selectedRoundNumber, setSelectedRoundNumber] = useState(1);
  const [steerDraft, setSteerDraft] = useState("");
  const [recoveryDraft, setRecoveryDraft] = useState("");
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
  const preservedArtifactVersion = run.artifact_versions.at(-1)?.version ?? currentArtifactVersion;
  const recoveryKind = selectedRound?.next_step?.recovery_kind ?? null;
  const guidedRecovery = Boolean(recoveryKind) && waitingForBranch;
  const boundedTerminalRecovery = run.status === "stopped"
    && selectedRound?.round_number === run.current_round
    && selectedRound?.next_step?.decision === "budget_exhausted"
    && Boolean(recoveryKind);
  const decisionRequests = uniqueDecisionRequests([
    ...run.decision_requests,
    ...(selectedRound?.next_step?.decision_requests ?? []),
  ]);
  const pendingResolutions = (selectedRound?.next_step?.evidence_resolutions ?? []).filter((resolution) => {
    const request = resolution.decision_request ?? decisionRequests.find((item) => item.resolution_id === resolution.resolution_id || item.finding_id === resolution.finding_id);
    const record = [...run.decision_records].reverse().find((item) => item.resolution_id === resolution.resolution_id);
    const decisionState = resolution.decision_status ?? request?.state ?? (record?.action === "accept" ? "accepted" : record?.action === "decline" ? "declined" : record?.action === "cancel" ? "cancelled" : record?.action === "defer" ? "deferred" : null);
    return !["accepted", "declined", "cancelled", "rejected"].includes(decisionState ?? "");
  });
  const recoveryBranches = roundBranches.filter((branch) => branch.status === "waiting_input").sort((left, right) => left.missing_file_refs.length - right.missing_file_refs.length);
  const verifiedEffectReady = run.effect_receipts.some((receipt) => receipt.status === "passed")
    && run.workspace_artifacts.length > 0
    && run.workspace_artifacts.every((artifact) => artifact.verifier_status === "passed");
  const passedArtifactChecks = run.workspace_artifacts.reduce((total, artifact) => total + artifact.checks.filter((check) => check.passed).length, 0);
  const totalArtifactChecks = run.workspace_artifacts.reduce((total, artifact) => total + artifact.checks.length, 0);
  const verifiedOutcomeWithAuditPending = verifiedEffectReady
    && selectedRound?.next_step?.decision === "waiting_input"
    && Boolean(selectedRound.evidence_gaps.length);
  const evidenceGapGroups = verifiedOutcomeWithAuditPending
    ? groupEvidenceGaps(selectedRound?.evidence_gaps ?? [])
    : (selectedRound?.evidence_gaps ?? []).map((gap) => ({
        groupKey: gap.gap_id,
        candidateFileRefs: uniqueFileRefs(gap.candidate_file_refs),
        gaps: [gap],
      }));
  const selectedRoundGateLabel = verifiedOutcomeWithAuditPending
    ? "成果可用，审计待补充"
    : gateLabel(selectedRound?.next_step?.decision);
  const terminalCandidateBranches = new Set(selectedRound?.next_step?.candidate_branch_ids ?? []);
  const terminalRecoveryBranches = roundBranches
    .filter((branch) => terminalCandidateBranches.size > 0
      ? terminalCandidateBranches.has(branch.branch_id)
      : ["waiting_input", "stopped", "failed"].includes(branch.status))
    .sort((left, right) => left.missing_file_refs.length - right.missing_file_refs.length || left.input_file_refs.length - right.input_file_refs.length);
  const failedAtSourceLocation = run.status === "failed" && run.events.some((event) => event.eventName === "analysis_validation_rejected");
  const retryBranch = [...roundBranches].sort((left, right) => left.input_file_refs.length - right.input_file_refs.length)[0] ?? null;
  const retryInstruction = `${run.instruction}\n恢复策略：先只核对${retryBranch ? `“${retryBranch.title}”` : "一个最小证据分支"}，逐条使用可唯一定位的原文；若资料不足，明确列出缺少的版本、字段或记录，不要输出无法核对的结论。`;
  const startBranchRecoveryRun = async (branch: LoopBranch) => {
    const sourceLabels = branch.input_file_refs.map(fileLabel);
    const userDirection = recoveryDraft.trim();
    const branchInstruction = [
      run.instruction,
      `续办分支：${branch.title}`,
      `本次以“${branch.objective}”作为任务目标。请从整个资料库自主查找完成这一目标所需的最小证据，逐条提供可唯一定位的原文位置。`,
      sourceLabels.length > 0 ? `上次 Run 为该分支选择过：${sourceLabels.join("、")}。这些只是历史选择，不限制新 Run 重新检索整个资料库。` : "新 Run 仍可自主检索整个资料库。",
      "若仍无法核对，请明确列出缺少的文件、版本、字段或记录，不要生成无法回到原文的结论。",
      userDirection ? `用户补充：${userDirection}` : "",
      "边界：只读分析，不修改原文件，不执行外部动作。",
    ].filter(Boolean).join("\n");
    await onStartTask(branchInstruction);
  };

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
    {run.status === "failed" && <section className="loop-failure-recovery" role="alert">
      <header><IconAlertTriangle aria-hidden="true" /><div><span>这次运行已停下，但不是死路</span><h3>{failedAtSourceLocation ? "候选结论无法唯一定位到原文" : "本轮结果没有通过服务端校验"}</h3></div></header>
      <ol>
        <li><b>1</b><span><strong>已经保留</strong>任务目标、服务端计划、{run.budget.model_calls_used} 次模型调用记录和已选文件范围都还在。</span></li>
        <li><b>2</b><span><strong>没有发生</strong>候选结果未被采用，也没有修改文件或执行外部动作。</span></li>
        <li><b>3</b><span><strong>建议这样继续</strong>{failedAtSourceLocation ? "缩小到一个分支，用更长且唯一的原文重新核对。" : "编辑上方任务目标，或按推荐的最小范围重新运行。"}</span></li>
      </ol>
      <footer><span>{run.validation_errors[0] || "服务端已安全停止本轮任务。"}</span><button type="button" disabled={starting} onClick={() => void onStartTask(retryInstruction)}><IconRefresh aria-hidden="true" />{starting ? "正在重建任务" : "缩小范围重新核对"}</button></footer>
    </section>}
    {boundedTerminalRecovery && <section className="loop-terminal-recovery" aria-labelledby="terminal-recovery-title">
      <header><IconAlertTriangle aria-hidden="true" /><div><span>预算停止后的下一步</span><h3 id="terminal-recovery-title">当前 Run 已到预算边界，不能继续原地运行</h3><p><b>停止原因：{run.budget.stop_reason || "剩余预算不足以完成下一步"}。</b> 这不是整项工作丢失。旧 Run、调用回执和成果版本保持不变；请选择一个未完成分支，以它为目标创建新的独立 Run。</p></div></header>
      <div className="source-recovery-facts"><span><b>只影响</b>{terminalRecoveryBranches.length} 条尚未完成的分支</span><span><b>已保留</b>Plan、调用回执、分支状态与{preservedArtifactVersion ? `成果 v${preservedArtifactVersion}` : "阶段成果"}</span><span><b>未发生</b>原文件修改或外部动作</span></div>
      <label><span>补充给新任务的方向（可选）</span><textarea value={recoveryDraft} onChange={(event) => setRecoveryDraft(event.target.value)} placeholder="例如：先核对上线配置清单与功能测试报告中的版本和日期字段" /></label>
      <div className="source-recovery-branches">{terminalRecoveryBranches.map((branch, index) => <article key={branch.branch_id}><div><b>{index === 0 ? "最小续办分支" : "可单独续办"}</b><h4>{branch.title}</h4><p>{branch.objective}</p><small>{branch.input_file_refs.length > 0 ? branch.input_file_refs.map(fileLabel).join(" · ") : "由 Agent 在整个资料库中重新选证"}</small></div><button type="button" disabled={starting} onClick={() => void startBranchRecoveryRun(branch)}><IconRefresh aria-hidden="true" />{starting ? "正在创建" : "用此分支创建新任务"}</button></article>)}</div>
      <footer><IconShieldCheck aria-hidden="true" /><span>这是新的 Task Contract，不会覆盖或假装续跑旧 Run；新 Run 仍由服务端冻结整库索引并重新校验证据。</span></footer>
    </section>}
    {!boundedTerminalRecovery && <section className="loop-controls" aria-label="人工控制">
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
    </section>}
    <nav className="loop-round-tabs" aria-label="研究轮次">
      {run.rounds.length ? run.rounds.map((round) => <button type="button" key={round.round_number} className={round.round_number === selectedRound?.round_number ? "is-active" : ""} onClick={() => setSelectedRoundNumber(round.round_number)}>
        <span>{round.status === "completed" ? <IconCheck aria-hidden="true" /> : round.round_number}</span>
        <b>第 {round.round_number} 轮</b>
        <small>{round.round_number === selectedRound?.round_number && verifiedOutcomeWithAuditPending ? "成果可用，审计待补充" : round.next_step ? gateLabel(round.next_step.decision) : LOOP_PHASES.find((phase) => phase.key === round.phase)?.label}</small>
      </button>) : <span>服务端正在建立第一轮。</span>}
    </nav>
    {(run.workspace_artifacts.length > 0 || run.effect_receipts.length > 0) && <WorkspaceArtifactSection artifacts={run.workspace_artifacts} receipts={run.effect_receipts} />}
    {selectedRound && <article className="loop-round-detail">
      <header><div><span>本轮问题</span><h3>{selectedRound.question}</h3></div><b>{selectedRoundGateLabel}</b></header>
      <ol className="loop-phase-rail">
        {LOOP_PHASES.slice(0, 5).map((phase, index) => {
          const activeIndex = LOOP_PHASES.findIndex((item) => item.key === selectedRound.phase);
          const complete = index < activeIndex || selectedRound.status === "completed";
          return <li key={phase.key} className={complete ? "is-complete" : index === activeIndex ? "is-active" : ""}><span>{complete ? <IconCheck aria-hidden="true" /> : index + 1}</span><b>{phase.label}</b></li>;
        })}
      </ol>
      {selectedRound.input_file_refs.length > 0 && <section className="loop-round-files"><span>Agent 本轮自主选择</span>{selectedRound.selection_reason && <p>{selectedRound.selection_reason}</p>}<div>{selectedRound.input_file_refs.map((ref) => <b key={ref}>{fileLabel(ref)}</b>)}</div></section>}
      {guidedRecovery && <section className="loop-source-recovery" aria-labelledby="source-recovery-title">
        <header><IconAlertTriangle aria-hidden="true" /><div><span>{verifiedOutcomeWithAuditPending ? "成果与审计分开处理" : "这轮需要分支级处理"}</span><h3 id="source-recovery-title">{verifiedOutcomeWithAuditPending ? `成果已生成，${evidenceGapGroups.length} 处来源定位待补充` : `共有 ${evidenceGapGroups.length} 个待处理，每次处理 1 个`}</h3><p>{verifiedOutcomeWithAuditPending ? "成果文件可以下载；这里缺的是 Agent 说明中的原文位置，不是源文件，也不是日期结果。" : pendingResolutions.some((item) => item.status === "ambiguous") ? "需要选择原文的分支与可以直接重试的分支已经分开标注。" : "这些分支都不需要你修改文件；选择一条后才会继续。"}</p></div></header>
        <div className="source-recovery-facts"><span><b>{verifiedOutcomeWithAuditPending ? `${passedArtifactChecks}/${totalArtifactChecks} 通过` : "已保留"}</b>{verifiedOutcomeWithAuditPending ? "成果确定性检查" : "本轮计划、文件范围、调用记录"}</span><span><b>{verifiedOutcomeWithAuditPending ? "待补充" : "未采用"}</b>{verifiedOutcomeWithAuditPending ? "Agent 来源定位" : "无法定位的候选结论"}</span><span><b>未发生</b>原文件修改或外部动作</span></div>
      </section>}
      {roundBranches.length > 0 && <section className="loop-branches" aria-label={`第 ${selectedRound.round_number} 轮任务分支`}>
        <header><div><span>任务分支现场</span><h3>{roundBranches.length} 条分支，分别保留证据状态</h3></div><b>{roundBranches.filter((branch) => branch.status === "completed").length}/{roundBranches.length} 已核对</b></header>
        <ol>{roundBranches.map((branch, index) => <li key={branch.branch_id} className={`is-${branch.status}${run.active_branch_id === branch.branch_id ? " is-selected" : ""}`}>
          <span>{branch.status === "completed" ? <IconCheck aria-hidden="true" /> : index + 1}</span>
          <div><header><b>{branch.title}</b><small>{verifiedOutcomeWithAuditPending && branch.status === "waiting_input" ? "审计待补充" : branchStatusLabel(branch.status)}</small></header><p>{branch.objective}</p><footer><span>{branch.input_file_refs.length} 份资料</span>{branch.depends_on.length > 0 && <span>{branch.depends_on.length} 条前序依赖</span>}{branch.parent_branch_id && <span>续自上一轮</span>}{branch.missing_file_refs.length > 0 && <strong>{verifiedOutcomeWithAuditPending ? `${branch.missing_file_refs.length} 处来源待定位` : `缺 ${branch.missing_file_refs.length} 份引用`}</strong>}</footer></div>
          {branch.status === "waiting_input" && waitingForBranch && !guidedRecovery && <div className="loop-branch-actions"><button type="button" className="is-review" onClick={() => onReview(branchReviewRequest(branch, selectedRound.evidence_gaps, selectedRound, run))}><IconEye aria-hidden="true" />查看问题</button><button type="button" onClick={() => void onControl("resume", { branchId: branch.branch_id })} disabled={!canResume || controlBusy !== null}><IconPlayerPlay aria-hidden="true" />{controlBusy === "resume" ? "正在启动" : "继续此分支"}</button></div>}
        </li>)}</ol>
      </section>}
      {selectedRound.result && <section className="loop-round-result"><span>本轮核对结果</span><h3>{selectedRound.result.summary}</h3><p>{selectedRound.result.findings.length} 条发现，引用 {selectedRound.verified_file_refs.length} 份文件。</p>{selectedRound.result.findings.length > 0 && <div className="loop-review-links">{selectedRound.result.findings.map((finding, index) => <button type="button" key={`${finding.title}:${index}`} onClick={() => onReview(findingReviewRequest(finding, index, selectedRound.round_number, run.decision_records, decisionRequests))}><IconEye aria-hidden="true" />核对：{finding.title}</button>)}</div>}</section>}
      {evidenceGapGroups.length > 0 && <section className="loop-gap" aria-labelledby={`loop-gap-title-${selectedRound.round_number}`}>
        <header><IconRoute aria-hidden="true" /><div><span>{verifiedOutcomeWithAuditPending ? "审计说明" : "待处理分支"}</span><h3 id={`loop-gap-title-${selectedRound.round_number}`}>{verifiedOutcomeWithAuditPending ? `还有 ${evidenceGapGroups.length} 处来源定位待补充` : `共有 ${evidenceGapGroups.length} 个待处理，每次处理 1 个`}</h3><p>{verifiedOutcomeWithAuditPending ? "相同来源影响的多个内部分支已合并显示；补齐定位不会重新生成或覆盖当前成果。" : boundedTerminalRecovery ? "旧 Run 已结束；先选一条路径创建新任务，其他结果保持不变。" : "先选一条路径继续；没有被选择的分支不会启动，也不会消耗下一轮预算。"}</p></div><b>{verifiedOutcomeWithAuditPending ? "不影响成果" : "每次 1 个"}</b></header>
        <ol className="loop-gap-branches">{evidenceGapGroups.map((group, index) => {
          const gap = group.gaps[0];
          const affectedBranches = group.gaps.flatMap((item) => {
            const branch = run.branches.find((candidate) => candidate.branch_id === item.branch_id);
            return branch ? [branch] : [];
          });
          const branch = affectedBranches.sort((left, right) => left.input_file_refs.length - right.input_file_refs.length)[0] ?? null;
          const affectedBranchIds = new Set(affectedBranches.map((item) => item.branch_id));
          const branchRequests = decisionRequests.filter((item) => affectedBranchIds.has(item.branch_id ?? "") && ["pending", "deferred"].includes(item.state ?? "pending"));
          const openRequest = branchRequests.find((item) => Boolean(item.resolution_id)) ?? branchRequests[0] ?? null;
          const unresolvedResolutions = run.rounds.flatMap((round) => round.next_step?.evidence_resolutions ?? []);
          const resolution = unresolvedResolutions.find((item) => item.resolution_id === openRequest?.resolution_id)
            ?? unresolvedResolutions.find((item) => affectedBranchIds.has(item.branch_id ?? "") && ["ambiguous", "unavailable", "stale"].includes(item.status))
            ?? null;
          const sourceRefs = group.candidateFileRefs.length > 0 ? group.candidateFileRefs : uniqueFileRefs([...(branch?.input_file_refs ?? []), ...gap.candidate_file_refs]);
          const primarySource = sourceRefs[0] ? fileLabel(sourceRefs[0]) : null;
          const requiresSourceChoice = resolution?.status === "ambiguous";
          const evidenceGateLabel = requiresSourceChoice
            ? `需要从 ${resolution.candidates.length} 个原文位置中选 1 个`
            : verifiedOutcomeWithAuditPending
              ? "Agent 未完成原文定位"
              : "无需核对文件，建议重试";
          const reviewRequest = resolution
            ? resolutionReviewRequest(resolution, selectedRound.round_number, branch?.title ?? null, run.decision_records, decisionRequests)
            : gapReviewRequest(gap, index, selectedRound, branch, run);
          const nextLabel = requiresSourceChoice
            ? "需要你选 1 个位置"
            : boundedTerminalRecovery
              ? "查看后创建新任务"
              : verifiedOutcomeWithAuditPending
                ? "让 Agent 补齐来源定位"
                : "建议只重试此分支";
          const groupTitle = verifiedOutcomeWithAuditPending && affectedBranches.length > 1
            ? `同一来源影响 ${affectedBranches.length} 个内部步骤`
            : branch?.title ?? gap.label;
          return <li key={group.groupKey} className={`is-${branch?.status ?? "waiting_input"}`} aria-label={`${verifiedOutcomeWithAuditPending ? "审计项" : "分支"}：${groupTitle}`}>
            <section className="loop-gap-branch-identity"><span>{verifiedOutcomeWithAuditPending ? "审计项" : "分支"} {index + 1}</span><h4>{groupTitle}</h4><b>{verifiedOutcomeWithAuditPending ? "不影响成果" : branch ? branchStatusLabel(branch.status) : "等待处理"}</b></section>
            <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
            <section className="loop-gap-branch-stage"><span>{verifiedOutcomeWithAuditPending ? "待定位来源" : "当前材料"}</span><strong>{primarySource ?? "等待 Agent 重新检索"}</strong><small>{verifiedOutcomeWithAuditPending ? `${sourceRefs.length > 1 ? `另有 ${sourceRefs.length - 1} 份 · ` : ""}文件存在，缺少的是说明中的精确位置` : `${sourceRefs.length > 1 ? `另有 ${sourceRefs.length - 1} 份 · ` : ""}${branch?.verified_file_refs.length ?? 0}/${sourceRefs.length} 份已形成引用`}</small></section>
            <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
            <section className="loop-gap-branch-stage is-gate"><span>{verifiedOutcomeWithAuditPending ? "审计状态" : "证据门"}</span><strong>{evidenceGateLabel}</strong><small>{verifiedOutcomeWithAuditPending ? "成果检查已通过；系统不会把定位缺口解释为文件或日期错误。" : gap.detail}</small></section>
            <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
            <section className="loop-gap-branch-next"><span>下一步</span><strong>{nextLabel}</strong><button type="button" onClick={() => onReview(reviewRequest)}>{requiresSourceChoice ? <IconEye aria-hidden="true" /> : verifiedOutcomeWithAuditPending ? <IconRefresh aria-hidden="true" /> : <IconPlayerPlay aria-hidden="true" />}{requiresSourceChoice ? "选择原文位置" : boundedTerminalRecovery ? "查看如何续办" : verifiedOutcomeWithAuditPending ? "补齐来源定位" : "继续此分支"}</button></section>
          </li>;
        })}</ol>
        <footer><IconShieldCheck aria-hidden="true" /><span>{verifiedOutcomeWithAuditPending ? "成果可以继续下载和复核；补齐来源定位只更新审计说明，不修改原始文件。" : "已有成果版本和已完成分支不会被覆盖；当前仍是只读核对，不修改文件，也不执行外部动作。"}</span></footer>
      </section>}
      {selectedRound.next_step && <footer className={selectedRound.next_step.decision === "completed" ? "is-complete" : "is-next"}><div><span>服务端决定</span><strong>{selectedRoundGateLabel}</strong><p>{verifiedOutcomeWithAuditPending ? "成果文件已通过确定性检查；当前只保留 Agent 来源定位的审计缺口。" : selectedRound.next_step.reason}</p></div>{selectedRound.next_step.decision === "waiting_input" ? <b>{verifiedOutcomeWithAuditPending ? "成果不受影响" : guidedRecovery ? "选择恢复分支继续" : "选择上方分支继续"}</b> : boundedTerminalRecovery ? <b>选择上方分支创建新任务</b> : selectedRound.next_step.decision === "next_round" ? <IconArrowRight aria-hidden="true" /> : null}</footer>}
    </article>}
    {run.artifact_versions.length > 0 && <section className="artifact-evolution" aria-label="成果版本">
      <header><div><span>不可变成果历史</span><h3>每轮形成一个可追溯版本</h3></div><b>{currentArtifactVersion ? `当前 v${currentArtifactVersion}` : "尚未提交"}</b></header>
      <ol>{run.artifact_versions.map((artifact) => <li key={`${artifact.artifact_id}:${artifact.version}`} className={currentArtifactVersion === artifact.version ? "is-current" : ""}><span>v{artifact.version}</span><div><b>{currentArtifactVersion === artifact.version ? "当前版本" : artifact.status === "verified" ? "已核对" : "阶段草稿"}</b><p>第 {artifact.round_number} 轮 · {artifact.finding_count} 条发现 · {artifact.source_file_refs.length} 份引用</p></div>{terminal && currentArtifactVersion !== artifact.version && <button type="button" title={`恢复为成果版本 v${artifact.version}`} onClick={() => void onControl("rollback", { artifactVersion: artifact.version })} disabled={controlBusy !== null}><IconRefresh aria-hidden="true" />{controlBusy === "rollback" ? "恢复中" : "恢复"}</button>}</li>)}</ol>
      {run.last_commit && <footer><IconCircleCheck aria-hidden="true" /><span>{run.last_commit.summary}</span><b>{run.commits.length} 次提交记录</b></footer>}
    </section>}
    {run.brief && <section className={`loop-brief is-${run.brief.outcome}`}><IconCircleCheck aria-hidden="true" /><div><span>任务简报</span><h3>{run.brief.summary}</h3><p>外部动作：未发生 · 结果仍需人工复核</p></div></section>}
  </section>;
}

function WorkspaceArtifactSection({ artifacts, receipts }: { artifacts: WorkspaceArtifact[]; receipts: EffectReceipt[] }) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const passedChecks = artifacts.reduce((total, artifact) => total + artifact.checks.filter((check) => check.passed).length, 0);
  const totalChecks = artifacts.reduce((total, artifact) => total + artifact.checks.length, 0);
  const latestReceipt = receipts.at(-1) ?? null;
  const boundary = latestReceipt && latestReceipt.status !== "passed" ? latestReceipt : null;
  const downloadArtifact = async (artifact: WorkspaceArtifact) => {
    if (!artifact.download_path.startsWith("/v1/harness/runs/")) {
      setDownloadError("成果下载地址未通过客户端边界检查。");
      return;
    }
    setDownloading(artifact.artifact_id);
    setDownloadError("");
    try {
      const response = await fetch(`${API_BASE}${artifact.download_path}`, { headers: { "X-User-Id": "demo_user" } });
      if (!response.ok) throw new Error("成果文件完整性校验或下载失败。");
      const blobUrl = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = blobUrl;
      link.download = artifact.file_name;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(blobUrl);
    } catch (error) {
      setDownloadError(error instanceof Error ? error.message : "成果文件下载失败。");
    } finally {
      setDownloading(null);
    }
  };
  return <section className={`workspace-artifacts${boundary ? " is-bounded" : ""}`} aria-labelledby="workspace-artifacts-title">
    <header>
      <IconFileDescription aria-hidden="true" />
      <div><span>运行工作区</span><h3 id="workspace-artifacts-title">{artifacts.length > 0 ? `Agent 已生成 ${artifacts.length} 份真实成果文件` : "这项任务尚不能生成可信成果"}</h3><p>{artifacts.length > 0 ? "文件已写入本次 Run 的隔离目录，原始 FORTE 文件没有被修改。" : boundary?.result}</p></div>
      <b>{artifacts.length > 0 ? `${passedChecks}/${totalChecks} 项检查通过` : "未伪造结果"}</b>
    </header>
    {artifacts.length > 0 && <ol>{artifacts.map((artifact) => <li key={artifact.artifact_id} className={artifact.verifier_status === "passed" ? "is-passed" : "is-failed"}>
      <div className="workspace-artifact-file"><span><IconFile aria-hidden="true" /></span><div><h4>{artifact.title}</h4><p>{artifact.summary}</p><small>文件：{artifact.file_name} · 第 {artifact.round_number} 轮 · {formatSize(artifact.size)} · {artifact.source_file_refs.length} 份内容来源</small></div></div>
      <div className="workspace-artifact-status"><b>{artifact.verifier_status === "passed" ? <><IconCheck aria-hidden="true" />确定性检查通过</> : <><IconAlertTriangle aria-hidden="true" />检查未通过</>}</b><span>{artifact.record_count !== null ? `${artifact.record_count} 条记录 · ` : ""}{artifact.checks.filter((check) => check.passed).length}/{artifact.checks.length} 项检查</span></div>
      <button type="button" onClick={() => void downloadArtifact(artifact)} disabled={downloading !== null}><IconDownload aria-hidden="true" />{downloading === artifact.artifact_id ? "正在下载" : "下载成果"}</button>
      {(artifact.covered_period || artifact.statistic_basis || artifact.purpose) && <dl className="workspace-artifact-semantics">
        {artifact.covered_period && <div><dt>涵盖期间</dt><dd>{artifact.covered_period}</dd></div>}
        {artifact.statistic_basis && <div><dt>统计口径</dt><dd>{artifact.statistic_basis}</dd></div>}
        {artifact.purpose && <div><dt>用途</dt><dd>{artifact.purpose}</dd></div>}
      </dl>}
      <details><summary><IconEye aria-hidden="true" />查看逐项检查</summary><ul>{artifact.checks.map((check) => <li key={check.check_id} className={check.passed ? "is-passed" : "is-failed"}><span>{check.passed ? <IconCheck aria-hidden="true" /> : <IconAlertTriangle aria-hidden="true" />}</span><div><b>{check.label}</b><p>{check.detail}</p></div></li>)}</ul></details>
    </li>)}</ol>}
    {boundary && <article className="workspace-effect-boundary"><IconAlertTriangle aria-hidden="true" /><div><b>{boundary.status === "blocked_external_boundary" ? "缺少已授权的外部连接" : boundary.status === "unsupported_local_capability" ? "本地能力仍未实现" : "确定性效果门未通过"}</b><p>{boundary.observation}</p><strong>{boundary.result}</strong></div></article>}
    {latestReceipt && <details className="workspace-effect-receipt"><summary><IconRoute aria-hidden="true" />查看效果回执</summary><ol><li><b>状态</b><span>{latestReceipt.state}</span></li><li><b>动作</b><span>{latestReceipt.action}</span></li><li><b>观察</b><span>{latestReceipt.observation}</span></li><li><b>成本</b><span>{latestReceipt.cost}</span></li><li><b>结果</b><span>{latestReceipt.result}</span></li></ol></details>}
    <footer><IconShieldCheck aria-hidden="true" /><span>原始输入未修改 · 外部动作未发生 · 成果仍需人工复核</span></footer>
    {downloadError && <p className="workspace-artifact-error" role="alert">{downloadError}</p>}
  </section>;
}

function ResultView({
  result,
  artifacts,
  commit,
  decisions,
  decisionRequests,
  files,
  onOpenFile,
  onReview,
  onStartTask,
  starting,
}: {
  result: HarnessResult | null;
  artifacts: ArtifactVersion[];
  commit: LoopCommit | null;
  decisions: DecisionRecord[];
  decisionRequests: DecisionRequest[];
  files: HarnessFile[];
  onOpenFile: (file: HarnessFile) => void;
  onReview: (request: EvidenceReviewRequest) => void;
  onStartTask: (instruction: string) => Promise<boolean>;
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
        <div><h3>{finding.title}</h3><p>{finding.fact_summary || finding.detail}</p>{finding.impact && <small className="finding-impact">影响：{finding.impact}</small>}{finding.review?.requires_human_decision && <b className="finding-decision-badge">需要你决定</b>}<footer>
          <button type="button" className="is-review" onClick={() => onReview(findingReviewRequest(finding, index, findingArtifact?.round_number ?? null, decisions, decisionRequests))}><IconEye aria-hidden="true" />打开审查页</button>
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
