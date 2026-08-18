export type Demo2RouteMode =
  | "tool_call"
  | "single_agent"
  | "fixed_workflow"
  | "adaptive_swarm";

export type Demo2AdmissionStatus = "recommended" | "route_selected";
export type Demo2SelectionSource = "admission" | "user_override";
export type Demo2OverrideScope = "this_run";

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

export type Demo2RouteProfile = {
  mode: Demo2RouteMode;
  label: string;
  summary: string;
  forecast: Demo2AdmissionForecast;
  tradeoff: string;
  candidate_only: boolean;
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
