export type Demo2RouteMode =
  | "tool_call"
  | "single_agent"
  | "fixed_workflow"
  | "adaptive_swarm";

export type Demo2AdmissionStatus = "recommended" | "route_selected";
export type Demo2SelectionSource = "admission" | "user_override";
export type Demo2OverrideScope = "this_run";
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
  summary: string;
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
  execution_status: "not_started";
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

export type WorkCockpitProps = {
  snapshot: Demo2CockpitSnapshot | null;
  loading: boolean;
  saving: boolean;
  selectedId: string | null;
  draftMode: Demo2RouteMode | null;
  onSelect: (workItemId: string) => void;
  onRefresh: () => void;
};

export type WorkCockpitDecisionPaneProps = {
  item: Demo2WorkItem | null;
  saving: boolean;
  error: string;
  draftMode: Demo2RouteMode | null;
  onDraftMode: (mode: Demo2RouteMode) => void;
  onConfirm: () => void;
  onRefresh: () => void;
};
