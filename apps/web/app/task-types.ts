export type TaskStatus =
  | "ready"
  | "running"
  | "waiting_input"
  | "paused"
  | "taken_over"
  | "verifying"
  | "committed"
  | "failed"
  | "cancelled";

export type TaskPhase = "contract" | "observe" | "plan" | "act" | "verify" | "commit";

export type TaskStageStatus = "pending" | "running" | "completed" | "failed";
export type TaskStage = "observe" | "plan" | "act" | "verify";
export type TaskStageSource = "deterministic" | "model" | "template_fallback" | "human" | "system";

/**
 * Durable stage facts returned by the progressive Task Runtime.
 * Older servers omit this field; the UI must then stay on the legacy snapshot.
 */
export type TaskStageRecord = {
  phase: TaskStage;
  status: TaskStageStatus;
  summary: string;
  detail: Record<string, unknown>;
  artifact_version_ids: string[];
  generation_source: TaskStageSource;
  started_at: string;
  completed_at?: string | null;
  failed_at?: string | null;
};

export type BranchStatus =
  | "queued"
  | "running"
  | "waiting_evidence"
  | "paused"
  | "taken_over"
  | "verifying"
  | "failed"
  | "committed"
  | "cancelled";

export type ArtifactStatus = "candidate" | "verified" | "rejected" | "committed" | "invalidated";
export type VerificationStatus = "pending" | "passed" | "failed" | "conflict";
export type ConflictStatus = "open" | "resolved" | "dismissed";
export type ControlKind =
  | "steer"
  | "pause_branch"
  | "resume_branch"
  | "take_over"
  | "return_control"
  | "resolve_evidence";
export type ControlStatus = "accepted" | "applied" | "rejected";

export type TaskEventType =
  | "TASK_CREATED"
  | "TASK_RESTORED"
  | "TASK_STATUS_CHANGED"
  | "TASK_PHASE_CHANGED"
  | "BRANCH_STATUS_CHANGED"
  | "LOOP_STEP_STARTED"
  | "LOOP_STEP_COMPLETED"
  | "ARTIFACT_VERSION_CREATED"
  | "VERIFICATION_RECORDED"
  | "CONFLICT_OPENED"
  | "CONFLICT_RESOLVED"
  | "CONTROL_ACCEPTED"
  | "CONTROL_APPLIED"
  | "CONTROL_REJECTED"
  | "BUDGET_UPDATED"
  | "CHECKPOINT_COMMITTED"
  | "TASK_COMMITTED"
  | "TASK_FAILED";

export type DeliverableSpec = {
  deliverable_id: string;
  title: string;
  kind: "analysis" | "risk_brief" | "reply_draft" | "document" | "mail" | "structured_data";
  completion_criteria: string[];
};

export type TaskBudget = {
  max_steps: number;
  max_tool_calls: number;
  max_runtime_seconds: number;
};

export type TaskBudgetSnapshot = {
  steps_used: number;
  tool_calls_used: number;
  runtime_seconds: number;
  exhausted: boolean;
};

export type TaskContract = {
  title: string;
  objective: string;
  source_scope: string[];
  allowed_capabilities: string[];
  deliverables: DeliverableSpec[];
  completion_criteria: string[];
  budget: TaskBudget;
  deadline_at: string | null;
  schema_version: "1.0";
  task_id: string;
  owner_id: string;
  contract_version: number;
  created_at: string;
};

export type BranchSnapshot = {
  branch_id: string;
  task_id: string;
  title: string;
  objective: string;
  deliverable_ids: string[];
  status: BranchStatus;
  version: number;
  artifact_heads: Record<string, string>;
  issue_ids: string[];
  pause_reason: string | null;
  last_commit_id: string | null;
  created_at: string;
  updated_at: string;
};

export type ArtifactVersion = {
  artifact_version_id: string;
  artifact_id: string;
  task_id: string;
  branch_id: string;
  deliverable_id: string;
  version: number;
  parent_version_id: string | null;
  title: string;
  kind: string;
  status: ArtifactStatus;
  content: Record<string, unknown>;
  content_digest: string;
  source_refs: string[];
  created_by: "agent" | "human" | "system";
  created_at: string;
};

export type VerificationCheck = {
  check_id: string;
  label: string;
  status: "passed" | "failed" | "conflict";
  detail: string;
  source_refs: string[];
};

export type VerificationReport = {
  report_id: string;
  task_id: string;
  branch_id: string;
  artifact_version_id: string;
  status: VerificationStatus;
  checks: VerificationCheck[];
  checked_at: string;
};

export type ConflictRecord = {
  conflict_id: string;
  task_id: string;
  branch_id: string;
  subject: string;
  summary: string;
  source_refs: string[];
  candidate_values: string[];
  status: ConflictStatus;
  resolution: string | null;
  opened_at: string;
  resolved_at: string | null;
};

export type TaskControlCommand = {
  kind: ControlKind;
  branch_id?: string | null;
  instruction?: string | null;
  reason?: string | null;
  selected_source_ref?: string | null;
  expected_task_version: number;
  idempotency_key: string;
};

export type ControlEvent = TaskControlCommand & {
  control_event_id: string;
  task_id: string;
  actor_id: string;
  status: ControlStatus;
  applied_task_version: number | null;
  rejection_reason: string | null;
  created_at: string;
  applied_at: string | null;
};

export type TaskCommit = {
  commit_id: string;
  task_id: string;
  task_version: number;
  artifact_version_ids: string[];
  verification_report_ids: string[];
  state_hash: string;
  summary: string;
  committed_at: string;
};

export type TaskError = {
  code: string;
  scope: "task" | "branch" | "artifact" | "control" | "stream";
  message: string;
  recoverable: boolean;
  user_action: string | null;
};

export type TaskSnapshot = {
  task_id: string;
  trace_id: string;
  owner_id: string;
  contract: TaskContract;
  status: TaskStatus;
  phase: TaskPhase;
  version: number;
  branches: BranchSnapshot[];
  artifact_versions: ArtifactVersion[];
  verification_reports: VerificationReport[];
  conflicts: ConflictRecord[];
  controls: ControlEvent[];
  budget: TaskBudgetSnapshot;
  last_commit: TaskCommit | null;
  last_event_sequence: number;
  last_error: TaskError | null;
  created_at: string;
  updated_at: string;
  stage_records?: TaskStageRecord[];
};

export type TaskEvent = {
  sequence: number;
  event_id: string;
  task_id: string;
  trace_id: string;
  task_version: number;
  branch_id: string | null;
  artifact_version_id: string | null;
  control_event_id: string | null;
  actor_id: string;
  event_type: TaskEventType;
  idempotency_key: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
};
