export type Demo2RouteMode =
  | "tool_call"
  | "single_agent"
  | "fixed_workflow"
  | "adaptive_swarm";

export type Demo2AdmissionStatus = "recommended" | "route_selected";
export type Demo2SelectionSource = "admission" | "user_override";
export type Demo2OverrideScope = "this_run";
export type Demo2ExecutionStatus =
  | "not_started"
  | "queued"
  | "running"
  | "verifying"
  | "completed"
  | "failed"
  | "cancelled";
export type Demo2WorkUnitStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export type Demo2ProcessingKind = "language_model" | "deterministic" | "policy_engine";
export type Demo2ProcessingPath = "language_model" | "deterministic";
export type Demo2ProcessingOutput = "model" | "deterministic" | "template_fallback";
export type Demo2RouteImpactKind = "change" | "preserve" | "no_external_action";
export type Demo2RouteImpactAspect =
  | "route_decision"
  | "work_allocation"
  | "coordination"
  | "human_control"
  | "policy_forecast"
  | "execution_boundary"
  | "external_action";

export type Demo2WorkItemFacts = {
  value_band: "low" | "medium" | "high";
  breadth: number;
  parallelism: number;
  deadline_pressure: "low" | "medium" | "high";
  risk_band: "low" | "medium" | "high";
  budget_band: "tight" | "approved" | "ample";
  source_labels: string[];
};

export type Demo2AdmissionForecast = {
  source_type: "fixture_policy_forecast";
  estimated_tool_calls: number;
  estimated_runtime_seconds: number;
  max_workers: number;
};

export type Demo2AdmissionReason = {
  factor: "value" | "breadth" | "parallelism" | "deadline" | "risk" | "budget";
  label: string;
  detail: string;
};

export type Demo2RouteImpactChange = {
  change_kind: Demo2RouteImpactKind;
  aspect: Demo2RouteImpactAspect;
  label: string;
  before: string | null;
  after: string;
  detail: string | null;
};

export type Demo2RouteImpactPreview = {
  summary: string;
  changes: Demo2RouteImpactChange[];
  execution_status_before: "not_started";
  execution_status_after: "not_started";
  external_side_effect: "none";
};

export type Demo2RouteSelectionReceipt = {
  receipt_id: string;
  from_cockpit_version: number;
  to_cockpit_version: number;
  from_item_version: number;
  to_item_version: number;
  selected_mode: Demo2RouteMode;
  selection_source: Demo2SelectionSource;
  override_scope: Demo2OverrideScope | null;
  forecast: Demo2AdmissionForecast;
  changes: Demo2RouteImpactChange[];
  execution_status_before: "not_started";
  execution_status_after: "not_started";
  external_side_effect: "none";
  processing?: {
    path: "policy_engine";
    model_called: false;
    elapsed_ms: number;
  } | null;
  summary: string;
};

export type Demo2ProcessingSource = {
  path: Demo2ProcessingPath;
  kind: Demo2ProcessingKind;
  label: string;
  model_called: boolean;
  model: string | null;
  elapsed_ms: number | null;
  output_used: Demo2ProcessingOutput;
  fallback_reason: string | null;
};

export type Demo2WorkerRun = {
  worker_run_id: string;
  label: string;
  objective: string;
  role: string;
  status: Demo2WorkUnitStatus;
  source_document_ids: string[];
  trigger: "initial_plan" | "dynamic_replan" | "verification";
  artifact_version_id: string | null;
  depends_on: string[];
  error_code?: string | null;
  processing?: Demo2ProcessingSource | null;
};

export type Demo2ArtifactVersion = {
  artifact_version_id: string;
  artifact_id: string;
  version: number;
  title: string;
  kind: "worker_finding" | "verified_report_bundle";
  status: "draft" | "validated";
  source_document_ids: string[];
  content: Record<string, unknown>;
  created_at: string;
};

export type Demo2SwarmEvent = {
  execution_id?: string;
  sequence: number;
  event_type: string;
  status: Demo2ExecutionStatus;
  worker_run_id: string | null;
  artifact_version_id: string | null;
  message: string;
  details: Record<string, string>;
};

export type Demo2ReplanEvent = {
  event_id: string;
  kind: "dispatch" | "replan" | "wait" | "resume";
  summary: string;
  reason: string;
  occurred_at: string | null;
};

export type Demo2SharedArtifact = {
  artifact_id: string;
  label: string;
  status: "assembling" | "verifying" | "verified" | "blocked";
  summary: string;
  verified_unit_count: number;
  total_unit_count: number;
};

export type Demo2ExecutionReceipt = {
  receipt_id: string;
  execution_id: string;
  work_item_id: string;
  status: "completed" | "failed" | "cancelled";
  worker_run_ids: string[];
  artifact_version_ids: string[];
  summary: string;
  external_side_effect: "none";
  final_artifact_version_id: string | null;
  started_at: string;
  completed_at: string;
};

export type Demo2ExecutionSnapshot = {
  execution_id: string;
  status: Demo2ExecutionStatus;
  mode: "adaptive_swarm";
  owner_id?: string;
  work_item_id?: string;
  version?: number;
  source_document_ids?: string[];
  worker_runs: Demo2WorkerRun[];
  artifacts: Demo2ArtifactVersion[];
  events: Demo2SwarmEvent[];
  receipt: Demo2ExecutionReceipt | null;
  budget_max_workers?: number;
  budget_max_worker_runs?: number;
  last_event_sequence: number;
};

export type Demo2RouteProfile = {
  mode: Demo2RouteMode;
  label: string;
  summary: string;
  forecast: Demo2AdmissionForecast;
  tradeoff: string;
  candidate_only: boolean;
  impact_preview: Demo2RouteImpactPreview | null;
};

export type Demo2WorkItem = {
  work_item_id: string;
  owner_id: string;
  title: string;
  objective: string;
  business_status: "attention" | "ready" | "waiting";
  priority: number;
  facts: Demo2WorkItemFacts;
  allowed_modes: Demo2RouteMode[];
  route_profiles: Demo2RouteProfile[];
  admission_status: Demo2AdmissionStatus;
  recommendation: {
    mode: Demo2RouteMode;
    summary: string;
    reasons: Demo2AdmissionReason[];
    forecast: Demo2AdmissionForecast;
    policy_version: string;
  };
  selected_mode: Demo2RouteMode | null;
  selection_source: Demo2SelectionSource | null;
  override_scope: Demo2OverrideScope | null;
  execution_status: Demo2ExecutionStatus;
  execution_id?: string | null;
  execution?: Demo2ExecutionSnapshot | null;
  selection_receipt: Demo2RouteSelectionReceipt | null;
  selection_receipts: Demo2RouteSelectionReceipt[];
  version: number;
  last_event_sequence: number;
  last_event_type: "ADMISSION_EVALUATED" | "ROUTE_SELECTED";
};

export type Demo2CockpitSnapshot = {
  owner_id: string;
  backend: "memory";
  version: number;
  last_event_sequence: number;
  items: Demo2WorkItem[];
};

export type Demo2RouteSelectionResult = {
  cockpit_version: number;
  cockpit_last_event_sequence: number;
  item: Demo2WorkItem;
};

export type Demo2ExecutionStartResult = {
  cockpit_version?: number;
  cockpit_last_event_sequence?: number;
  item: Demo2WorkItem;
  execution: Demo2ExecutionSnapshot;
};

export type WorkCockpitProps = {
  snapshot: Demo2CockpitSnapshot | null;
  loading: boolean;
  saving: boolean;
  selectedId: string | null;
  draftMode: Demo2RouteMode | null;
  onSelect: (workItemId: string) => void;
  onRefresh: () => void;
  onStartExecution?: (workItemId: string) => void;
};

export type WorkCockpitDecisionPaneProps = {
  item: Demo2WorkItem | null;
  saving: boolean;
  error: string;
  draftMode: Demo2RouteMode | null;
  onDraftMode: (mode: Demo2RouteMode) => void;
  onConfirm: () => void;
  onRefresh: () => void;
  onStartExecution?: (workItemId: string) => void;
};
