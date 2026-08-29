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

type NarrativeConflict = {
  conflict_id: string;
  kind: "incomplete_coverage" | "outcome_count_mismatch" | "priority_mismatch" | "unsupported_solution_claim" | "redundant_completed_work" | "outcome_revision_mismatch";
  narrative_path: string;
  narrative_excerpt: string;
  outcome_path: string;
  expected: string;
  observed: string;
  severity: "warning" | "error";
};

type NarrativeReconciliation = {
  reconciliation_id: string;
  round_number: number;
  status: "consistent" | "partial" | "contradictory" | "stale" | "not_applicable";
  authority: "deterministic_outcome" | "model_only";
  model_disposition: "adopted" | "supplemental" | "rejected";
  outcome_revision: string | null;
  effect_receipt_id: string | null;
  model_returned: boolean;
  comparable_claim_count: number;
  conflicts: NarrativeConflict[];
  message: string;
  checked_at: string;
  external_action: "none";
};

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
  narrative_reconciliation: NarrativeReconciliation | null;
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

type ArtifactSelfTest = {
  instruction: string;
  expected_files: string[];
  commands: string[];
  expected_checks: string[];
  failure_signals: string[];
  test_manifest_file: string | null;
  test_manifest_matches_collected: boolean | null;
  test_suites: ArtifactTestSuite[];
};

type ArtifactTestSuite = {
  suite_id: string;
  label: string;
  test_files: string[];
  test_count: number;
  test_ids: string[];
};

type BusinessGate = {
  gate_id: string;
  label: string;
  passed: boolean;
  numerator: number;
  denominator: number;
  operator: ">=" | "==" | "<=";
  threshold: number;
  actual: number;
  unit: "percent" | "count";
  formula: string;
  source_rule: string;
  result: string;
};

type BusinessMetric = {
  metric_id: string;
  label: string;
  numerator: number;
  denominator: number;
  value: number;
  unit: "percent" | "count";
  formula: string;
  source_note: string;
};

type BusinessRecord = {
  record_id: string;
  title: string;
  module: string;
  priority: string;
  owner: string;
  configuration_status: string;
  test_status: string;
  test_reason: string;
  total_cases: number;
  passed_cases: number;
  compatibility_issue_count: number;
  compatibility_issue_environments: string[];
  rules_hit: string[];
  base_risk_level: "none" | "minor" | "major" | "severe";
  compatibility_risk_level: "none" | "minor" | "severe";
  final_risk_level: "none" | "minor" | "major" | "severe";
  affected_gate_ids: string[];
  source_locations: string[];
  remediation_action: string;
  exit_condition: string;
};

type BusinessGateOutcome = {
  outcome_id: string;
  outcome_kind: "release_readiness" | "legal_delegation_review";
  status: "passed" | "failed" | "invalid";
  decision: string;
  summary: string;
  total_gate_count: number;
  failed_gate_count: number;
  gates: BusinessGate[];
  auxiliary_metrics: BusinessMetric[];
  records: BusinessRecord[];
  external_action: "none";
};

type LegalRuleAssessment = {
  assessment_id: string;
  rule_id: string;
  rule_name: string;
  rule_level: "high" | "medium" | "low";
  status: "triggered" | "not_triggered" | "unverifiable";
  source_locator: string;
  excerpt: string;
  fact: string;
  judgment: string;
  reason: string;
  owner: string;
  remediation_action: string;
  exit_condition: string;
};

type LegalDocumentReview = {
  document_id: string;
  document_name: string;
  source_file_ref: string;
  highest_triggered_level: "none" | "low" | "medium" | "high";
  triggered_count: number;
  unverifiable_count: number;
  signing_evidence_status: "present" | "absent" | "unverifiable";
  summary: string;
  assessments: LegalRuleAssessment[];
};

type LegalReviewOutcome = {
  outcome_id: string;
  status: "cleared" | "review_required" | "invalid";
  decision: string;
  summary: string;
  document_count: number;
  rule_count: number;
  assessment_count: number;
  high_risk_document_count: number;
  medium_risk_document_count: number;
  low_risk_document_count: number;
  no_trigger_document_count: number;
  critical_unverifiable_count: number;
  signing_evidence_count: number;
  human_review_required: boolean;
  signing_status: "evidence_present" | "evidence_incomplete" | "invalid";
  documents: LegalDocumentReview[];
  external_action: "none";
};

type CandidateConditionAssessment = {
  assessment_id: string;
  role_id: "merchant_bd" | "text_evaluation";
  candidate_id: string;
  candidate_name: string;
  condition_id: string;
  condition_type: "responsibility" | "default_threshold" | "required" | "preferred" | "bonus";
  condition_label: string;
  jd_source_file_ref: string;
  jd_locator: string;
  jd_excerpt: string;
  resume_source_file_ref: string;
  resume_locator: string;
  resume_excerpt: string;
  resume_evidence_present: boolean;
  status: "met" | "not_met" | "unverifiable" | "human_exception_required";
  fact: string;
  judgment: string;
  reason: string;
  owner: string;
  review_action: string;
  exit_condition: string;
};

type CandidateRoleReview = {
  review_id: string;
  role_id: "merchant_bd" | "text_evaluation";
  role_name: string;
  jd_source_file_ref: string;
  candidate_id: string;
  candidate_name: string;
  resume_source_file_ref: string;
  recommendation: "recommended_for_human_review" | "explicit_hard_gap" | "insufficient_evidence" | "exception_review_required";
  condition_count: number;
  met_count: number;
  not_met_count: number;
  unverifiable_count: number;
  human_exception_count: number;
  summary: string;
  assessments: CandidateConditionAssessment[];
};

type CandidateReviewOutcome = {
  outcome_id: string;
  status: "review_required" | "invalid";
  decision: string;
  summary: string;
  role_count: number;
  candidate_count: number;
  review_count: number;
  assessment_count: number;
  met_count: number;
  not_met_count: number;
  unverifiable_count: number;
  human_exception_count: number;
  recommended_for_human_review_count: number;
  explicit_hard_gap_count: number;
  insufficient_evidence_count: number;
  exception_review_required_count: number;
  human_review_required: true;
  fairness_evaluated: false;
  reviews: CandidateRoleReview[];
  external_action: "none";
};

type FinanceCandidateSource = {
  period_id: "2025_h1" | "2025_h2" | "2026";
  period_label: string;
  source_file_ref: string;
  file_name: string;
  sheet_name: string;
  row_number: number;
  locator: string;
  direction: "借";
  ending_balance: string;
};

type FinanceCandidate = {
  candidate_id: string;
  key: string;
  subject: string;
  customer: string;
  sources: FinanceCandidateSource[];
  review_action: string;
  exit_condition: string;
};

type FinanceReviewOutcome = {
  outcome_id: string;
  status: "review_required" | "invalid";
  decision: string;
  summary: string;
  period_ids: ("2025_h1" | "2025_h2" | "2026")[];
  unpaid_count: number;
  unpaid_total: string;
  unreceived_count: number;
  unreceived_total: string;
  candidate_count: number;
  candidates: FinanceCandidate[];
  method: string;
  limitations: string[];
  human_review_required: true;
  original_inputs_modified: false;
  external_action: "none";
};

type OutboundRuleParameter = {
  name: string;
  value: string;
  unit: string | null;
};

type OutboundRule = {
  rule_id: string;
  group: "TIME" | "FREQ" | "RECORD" | "IDENTITY" | "THIRD_PARTY" | "PROHIBIT" | "CONNECT" | "PTP" | "SOFT" | "HARD" | "DISPUTE" | "INVALID" | "TERMINAL" | "PAYMENT" | "REDIAL";
  source_file_ref: string;
  locator: string;
  excerpt: string;
  parameters: OutboundRuleParameter[];
  expected_relation: string;
  expected_action: string;
  coverage_state: "covered" | "unsupported" | "conflict";
  mapped_node_ids: string[];
  mapped_edge_ids: string[];
  mapped_guard_ids: string[];
  mapped_terminal_ids: string[];
};

type OutboundNode = {
  node_id: string;
  label: string;
  kind: "start" | "gate" | "decision" | "action" | "terminal";
  source_rule_ids: string[];
  future_action: boolean;
};

type OutboundEdge = {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  label: string;
  guard_ids: string[];
  source_rule_ids: string[];
  future_action: boolean;
};

type OutboundGuard = {
  guard_id: string;
  label: string;
  parameters: OutboundRuleParameter[];
  source_rule_ids: string[];
};

type OutboundTerminal = {
  terminal_id: string;
  node_id: string;
  label: string;
  source_rule_ids: string[];
  source_listed: boolean;
};

type OutboundGraphIntegrity = {
  unique_start: boolean;
  unique_ids: boolean;
  no_dangling_edges: boolean;
  all_nodes_reachable: boolean;
  all_terminals_reachable: boolean;
  every_nonterminal_has_outgoing: boolean;
  every_node_can_reach_terminal: boolean;
  critical_order_valid: boolean;
  third_party_boundary_valid: boolean;
  all_rules_mapped: boolean;
};

type OutboundFlowOutcome = {
  outcome_id: string;
  status: "approval_required" | "invalid";
  decision: string;
  summary: string;
  source_rule_group_count: number;
  atomic_requirement_count: number;
  covered_count: number;
  unsupported_count: number;
  conflict_count: number;
  node_count: number;
  edge_count: number;
  guard_count: number;
  terminal_count: number;
  reachable_terminal_count: number;
  parameters: OutboundRuleParameter[];
  rules: OutboundRule[];
  nodes: OutboundNode[];
  edges: OutboundEdge[];
  guards: OutboundGuard[];
  terminals: OutboundTerminal[];
  graph_integrity: OutboundGraphIntegrity;
  human_approval_required: true;
  legal_opinion: false;
  original_inputs_modified: false;
  external_action: "none";
};

type CustomerSegmentationRule = {
  rule_id: string;
  category: "cleaning" | "classification" | "priority" | "exclusion" | "report";
  source_file_ref: string;
  locator: string;
  excerpt: string;
  parameters: string[];
};

type CustomerSampleDecision = {
  sample_id: string;
  source_file_ref: string;
  source_row: number;
  source_locator: string;
  industry: string;
  company_size: string;
  respondent_role: string;
  raw_scores: Record<string, string>;
  cleaned_scores: Record<string, number>;
  transformations: string[];
  matched_profiles: string[];
  priority_applied: boolean;
  final_label: string | null;
  exclusion_reason: "exact_duplicate" | "unclassified" | null;
  duplicate_of: string | null;
  rule_refs: string[];
};

type CustomerSegmentationOutcome = {
  outcome_id: string;
  status: "sales_review_required" | "invalid";
  decision: string;
  summary: string;
  source_row_count: number;
  unique_payload_count: number;
  duplicate_count: number;
  classified_count: number;
  unclassified_count: number;
  excluded_count: number;
  profile_counts: Record<string, number>;
  parameters: {
    parsing_encoding: "utf-8-sig" | "utf-8" | "gb18030";
    missing_score_default: number;
    chinese_number_domain: string;
    profile_thresholds: Record<string, number>;
    profile_priority: string[];
    duplicate_policy: "exact_non_id_payload";
  };
  rules: CustomerSegmentationRule[];
  samples: CustomerSampleDecision[];
  duplicate_policy_assumption: "exact_non_id_payload";
  policy_assumption_review_required: true;
  priority_witness_count: number;
  strategy_evidence_status: "no_approved_strategy_source";
  human_review_required: true;
  original_inputs_modified: false;
  external_action: "none";
};

type SREObservation = {
  observation_id: string;
  category: string;
  statement: string;
  source_file_ref: string;
  locator: string;
  excerpt: string;
  fields: Record<string, string>;
  status: "observed" | "unclassified";
};

type SRESourceConflict = {
  conflict_id: string;
  title: string;
  statement: string;
  side_a_observation_ids: string[];
  side_b_observation_ids: string[];
  locators: string[];
  impact: string;
  status: "open" | "resolved";
};

type SREHypothesis = {
  hypothesis_id: string;
  statement: string;
  confidence: "low" | "medium" | "high";
  supporting_observation_ids: string[];
  supporting_locators: string[];
  counter_evidence_ids: string[];
  counter_evidence_locators: string[];
  limitations: string[];
};

type SREActionProposal = {
  proposal_id: string;
  kind: "read_only_preflight" | "write_change" | "business_mitigation";
  title: string;
  risk_level: "low" | "medium" | "high";
  command_template: string | null;
  action_text: string | null;
  target_status: "unresolved" | "not_applicable";
  target_rationale: string;
  preconditions: string[];
  rollback: string;
  verify_after: string[];
  official_reference: string | null;
  approval_required: true;
  executed: false;
  source_observation_ids: string[];
};

type SREDiagnosisOutcome = {
  outcome_id: string;
  status: "incident_review_required" | "invalid";
  decision: string;
  summary: string;
  source_line_count: number;
  cluster_facts: Record<string, unknown>;
  node_facts: Record<string, unknown>;
  metric_facts: Record<string, unknown>;
  timeline: string[];
  observation_count: number;
  conflict_count: number;
  hypothesis_count: number;
  proposal_count: number;
  business_mitigation_count: number;
  unclassified_count: number;
  observations: SREObservation[];
  source_conflicts: SRESourceConflict[];
  hypotheses: SREHypothesis[];
  action_proposals: SREActionProposal[];
  business_mitigations: SREActionProposal[];
  resolved_target_count: 0;
  human_review_required: true;
  original_inputs_modified: false;
  external_action: "none";
};

type UXRule = {
  rule_id: string;
  kind: "severity" | "frequency" | "priority" | "disposition";
  name: string;
  locator: string;
  excerpt: string;
  parameters: Record<string, string>;
};

type UXSpecElement = {
  spec_id: string;
  page_name: string;
  page_order: number;
  element_name: string;
  element_order: number;
  requirement: string;
  locator: string;
};

type UXMappingDecision = {
  mapping_id: string;
  page_name: string;
  operation: string;
  status: "controlled_adapter_assumption" | "unmapped";
  spec_id: string | null;
  element_name: string | null;
  candidate_spec_ids: string[];
  mapping_basis: string;
  review_required: true;
};

type UXRowDecision = {
  row_number: number;
  locator: string;
  page_name: string;
  page_path: string;
  operation: string;
  operation_result: string;
  pain_type: string;
  failure_reason: string;
  misclick_count: number;
  exit_node: string;
  retry_count: number;
  status: "included" | "excluded" | "manual_review";
  group_id: string | null;
  mapping_id: string | null;
  mapping_status: "controlled_adapter_assumption" | "unmapped" | "not_applicable";
  duplicate_group_id: string | null;
  duplicate_ordinal: number;
  reason: string;
  data_quality_flags: string[];
};

type UXGroupRuleRef = {
  role: "severity" | "frequency" | "priority";
  rule_id: string;
  locator: string;
  application: "applied" | "conflict_side";
};

type UXGroup = {
  group_id: string;
  page_name: string;
  page_path: string;
  operation: string;
  spec_id: string;
  element_name: string;
  pain_type: string;
  severity: "严重" | "中等" | "轻微";
  scenario_count: number;
  denominator: number;
  ratio: string;
  frequency: "高频" | "中频" | "低频" | "边界待确认";
  priority: "P0" | "P1" | "P2" | "P3" | "P4" | null;
  disposition: string;
  spec_requirement: string;
  contributing_row_locators: string[];
  mapping_status: "controlled_adapter_assumption";
  mapping_basis: string;
  rule_refs: UXGroupRuleRef[];
  data_quality_flags: string[];
  suggestion_status: "no_approved_solution_source";
  suggestion_template: string;
};

type UXRuleConflict = {
  conflict_id: string;
  title: string;
  locators: string[];
  statement: string;
  impact: string;
  status: "open" | "resolved";
};

type UXPrioritizationOutcome = {
  outcome_id: string;
  status: "prioritization_review_required" | "invalid";
  decision: string;
  summary: string;
  source_row_count: number;
  analyzed_row_count: number;
  included_pain_row_count: number;
  excluded_no_pain_count: number;
  success_with_pain_count: number;
  group_count: number;
  priority_counts: Record<string, number>;
  duplicate_group_count: number;
  duplicate_extra_count: number;
  unmapped_count: number;
  uncovered_spec_count: number;
  rules: UXRule[];
  specs: UXSpecElement[];
  mappings: UXMappingDecision[];
  groups: UXGroup[];
  row_decisions: UXRowDecision[];
  rule_conflicts: UXRuleConflict[];
  suggestion_status: "no_approved_solution_source";
  human_review_required: true;
  original_inputs_modified: false;
  external_action: "none";
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
  deliverable_type: string | null;
  key_outputs: string[];
  key_outputs_label: string | null;
  review_guidance: string | null;
  execution_summary: string | null;
  self_test: ArtifactSelfTest | null;
  business_gate_outcome: BusinessGateOutcome | null;
  legal_review_outcome: LegalReviewOutcome | null;
  candidate_review_outcome: CandidateReviewOutcome | null;
  finance_review_outcome: FinanceReviewOutcome | null;
  outbound_flow_outcome: OutboundFlowOutcome | null;
  customer_segmentation_outcome: CustomerSegmentationOutcome | null;
  sre_diagnosis_outcome: SREDiagnosisOutcome | null;
  ux_prioritization_outcome: UXPrioritizationOutcome | null;
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
  business_gate_outcome: BusinessGateOutcome | null;
  legal_review_outcome: LegalReviewOutcome | null;
  candidate_review_outcome: CandidateReviewOutcome | null;
  finance_review_outcome: FinanceReviewOutcome | null;
  outbound_flow_outcome: OutboundFlowOutcome | null;
  customer_segmentation_outcome: CustomerSegmentationOutcome | null;
  sre_diagnosis_outcome: SREDiagnosisOutcome | null;
  ux_prioritization_outcome: UXPrioritizationOutcome | null;
  created_at: string;
  external_action: "none";
};

type ArtifactCheckSummary = {
  passed: number;
  total: number;
  projected: number;
  shared: boolean;
  sameChecklist: boolean;
};

function summarizeArtifactChecks(artifacts: WorkspaceArtifact[]): ArtifactCheckSummary {
  const checksById = new Map<string, boolean>();
  const checklistKeys = new Set<string>();
  let projected = 0;
  for (const artifact of artifacts) {
    checklistKeys.add(artifactChecklistKey(artifact));
    for (const check of artifact.checks) {
      projected += 1;
      checksById.set(check.check_id, (checksById.get(check.check_id) ?? true) && check.passed);
    }
  }
  return {
    passed: [...checksById.values()].filter(Boolean).length,
    total: checksById.size,
    projected,
    shared: projected > checksById.size,
    sameChecklist: artifacts.length > 1 && checklistKeys.size === 1 && !checklistKeys.has(""),
  };
}

function artifactChecklistKey(artifact: WorkspaceArtifact): string {
  return [...new Set(artifact.checks.map((check) => check.check_id))].sort().join("\u0000");
}

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
  narrative_reconciliation: NarrativeReconciliation | null;
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
  "analysis_partial_candidate",
  "analysis_recovery_required",
  "narrative_reconciliation_completed",
  "narrative_reconciliation_rejected",
  "evidence_disambiguation_required",
  "partial_artifact_saved",
  "decision_requested",
  "decision_recorded",
  "branch_resumed_from_checkpoint",
  "deterministic_office_tool_started",
  "run_workspace_artifact_written",
  "deterministic_verification_completed",
  "scenario_effect_failed",
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
function asStringRecord(value: unknown): Record<string, string> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === "string"));
}
function asNumberRecord(value: unknown): Record<string, number> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, number] => typeof entry[1] === "number" && Number.isFinite(entry[1])));
}

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

function normalizeNarrativeConflict(value: unknown): NarrativeConflict | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const conflictId = asText(raw.conflict_id);
  const kind = asText(raw.kind);
  const severity = asText(raw.severity);
  const narrativeExcerpt = asText(raw.narrative_excerpt);
  if (
    !conflictId
    || !["incomplete_coverage", "outcome_count_mismatch", "priority_mismatch", "unsupported_solution_claim", "redundant_completed_work", "outcome_revision_mismatch"].includes(kind)
    || !["warning", "error"].includes(severity)
    || !narrativeExcerpt
  ) return null;
  return {
    conflict_id: conflictId,
    kind: kind as NarrativeConflict["kind"],
    narrative_path: asText(raw.narrative_path),
    narrative_excerpt: narrativeExcerpt,
    outcome_path: asText(raw.outcome_path),
    expected: asText(raw.expected),
    observed: asText(raw.observed),
    severity: severity as NarrativeConflict["severity"],
  };
}

function normalizeNarrativeReconciliation(value: unknown): NarrativeReconciliation | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const reconciliationId = asText(raw.reconciliation_id);
  const status = asText(raw.status);
  const authority = asText(raw.authority);
  const disposition = asText(raw.model_disposition);
  if (
    !reconciliationId
    || !["consistent", "partial", "contradictory", "stale", "not_applicable"].includes(status)
    || !["deterministic_outcome", "model_only"].includes(authority)
    || !["adopted", "supplemental", "rejected"].includes(disposition)
  ) return null;
  return {
    reconciliation_id: reconciliationId,
    round_number: asNumber(raw.round_number, 1),
    status: status as NarrativeReconciliation["status"],
    authority: authority as NarrativeReconciliation["authority"],
    model_disposition: disposition as NarrativeReconciliation["model_disposition"],
    outcome_revision: asText(raw.outcome_revision) || null,
    effect_receipt_id: asText(raw.effect_receipt_id) || null,
    model_returned: raw.model_returned === true,
    comparable_claim_count: asNumber(raw.comparable_claim_count),
    conflicts: Array.isArray(raw.conflicts)
      ? raw.conflicts.map(normalizeNarrativeConflict).filter((item): item is NarrativeConflict => item !== null)
      : [],
    message: asText(raw.message),
    checked_at: asText(raw.checked_at),
    external_action: "none",
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
    narrative_reconciliation: normalizeNarrativeReconciliation(raw.narrative_reconciliation),
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
    analysis_partial_candidate: "模型候选说明仍待事实对账",
    analysis_recovery_required: "需要缩小范围后继续",
    narrative_reconciliation_completed: "模型说明已与服务端事实对账",
    narrative_reconciliation_rejected: "模型说明与服务端事实冲突，未采用",
    evidence_disambiguation_required: "需要你选择原文位置",
    partial_artifact_saved: "已保留可核对成果",
    decision_requested: "需要人工决定处理口径",
    decision_recorded: "人工决定已写入回执",
    branch_resumed_from_checkpoint: "仅恢复受影响分支",
    deterministic_office_tool_started: "确定性办公工具开始处理",
    run_workspace_artifact_written: "真实成果文件已生成",
    deterministic_verification_completed: "成果已通过确定性检查",
    scenario_effect_failed: "隔离成果构建或验证未完成",
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
  const tone = event.event_name === "harness_failed" || event.event_name === "plan_validation_rejected" || event.event_name === "analysis_structure_rejected" || event.event_name === "analysis_validation_rejected" || event.event_name === "analysis_recovery_required" || event.event_name === "evidence_disambiguation_required" || event.event_name === "scenario_effect_failed" || event.event_name === "scenario_effect_bounded" || event.event_name === "narrative_reconciliation_rejected" || event.event_name.includes("stopped") ? "warning"
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

function normalizeArtifactTestSuite(value: unknown): ArtifactTestSuite | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const suiteId = asText(raw.suite_id);
  const label = asText(raw.label);
  const testFiles = asStrings(raw.test_files);
  const testIds = asStrings(raw.test_ids);
  const testCount = asNumber(raw.test_count);
  if (!suiteId || !label || testFiles.length === 0 || testIds.length === 0 || testCount !== testIds.length) return null;
  return { suite_id: suiteId, label, test_files: testFiles, test_count: testCount, test_ids: testIds };
}

function normalizeBusinessGate(value: unknown): BusinessGate | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const gateId = asText(raw.gate_id);
  const operator = asText(raw.operator);
  const unit = asText(raw.unit);
  const denominator = asNumber(raw.denominator);
  if (!gateId || typeof raw.passed !== "boolean" || ![">=", "==", "<="].includes(operator) || !["percent", "count"].includes(unit) || denominator <= 0) return null;
  return {
    gate_id: gateId,
    label: asText(raw.label),
    passed: raw.passed,
    numerator: asNumber(raw.numerator),
    denominator,
    operator: operator as BusinessGate["operator"],
    threshold: asNumber(raw.threshold),
    actual: asNumber(raw.actual),
    unit: unit as BusinessGate["unit"],
    formula: asText(raw.formula),
    source_rule: asText(raw.source_rule),
    result: asText(raw.result),
  };
}

function normalizeBusinessMetric(value: unknown): BusinessMetric | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const metricId = asText(raw.metric_id);
  const unit = asText(raw.unit);
  const denominator = asNumber(raw.denominator);
  if (!metricId || !["percent", "count"].includes(unit) || denominator <= 0) return null;
  return {
    metric_id: metricId,
    label: asText(raw.label),
    numerator: asNumber(raw.numerator),
    denominator,
    value: asNumber(raw.value),
    unit: unit as BusinessMetric["unit"],
    formula: asText(raw.formula),
    source_note: asText(raw.source_note),
  };
}

function normalizeBusinessRecord(value: unknown): BusinessRecord | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const recordId = asText(raw.record_id);
  const risk = asText(raw.final_risk_level);
  const baseRisk = asText(raw.base_risk_level);
  const compatibilityRisk = asText(raw.compatibility_risk_level);
  if (!recordId || !["none", "minor", "major", "severe"].includes(risk) || !["none", "minor", "major", "severe"].includes(baseRisk) || !["none", "minor", "severe"].includes(compatibilityRisk)) return null;
  return {
    record_id: recordId,
    title: asText(raw.title),
    module: asText(raw.module),
    priority: asText(raw.priority),
    owner: asText(raw.owner),
    configuration_status: asText(raw.configuration_status),
    test_status: asText(raw.test_status),
    test_reason: asText(raw.test_reason),
    total_cases: asNumber(raw.total_cases),
    passed_cases: asNumber(raw.passed_cases),
    compatibility_issue_count: asNumber(raw.compatibility_issue_count),
    compatibility_issue_environments: asStrings(raw.compatibility_issue_environments),
    rules_hit: asStrings(raw.rules_hit),
    base_risk_level: baseRisk as BusinessRecord["base_risk_level"],
    compatibility_risk_level: compatibilityRisk as BusinessRecord["compatibility_risk_level"],
    final_risk_level: risk as BusinessRecord["final_risk_level"],
    affected_gate_ids: asStrings(raw.affected_gate_ids),
    source_locations: asStrings(raw.source_locations),
    remediation_action: asText(raw.remediation_action),
    exit_condition: asText(raw.exit_condition),
  };
}

function normalizeLegalRuleAssessment(value: unknown): LegalRuleAssessment | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const assessmentId = asText(raw.assessment_id);
  const ruleId = asText(raw.rule_id);
  const ruleLevel = asText(raw.rule_level);
  const status = asText(raw.status);
  if (
    !assessmentId
    || !/^[RML][0-9]{2}$/.test(ruleId)
    || !["high", "medium", "low"].includes(ruleLevel)
    || !["triggered", "not_triggered", "unverifiable"].includes(status)
  ) return null;
  return {
    assessment_id: assessmentId,
    rule_id: ruleId,
    rule_name: asText(raw.rule_name),
    rule_level: ruleLevel as LegalRuleAssessment["rule_level"],
    status: status as LegalRuleAssessment["status"],
    source_locator: asText(raw.source_locator),
    excerpt: asText(raw.excerpt),
    fact: asText(raw.fact),
    judgment: asText(raw.judgment),
    reason: asText(raw.reason),
    owner: asText(raw.owner),
    remediation_action: asText(raw.remediation_action),
    exit_condition: asText(raw.exit_condition),
  };
}

function normalizeLegalDocumentReview(value: unknown): LegalDocumentReview | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const documentId = asText(raw.document_id);
  const highestLevel = asText(raw.highest_triggered_level);
  const signingStatus = asText(raw.signing_evidence_status);
  const assessments = Array.isArray(raw.assessments)
    ? raw.assessments.map(normalizeLegalRuleAssessment).filter((item): item is LegalRuleAssessment => item !== null)
    : [];
  if (
    !/^DOC-[0-9]{2}$/.test(documentId)
    || !["none", "low", "medium", "high"].includes(highestLevel)
    || !["present", "absent", "unverifiable"].includes(signingStatus)
    || assessments.length !== 21
  ) return null;
  return {
    document_id: documentId,
    document_name: asText(raw.document_name),
    source_file_ref: asText(raw.source_file_ref),
    highest_triggered_level: highestLevel as LegalDocumentReview["highest_triggered_level"],
    triggered_count: asNumber(raw.triggered_count),
    unverifiable_count: asNumber(raw.unverifiable_count),
    signing_evidence_status: signingStatus as LegalDocumentReview["signing_evidence_status"],
    summary: asText(raw.summary),
    assessments,
  };
}

function normalizeLegalReviewOutcome(value: unknown): LegalReviewOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const outcomeId = asText(raw.outcome_id);
  const status = asText(raw.status);
  const signingStatus = asText(raw.signing_status);
  const documents = Array.isArray(raw.documents)
    ? raw.documents.map(normalizeLegalDocumentReview).filter((item): item is LegalDocumentReview => item !== null)
    : [];
  if (
    !outcomeId
    || !["cleared", "review_required", "invalid"].includes(status)
    || !["evidence_present", "evidence_incomplete", "invalid"].includes(signingStatus)
    || documents.length !== 6
  ) return null;
  return {
    outcome_id: outcomeId,
    status: status as LegalReviewOutcome["status"],
    decision: asText(raw.decision),
    summary: asText(raw.summary),
    document_count: asNumber(raw.document_count),
    rule_count: asNumber(raw.rule_count),
    assessment_count: asNumber(raw.assessment_count),
    high_risk_document_count: asNumber(raw.high_risk_document_count),
    medium_risk_document_count: asNumber(raw.medium_risk_document_count),
    low_risk_document_count: asNumber(raw.low_risk_document_count),
    no_trigger_document_count: asNumber(raw.no_trigger_document_count),
    critical_unverifiable_count: asNumber(raw.critical_unverifiable_count),
    signing_evidence_count: asNumber(raw.signing_evidence_count),
    human_review_required: raw.human_review_required === true,
    signing_status: signingStatus as LegalReviewOutcome["signing_status"],
    documents,
    external_action: "none",
  };
}

function normalizeCandidateConditionAssessment(value: unknown): CandidateConditionAssessment | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const assessmentId = asText(raw.assessment_id);
  const roleId = asText(raw.role_id);
  const candidateId = asText(raw.candidate_id);
  const conditionType = asText(raw.condition_type);
  const status = asText(raw.status);
  if (
    !assessmentId
    || !["merchant_bd", "text_evaluation"].includes(roleId)
    || !/^CAND-[0-9]{2}$/.test(candidateId)
    || !["responsibility", "default_threshold", "required", "preferred", "bonus"].includes(conditionType)
    || !["met", "not_met", "unverifiable", "human_exception_required"].includes(status)
  ) return null;
  return {
    assessment_id: assessmentId,
    role_id: roleId as CandidateConditionAssessment["role_id"],
    candidate_id: candidateId,
    candidate_name: asText(raw.candidate_name),
    condition_id: asText(raw.condition_id),
    condition_type: conditionType as CandidateConditionAssessment["condition_type"],
    condition_label: asText(raw.condition_label),
    jd_source_file_ref: asText(raw.jd_source_file_ref),
    jd_locator: asText(raw.jd_locator),
    jd_excerpt: asText(raw.jd_excerpt),
    resume_source_file_ref: asText(raw.resume_source_file_ref),
    resume_locator: asText(raw.resume_locator),
    resume_excerpt: asText(raw.resume_excerpt),
    resume_evidence_present: raw.resume_evidence_present === true,
    status: status as CandidateConditionAssessment["status"],
    fact: asText(raw.fact),
    judgment: asText(raw.judgment),
    reason: asText(raw.reason),
    owner: asText(raw.owner),
    review_action: asText(raw.review_action),
    exit_condition: asText(raw.exit_condition),
  };
}

function normalizeCandidateRoleReview(value: unknown): CandidateRoleReview | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const reviewId = asText(raw.review_id);
  const roleId = asText(raw.role_id);
  const candidateId = asText(raw.candidate_id);
  const recommendation = asText(raw.recommendation);
  const assessments = Array.isArray(raw.assessments)
    ? raw.assessments.map(normalizeCandidateConditionAssessment).filter((item): item is CandidateConditionAssessment => item !== null)
    : [];
  const conditionCount = asNumber(raw.condition_count);
  if (
    !reviewId
    || !["merchant_bd", "text_evaluation"].includes(roleId)
    || !/^CAND-[0-9]{2}$/.test(candidateId)
    || !["recommended_for_human_review", "explicit_hard_gap", "insufficient_evidence", "exception_review_required"].includes(recommendation)
    || assessments.length !== conditionCount
  ) return null;
  return {
    review_id: reviewId,
    role_id: roleId as CandidateRoleReview["role_id"],
    role_name: asText(raw.role_name),
    jd_source_file_ref: asText(raw.jd_source_file_ref),
    candidate_id: candidateId,
    candidate_name: asText(raw.candidate_name),
    resume_source_file_ref: asText(raw.resume_source_file_ref),
    recommendation: recommendation as CandidateRoleReview["recommendation"],
    condition_count: conditionCount,
    met_count: asNumber(raw.met_count),
    not_met_count: asNumber(raw.not_met_count),
    unverifiable_count: asNumber(raw.unverifiable_count),
    human_exception_count: asNumber(raw.human_exception_count),
    summary: asText(raw.summary),
    assessments,
  };
}

function normalizeCandidateReviewOutcome(value: unknown): CandidateReviewOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const outcomeId = asText(raw.outcome_id);
  const status = asText(raw.status);
  const reviews = Array.isArray(raw.reviews)
    ? raw.reviews.map(normalizeCandidateRoleReview).filter((item): item is CandidateRoleReview => item !== null)
    : [];
  const reviewCount = asNumber(raw.review_count);
  const assessmentCount = asNumber(raw.assessment_count);
  if (
    !outcomeId
    || !["review_required", "invalid"].includes(status)
    || reviews.length !== reviewCount
    || reviews.reduce((sum, review) => sum + review.condition_count, 0) !== assessmentCount
    || raw.human_review_required !== true
    || raw.fairness_evaluated !== false
  ) return null;
  return {
    outcome_id: outcomeId,
    status: status as CandidateReviewOutcome["status"],
    decision: asText(raw.decision),
    summary: asText(raw.summary),
    role_count: asNumber(raw.role_count),
    candidate_count: asNumber(raw.candidate_count),
    review_count: reviewCount,
    assessment_count: assessmentCount,
    met_count: asNumber(raw.met_count),
    not_met_count: asNumber(raw.not_met_count),
    unverifiable_count: asNumber(raw.unverifiable_count),
    human_exception_count: asNumber(raw.human_exception_count),
    recommended_for_human_review_count: asNumber(raw.recommended_for_human_review_count),
    explicit_hard_gap_count: asNumber(raw.explicit_hard_gap_count),
    insufficient_evidence_count: asNumber(raw.insufficient_evidence_count),
    exception_review_required_count: asNumber(raw.exception_review_required_count),
    human_review_required: true,
    fairness_evaluated: false,
    reviews,
    external_action: "none",
  };
}

function normalizeFinanceCandidateSource(value: unknown): FinanceCandidateSource | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const periodId = asText(raw.period_id);
  const sourceFileRef = asText(raw.source_file_ref);
  const locator = asText(raw.locator);
  if (!(["2025_h1", "2025_h2", "2026"] as string[]).includes(periodId) || !sourceFileRef || !locator) return null;
  return {
    period_id: periodId as FinanceCandidateSource["period_id"],
    period_label: asText(raw.period_label),
    source_file_ref: sourceFileRef,
    file_name: asText(raw.file_name),
    sheet_name: asText(raw.sheet_name),
    row_number: asNumber(raw.row_number),
    locator,
    direction: "借",
    ending_balance: asText(raw.ending_balance),
  };
}

function normalizeFinanceCandidate(value: unknown): FinanceCandidate | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const candidateId = asText(raw.candidate_id);
  const sources = Array.isArray(raw.sources)
    ? raw.sources.map(normalizeFinanceCandidateSource).filter((item): item is FinanceCandidateSource => item !== null)
    : [];
  if (!candidateId || sources.length !== 3) return null;
  return {
    candidate_id: candidateId,
    key: asText(raw.key),
    subject: asText(raw.subject),
    customer: asText(raw.customer),
    sources,
    review_action: asText(raw.review_action),
    exit_condition: asText(raw.exit_condition),
  };
}

function normalizeFinanceReviewOutcome(value: unknown): FinanceReviewOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  const periodIds = asStrings(raw.period_ids).filter((item) => (["2025_h1", "2025_h2", "2026"] as string[]).includes(item));
  const candidates = Array.isArray(raw.candidates)
    ? raw.candidates.map(normalizeFinanceCandidate).filter((item): item is FinanceCandidate => item !== null)
    : [];
  const candidateCount = asNumber(raw.candidate_count);
  if (
    !asText(raw.outcome_id)
    || !["review_required", "invalid"].includes(status)
    || periodIds.length !== 3
    || new Set(periodIds).size !== 3
    || candidates.length !== candidateCount
    || raw.human_review_required !== true
    || raw.original_inputs_modified !== false
  ) return null;
  return {
    outcome_id: asText(raw.outcome_id),
    status: status as FinanceReviewOutcome["status"],
    decision: asText(raw.decision),
    summary: asText(raw.summary),
    period_ids: periodIds as FinanceReviewOutcome["period_ids"],
    unpaid_count: asNumber(raw.unpaid_count),
    unpaid_total: asText(raw.unpaid_total),
    unreceived_count: asNumber(raw.unreceived_count),
    unreceived_total: asText(raw.unreceived_total),
    candidate_count: candidateCount,
    candidates,
    method: asText(raw.method),
    limitations: asStrings(raw.limitations),
    human_review_required: true,
    original_inputs_modified: false,
    external_action: "none",
  };
}

function normalizeOutboundParameter(value: unknown): OutboundRuleParameter | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const name = asText(raw.name);
  const parameterValue = asText(raw.value);
  if (!name || !parameterValue) return null;
  return { name, value: parameterValue, unit: asText(raw.unit) || null };
}

function normalizeOutboundRule(value: unknown): OutboundRule | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const ruleId = asText(raw.rule_id);
  const group = asText(raw.group);
  const coverageState = asText(raw.coverage_state);
  const groups = ["TIME", "FREQ", "RECORD", "IDENTITY", "THIRD_PARTY", "PROHIBIT", "CONNECT", "PTP", "SOFT", "HARD", "DISPUTE", "INVALID", "TERMINAL", "PAYMENT", "REDIAL"];
  if (!ruleId || !groups.includes(group) || !["covered", "unsupported", "conflict"].includes(coverageState)) return null;
  return {
    rule_id: ruleId,
    group: group as OutboundRule["group"],
    source_file_ref: asText(raw.source_file_ref),
    locator: asText(raw.locator),
    excerpt: asText(raw.excerpt),
    parameters: Array.isArray(raw.parameters) ? raw.parameters.map(normalizeOutboundParameter).filter((item): item is OutboundRuleParameter => item !== null) : [],
    expected_relation: asText(raw.expected_relation),
    expected_action: asText(raw.expected_action),
    coverage_state: coverageState as OutboundRule["coverage_state"],
    mapped_node_ids: asStrings(raw.mapped_node_ids),
    mapped_edge_ids: asStrings(raw.mapped_edge_ids),
    mapped_guard_ids: asStrings(raw.mapped_guard_ids),
    mapped_terminal_ids: asStrings(raw.mapped_terminal_ids),
  };
}

function normalizeOutboundNode(value: unknown): OutboundNode | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const kind = asText(raw.kind);
  if (!asText(raw.node_id) || !["start", "gate", "decision", "action", "terminal"].includes(kind)) return null;
  return { node_id: asText(raw.node_id), label: asText(raw.label), kind: kind as OutboundNode["kind"], source_rule_ids: asStrings(raw.source_rule_ids), future_action: raw.future_action === true };
}

function normalizeOutboundEdge(value: unknown): OutboundEdge | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (!asText(raw.edge_id) || !asText(raw.from_node_id) || !asText(raw.to_node_id)) return null;
  return { edge_id: asText(raw.edge_id), from_node_id: asText(raw.from_node_id), to_node_id: asText(raw.to_node_id), label: asText(raw.label), guard_ids: asStrings(raw.guard_ids), source_rule_ids: asStrings(raw.source_rule_ids), future_action: raw.future_action === true };
}

function normalizeOutboundGuard(value: unknown): OutboundGuard | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (!asText(raw.guard_id)) return null;
  return { guard_id: asText(raw.guard_id), label: asText(raw.label), parameters: Array.isArray(raw.parameters) ? raw.parameters.map(normalizeOutboundParameter).filter((item): item is OutboundRuleParameter => item !== null) : [], source_rule_ids: asStrings(raw.source_rule_ids) };
}

function normalizeOutboundTerminal(value: unknown): OutboundTerminal | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (!asText(raw.terminal_id) || !asText(raw.node_id)) return null;
  return { terminal_id: asText(raw.terminal_id), node_id: asText(raw.node_id), label: asText(raw.label), source_rule_ids: asStrings(raw.source_rule_ids), source_listed: raw.source_listed === true };
}

function normalizeOutboundFlowOutcome(value: unknown): OutboundFlowOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  const rules = Array.isArray(raw.rules) ? raw.rules.map(normalizeOutboundRule).filter((item): item is OutboundRule => item !== null) : [];
  const nodes = Array.isArray(raw.nodes) ? raw.nodes.map(normalizeOutboundNode).filter((item): item is OutboundNode => item !== null) : [];
  const edges = Array.isArray(raw.edges) ? raw.edges.map(normalizeOutboundEdge).filter((item): item is OutboundEdge => item !== null) : [];
  const guards = Array.isArray(raw.guards) ? raw.guards.map(normalizeOutboundGuard).filter((item): item is OutboundGuard => item !== null) : [];
  const terminals = Array.isArray(raw.terminals) ? raw.terminals.map(normalizeOutboundTerminal).filter((item): item is OutboundTerminal => item !== null) : [];
  const integrityRaw = raw.graph_integrity && typeof raw.graph_integrity === "object" ? raw.graph_integrity as Record<string, unknown> : null;
  const atomicRequirementCount = asNumber(raw.atomic_requirement_count);
  if (!asText(raw.outcome_id) || !["approval_required", "invalid"].includes(status) || rules.length !== atomicRequirementCount || nodes.length !== asNumber(raw.node_count) || edges.length !== asNumber(raw.edge_count) || guards.length !== asNumber(raw.guard_count) || terminals.length !== asNumber(raw.terminal_count) || !integrityRaw || raw.human_approval_required !== true || raw.legal_opinion !== false || raw.original_inputs_modified !== false) return null;
  const graph_integrity: OutboundGraphIntegrity = {
    unique_start: integrityRaw.unique_start === true,
    unique_ids: integrityRaw.unique_ids === true,
    no_dangling_edges: integrityRaw.no_dangling_edges === true,
    all_nodes_reachable: integrityRaw.all_nodes_reachable === true,
    all_terminals_reachable: integrityRaw.all_terminals_reachable === true,
    every_nonterminal_has_outgoing: integrityRaw.every_nonterminal_has_outgoing === true,
    every_node_can_reach_terminal: integrityRaw.every_node_can_reach_terminal === true,
    critical_order_valid: integrityRaw.critical_order_valid === true,
    third_party_boundary_valid: integrityRaw.third_party_boundary_valid === true,
    all_rules_mapped: integrityRaw.all_rules_mapped === true,
  };
  return {
    outcome_id: asText(raw.outcome_id), status: status as OutboundFlowOutcome["status"], decision: asText(raw.decision), summary: asText(raw.summary),
    source_rule_group_count: asNumber(raw.source_rule_group_count), atomic_requirement_count: atomicRequirementCount, covered_count: asNumber(raw.covered_count), unsupported_count: asNumber(raw.unsupported_count), conflict_count: asNumber(raw.conflict_count),
    node_count: nodes.length, edge_count: edges.length, guard_count: guards.length, terminal_count: terminals.length, reachable_terminal_count: asNumber(raw.reachable_terminal_count),
    parameters: Array.isArray(raw.parameters) ? raw.parameters.map(normalizeOutboundParameter).filter((item): item is OutboundRuleParameter => item !== null) : [], rules, nodes, edges, guards, terminals, graph_integrity,
    human_approval_required: true, legal_opinion: false, original_inputs_modified: false, external_action: "none",
  };
}

function normalizeCustomerSegmentationRule(value: unknown): CustomerSegmentationRule | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const category = asText(raw.category);
  if (!asText(raw.rule_id) || !["cleaning", "classification", "priority", "exclusion", "report"].includes(category) || !asText(raw.locator)) return null;
  return {
    rule_id: asText(raw.rule_id),
    category: category as CustomerSegmentationRule["category"],
    source_file_ref: asText(raw.source_file_ref),
    locator: asText(raw.locator),
    excerpt: asText(raw.excerpt),
    parameters: asStrings(raw.parameters),
  };
}

function normalizeCustomerSampleDecision(value: unknown): CustomerSampleDecision | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const exclusion = asText(raw.exclusion_reason);
  const rawScores = asStringRecord(raw.raw_scores);
  const cleanedScores = asNumberRecord(raw.cleaned_scores);
  if (
    !asText(raw.sample_id)
    || !asText(raw.source_file_ref)
    || !asText(raw.source_locator)
    || Object.keys(rawScores).length !== 4
    || Object.keys(cleanedScores).length !== 4
    || (exclusion && !["exact_duplicate", "unclassified"].includes(exclusion))
  ) return null;
  return {
    sample_id: asText(raw.sample_id),
    source_file_ref: asText(raw.source_file_ref),
    source_row: asNumber(raw.source_row),
    source_locator: asText(raw.source_locator),
    industry: asText(raw.industry),
    company_size: asText(raw.company_size),
    respondent_role: asText(raw.respondent_role),
    raw_scores: rawScores,
    cleaned_scores: cleanedScores,
    transformations: asStrings(raw.transformations),
    matched_profiles: asStrings(raw.matched_profiles),
    priority_applied: raw.priority_applied === true,
    final_label: asText(raw.final_label) || null,
    exclusion_reason: (exclusion || null) as CustomerSampleDecision["exclusion_reason"],
    duplicate_of: asText(raw.duplicate_of) || null,
    rule_refs: asStrings(raw.rule_refs),
  };
}

function normalizeCustomerSegmentationOutcome(value: unknown): CustomerSegmentationOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  const parametersRaw = raw.parameters && typeof raw.parameters === "object" && !Array.isArray(raw.parameters)
    ? raw.parameters as Record<string, unknown>
    : null;
  const rules = Array.isArray(raw.rules)
    ? raw.rules.map(normalizeCustomerSegmentationRule).filter((item): item is CustomerSegmentationRule => item !== null)
    : [];
  const samples = Array.isArray(raw.samples)
    ? raw.samples.map(normalizeCustomerSampleDecision).filter((item): item is CustomerSampleDecision => item !== null)
    : [];
  const profileCounts = asNumberRecord(raw.profile_counts);
  const thresholds = asNumberRecord(parametersRaw?.profile_thresholds);
  const priority = asStrings(parametersRaw?.profile_priority);
  const sourceCount = asNumber(raw.source_row_count);
  const uniqueCount = asNumber(raw.unique_payload_count);
  const duplicateCount = asNumber(raw.duplicate_count);
  const classifiedCount = asNumber(raw.classified_count);
  const unclassifiedCount = asNumber(raw.unclassified_count);
  const excludedCount = asNumber(raw.excluded_count);
  const witnessCount = asNumber(raw.priority_witness_count);
  const encoding = asText(parametersRaw?.parsing_encoding);
  if (
    !asText(raw.outcome_id)
    || !["sales_review_required", "invalid"].includes(status)
    || !parametersRaw
    || !["utf-8-sig", "utf-8", "gb18030"].includes(encoding)
    || Object.keys(thresholds).length !== 3
    || priority.length !== 3
    || rules.length === 0
    || samples.length !== sourceCount
    || uniqueCount + duplicateCount !== sourceCount
    || classifiedCount + unclassifiedCount !== uniqueCount
    || unclassifiedCount + duplicateCount !== excludedCount
    || Object.values(profileCounts).reduce((sum, count) => sum + count, 0) !== classifiedCount
    || samples.filter((sample) => sample.duplicate_of !== null).length !== duplicateCount
    || samples.filter((sample) => sample.priority_applied).length !== witnessCount
    || parametersRaw.duplicate_policy !== "exact_non_id_payload"
    || raw.duplicate_policy_assumption !== "exact_non_id_payload"
    || raw.policy_assumption_review_required !== true
    || raw.strategy_evidence_status !== "no_approved_strategy_source"
    || raw.human_review_required !== true
    || raw.original_inputs_modified !== false
    || raw.external_action !== "none"
  ) return null;
  return {
    outcome_id: asText(raw.outcome_id),
    status: status as CustomerSegmentationOutcome["status"],
    decision: asText(raw.decision),
    summary: asText(raw.summary),
    source_row_count: sourceCount,
    unique_payload_count: uniqueCount,
    duplicate_count: duplicateCount,
    classified_count: classifiedCount,
    unclassified_count: unclassifiedCount,
    excluded_count: excludedCount,
    profile_counts: profileCounts,
    parameters: {
      parsing_encoding: encoding as CustomerSegmentationOutcome["parameters"]["parsing_encoding"],
      missing_score_default: asNumber(parametersRaw.missing_score_default),
      chinese_number_domain: asText(parametersRaw.chinese_number_domain),
      profile_thresholds: thresholds,
      profile_priority: priority,
      duplicate_policy: "exact_non_id_payload",
    },
    rules,
    samples,
    duplicate_policy_assumption: "exact_non_id_payload",
    policy_assumption_review_required: true,
    priority_witness_count: witnessCount,
    strategy_evidence_status: "no_approved_strategy_source",
    human_review_required: true,
    original_inputs_modified: false,
    external_action: "none",
  };
}

function normalizeSREObservation(value: unknown): SREObservation | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  if (!asText(raw.observation_id) || !asText(raw.locator) || !["observed", "unclassified"].includes(status)) return null;
  return {
    observation_id: asText(raw.observation_id),
    category: asText(raw.category),
    statement: asText(raw.statement),
    source_file_ref: asText(raw.source_file_ref),
    locator: asText(raw.locator),
    excerpt: asText(raw.excerpt),
    fields: asStringRecord(raw.fields),
    status: status as SREObservation["status"],
  };
}

function normalizeSREConflict(value: unknown): SRESourceConflict | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  if (!asText(raw.conflict_id) || !["open", "resolved"].includes(status)) return null;
  return {
    conflict_id: asText(raw.conflict_id), title: asText(raw.title), statement: asText(raw.statement),
    side_a_observation_ids: asStrings(raw.side_a_observation_ids), side_b_observation_ids: asStrings(raw.side_b_observation_ids),
    locators: asStrings(raw.locators), impact: asText(raw.impact), status: status as SRESourceConflict["status"],
  };
}

function normalizeSREHypothesis(value: unknown): SREHypothesis | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const confidence = asText(raw.confidence);
  if (!asText(raw.hypothesis_id) || !["low", "medium", "high"].includes(confidence)) return null;
  return {
    hypothesis_id: asText(raw.hypothesis_id), statement: asText(raw.statement), confidence: confidence as SREHypothesis["confidence"],
    supporting_observation_ids: asStrings(raw.supporting_observation_ids), supporting_locators: asStrings(raw.supporting_locators),
    counter_evidence_ids: asStrings(raw.counter_evidence_ids), counter_evidence_locators: asStrings(raw.counter_evidence_locators),
    limitations: asStrings(raw.limitations),
  };
}

function normalizeSREProposal(value: unknown): SREActionProposal | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const kind = asText(raw.kind); const risk = asText(raw.risk_level); const target = asText(raw.target_status);
  const command = asText(raw.command_template) || null; const action = asText(raw.action_text) || null;
  if (
    !asText(raw.proposal_id)
    || !["read_only_preflight", "write_change", "business_mitigation"].includes(kind)
    || !["low", "medium", "high"].includes(risk)
    || !["unresolved", "not_applicable"].includes(target)
    || Boolean(command) === Boolean(action)
    || raw.approval_required !== true
    || raw.executed !== false
  ) return null;
  return {
    proposal_id: asText(raw.proposal_id), kind: kind as SREActionProposal["kind"], title: asText(raw.title), risk_level: risk as SREActionProposal["risk_level"],
    command_template: command, action_text: action, target_status: target as SREActionProposal["target_status"], target_rationale: asText(raw.target_rationale),
    preconditions: asStrings(raw.preconditions), rollback: asText(raw.rollback), verify_after: asStrings(raw.verify_after),
    official_reference: asText(raw.official_reference) || null, approval_required: true, executed: false, source_observation_ids: asStrings(raw.source_observation_ids),
  };
}

function normalizeSREDiagnosisOutcome(value: unknown): SREDiagnosisOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  const observations = Array.isArray(raw.observations) ? raw.observations.map(normalizeSREObservation).filter((item): item is SREObservation => item !== null) : [];
  const conflicts = Array.isArray(raw.source_conflicts) ? raw.source_conflicts.map(normalizeSREConflict).filter((item): item is SRESourceConflict => item !== null) : [];
  const hypotheses = Array.isArray(raw.hypotheses) ? raw.hypotheses.map(normalizeSREHypothesis).filter((item): item is SREHypothesis => item !== null) : [];
  const proposals = Array.isArray(raw.action_proposals) ? raw.action_proposals.map(normalizeSREProposal).filter((item): item is SREActionProposal => item !== null) : [];
  const mitigations = Array.isArray(raw.business_mitigations) ? raw.business_mitigations.map(normalizeSREProposal).filter((item): item is SREActionProposal => item !== null) : [];
  if (
    !asText(raw.outcome_id) || !["incident_review_required", "invalid"].includes(status)
    || observations.length !== asNumber(raw.observation_count) || conflicts.length !== asNumber(raw.conflict_count)
    || hypotheses.length !== asNumber(raw.hypothesis_count) || proposals.length !== asNumber(raw.proposal_count)
    || mitigations.length !== asNumber(raw.business_mitigation_count)
    || observations.filter((item) => item.status === "unclassified").length !== asNumber(raw.unclassified_count)
    || raw.resolved_target_count !== 0 || raw.human_review_required !== true
    || raw.original_inputs_modified !== false || raw.external_action !== "none"
  ) return null;
  const clusterFacts = raw.cluster_facts && typeof raw.cluster_facts === "object" && !Array.isArray(raw.cluster_facts) ? raw.cluster_facts as Record<string, unknown> : {};
  const nodeFacts = raw.node_facts && typeof raw.node_facts === "object" && !Array.isArray(raw.node_facts) ? raw.node_facts as Record<string, unknown> : {};
  const metricFacts = raw.metric_facts && typeof raw.metric_facts === "object" && !Array.isArray(raw.metric_facts) ? raw.metric_facts as Record<string, unknown> : {};
  return {
    outcome_id: asText(raw.outcome_id), status: status as SREDiagnosisOutcome["status"], decision: asText(raw.decision), summary: asText(raw.summary),
    source_line_count: asNumber(raw.source_line_count), cluster_facts: clusterFacts, node_facts: nodeFacts, metric_facts: metricFacts, timeline: asStrings(raw.timeline),
    observation_count: observations.length, conflict_count: conflicts.length, hypothesis_count: hypotheses.length, proposal_count: proposals.length,
    business_mitigation_count: mitigations.length, unclassified_count: asNumber(raw.unclassified_count), observations, source_conflicts: conflicts,
    hypotheses, action_proposals: proposals, business_mitigations: mitigations, resolved_target_count: 0, human_review_required: true,
    original_inputs_modified: false, external_action: "none",
  };
}

function normalizeUXRule(value: unknown): UXRule | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const kind = asText(raw.kind);
  if (!asText(raw.rule_id) || !["severity", "frequency", "priority", "disposition"].includes(kind) || !asText(raw.locator)) return null;
  return { rule_id: asText(raw.rule_id), kind: kind as UXRule["kind"], name: asText(raw.name), locator: asText(raw.locator), excerpt: asText(raw.excerpt), parameters: asStringRecord(raw.parameters) };
}

function normalizeUXSpec(value: unknown): UXSpecElement | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (!asText(raw.spec_id) || !asText(raw.page_name) || !asText(raw.element_name) || !asText(raw.locator)) return null;
  return { spec_id: asText(raw.spec_id), page_name: asText(raw.page_name), page_order: asNumber(raw.page_order), element_name: asText(raw.element_name), element_order: asNumber(raw.element_order), requirement: asText(raw.requirement), locator: asText(raw.locator) };
}

function normalizeUXMapping(value: unknown): UXMappingDecision | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status);
  if (!asText(raw.mapping_id) || !["controlled_adapter_assumption", "unmapped"].includes(status) || raw.review_required !== true) return null;
  return { mapping_id: asText(raw.mapping_id), page_name: asText(raw.page_name), operation: asText(raw.operation), status: status as UXMappingDecision["status"], spec_id: asText(raw.spec_id) || null, element_name: asText(raw.element_name) || null, candidate_spec_ids: asStrings(raw.candidate_spec_ids), mapping_basis: asText(raw.mapping_basis), review_required: true };
}

function normalizeUXRow(value: unknown): UXRowDecision | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const status = asText(raw.status); const mappingStatus = asText(raw.mapping_status);
  if (!asNumber(raw.row_number) || !asText(raw.locator) || !["included", "excluded", "manual_review"].includes(status) || !["controlled_adapter_assumption", "unmapped", "not_applicable"].includes(mappingStatus)) return null;
  return {
    row_number: asNumber(raw.row_number), locator: asText(raw.locator), page_name: asText(raw.page_name), page_path: asText(raw.page_path), operation: asText(raw.operation), operation_result: asText(raw.operation_result), pain_type: asText(raw.pain_type), failure_reason: asText(raw.failure_reason), misclick_count: asNumber(raw.misclick_count), exit_node: asText(raw.exit_node), retry_count: asNumber(raw.retry_count), status: status as UXRowDecision["status"], group_id: asText(raw.group_id) || null, mapping_id: asText(raw.mapping_id) || null, mapping_status: mappingStatus as UXRowDecision["mapping_status"], duplicate_group_id: asText(raw.duplicate_group_id) || null, duplicate_ordinal: asNumber(raw.duplicate_ordinal, 1), reason: asText(raw.reason), data_quality_flags: asStrings(raw.data_quality_flags),
  };
}

function normalizeUXGroupRuleRef(value: unknown): UXGroupRuleRef | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const role = asText(raw.role); const application = asText(raw.application);
  if (
    !["severity", "frequency", "priority"].includes(role)
    || !asText(raw.rule_id)
    || !asText(raw.locator)
    || !["applied", "conflict_side"].includes(application)
  ) return null;
  return { role: role as UXGroupRuleRef["role"], rule_id: asText(raw.rule_id), locator: asText(raw.locator), application: application as UXGroupRuleRef["application"] };
}

function normalizeUXGroup(value: unknown): UXGroup | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const severity = asText(raw.severity); const frequency = asText(raw.frequency); const priority = asText(raw.priority) || null;
  const ruleRefs = Array.isArray(raw.rule_refs) ? raw.rule_refs.map(normalizeUXGroupRuleRef).filter((item): item is UXGroupRuleRef => item !== null) : [];
  const severityRefs = ruleRefs.filter((item) => item.role === "severity");
  const frequencyRefs = ruleRefs.filter((item) => item.role === "frequency");
  const priorityRefs = ruleRefs.filter((item) => item.role === "priority");
  if (
    !asText(raw.group_id)
    || !["严重", "中等", "轻微"].includes(severity)
    || !["高频", "中频", "低频", "边界待确认"].includes(frequency)
    || (priority !== null && !["P0", "P1", "P2", "P3", "P4"].includes(priority))
    || raw.suggestion_status !== "no_approved_solution_source"
    || severityRefs.length !== 1
    || (frequency === "边界待确认" ? frequencyRefs.length !== 2 || priorityRefs.length !== 0 : frequencyRefs.length !== 1 || priorityRefs.length !== 1)
  ) return null;
  return {
    group_id: asText(raw.group_id), page_name: asText(raw.page_name), page_path: asText(raw.page_path), operation: asText(raw.operation), spec_id: asText(raw.spec_id), element_name: asText(raw.element_name), pain_type: asText(raw.pain_type), severity: severity as UXGroup["severity"], scenario_count: asNumber(raw.scenario_count), denominator: asNumber(raw.denominator), ratio: asText(raw.ratio), frequency: frequency as UXGroup["frequency"], priority: priority as UXGroup["priority"], disposition: asText(raw.disposition), spec_requirement: asText(raw.spec_requirement), contributing_row_locators: asStrings(raw.contributing_row_locators), mapping_status: "controlled_adapter_assumption", mapping_basis: asText(raw.mapping_basis), rule_refs: ruleRefs, data_quality_flags: asStrings(raw.data_quality_flags), suggestion_status: "no_approved_solution_source", suggestion_template: asText(raw.suggestion_template),
  };
}

function normalizeUXConflict(value: unknown): UXRuleConflict | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>; const status = asText(raw.status);
  if (!asText(raw.conflict_id) || !["open", "resolved"].includes(status)) return null;
  return { conflict_id: asText(raw.conflict_id), title: asText(raw.title), locators: asStrings(raw.locators), statement: asText(raw.statement), impact: asText(raw.impact), status: status as UXRuleConflict["status"] };
}

function normalizeUXPrioritizationOutcome(value: unknown): UXPrioritizationOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>; const status = asText(raw.status);
  const rules = Array.isArray(raw.rules) ? raw.rules.map(normalizeUXRule).filter((item): item is UXRule => item !== null) : [];
  const specs = Array.isArray(raw.specs) ? raw.specs.map(normalizeUXSpec).filter((item): item is UXSpecElement => item !== null) : [];
  const mappings = Array.isArray(raw.mappings) ? raw.mappings.map(normalizeUXMapping).filter((item): item is UXMappingDecision => item !== null) : [];
  const groups = Array.isArray(raw.groups) ? raw.groups.map(normalizeUXGroup).filter((item): item is UXGroup => item !== null) : [];
  const rows = Array.isArray(raw.row_decisions) ? raw.row_decisions.map(normalizeUXRow).filter((item): item is UXRowDecision => item !== null) : [];
  const conflicts = Array.isArray(raw.rule_conflicts) ? raw.rule_conflicts.map(normalizeUXConflict).filter((item): item is UXRuleConflict => item !== null) : [];
  const sourceCount = asNumber(raw.source_row_count); const analyzedCount = asNumber(raw.analyzed_row_count); const priorityCounts = asNumberRecord(raw.priority_counts);
  if (
    !asText(raw.outcome_id) || !["prioritization_review_required", "invalid"].includes(status)
    || sourceCount <= 0 || analyzedCount !== sourceCount || rows.length !== sourceCount || groups.length !== asNumber(raw.group_count)
    || rows.filter((row) => row.status === "included").length !== asNumber(raw.included_pain_row_count)
    || rows.filter((row) => row.status === "excluded").length !== asNumber(raw.excluded_no_pain_count)
    || ["P0", "P1", "P2", "P3", "P4"].some((label) => (priorityCounts[label] ?? 0) !== groups.filter((group) => group.priority === label).length)
    || rules.length === 0 || specs.length === 0 || raw.suggestion_status !== "no_approved_solution_source"
    || raw.human_review_required !== true || raw.original_inputs_modified !== false || raw.external_action !== "none"
  ) return null;
  return {
    outcome_id: asText(raw.outcome_id), status: status as UXPrioritizationOutcome["status"], decision: asText(raw.decision), summary: asText(raw.summary), source_row_count: sourceCount, analyzed_row_count: analyzedCount, included_pain_row_count: asNumber(raw.included_pain_row_count), excluded_no_pain_count: asNumber(raw.excluded_no_pain_count), success_with_pain_count: asNumber(raw.success_with_pain_count), group_count: groups.length, priority_counts: priorityCounts, duplicate_group_count: asNumber(raw.duplicate_group_count), duplicate_extra_count: asNumber(raw.duplicate_extra_count), unmapped_count: asNumber(raw.unmapped_count), uncovered_spec_count: asNumber(raw.uncovered_spec_count), rules, specs, mappings, groups, row_decisions: rows, rule_conflicts: conflicts, suggestion_status: "no_approved_solution_source", human_review_required: true, original_inputs_modified: false, external_action: "none",
  };
}

function normalizeBusinessGateOutcome(value: unknown): BusinessGateOutcome | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  const outcomeId = asText(raw.outcome_id);
  const status = asText(raw.status);
  const outcomeKind = asText(raw.outcome_kind, "release_readiness");
  if (!outcomeId || !["passed", "failed", "invalid"].includes(status) || !["release_readiness", "legal_delegation_review"].includes(outcomeKind)) return null;
  const gates = Array.isArray(raw.gates) ? raw.gates.map(normalizeBusinessGate).filter((item): item is BusinessGate => item !== null) : [];
  const metrics = Array.isArray(raw.auxiliary_metrics) ? raw.auxiliary_metrics.map(normalizeBusinessMetric).filter((item): item is BusinessMetric => item !== null) : [];
  const records = Array.isArray(raw.records) ? raw.records.map(normalizeBusinessRecord).filter((item): item is BusinessRecord => item !== null) : [];
  return {
    outcome_id: outcomeId,
    outcome_kind: outcomeKind as BusinessGateOutcome["outcome_kind"],
    status: status as BusinessGateOutcome["status"],
    decision: asText(raw.decision),
    summary: asText(raw.summary),
    total_gate_count: asNumber(raw.total_gate_count),
    failed_gate_count: asNumber(raw.failed_gate_count),
    gates,
    auxiliary_metrics: metrics,
    records,
    external_action: "none",
  };
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
  const rawSelfTest = raw.self_test && typeof raw.self_test === "object" ? raw.self_test as Record<string, unknown> : null;
  const selfTest = rawSelfTest ? {
    instruction: asText(rawSelfTest.instruction),
    expected_files: asStrings(rawSelfTest.expected_files),
    commands: asStrings(rawSelfTest.commands),
    expected_checks: asStrings(rawSelfTest.expected_checks),
    failure_signals: asStrings(rawSelfTest.failure_signals),
    test_manifest_file: asText(rawSelfTest.test_manifest_file) || null,
    test_manifest_matches_collected: typeof rawSelfTest.test_manifest_matches_collected === "boolean" ? rawSelfTest.test_manifest_matches_collected : null,
    test_suites: Array.isArray(rawSelfTest.test_suites)
      ? rawSelfTest.test_suites.map(normalizeArtifactTestSuite).filter((item): item is ArtifactTestSuite => item !== null)
      : [],
  } : null;
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
    deliverable_type: asText(raw.deliverable_type) || null,
    key_outputs: asStrings(raw.key_outputs),
    key_outputs_label: asText(raw.key_outputs_label) || null,
    review_guidance: asText(raw.review_guidance) || null,
    execution_summary: asText(raw.execution_summary) || null,
    self_test: selfTest && selfTest.instruction && selfTest.commands.length > 0 ? selfTest : null,
    business_gate_outcome: normalizeBusinessGateOutcome(raw.business_gate_outcome),
    legal_review_outcome: normalizeLegalReviewOutcome(raw.legal_review_outcome),
    candidate_review_outcome: normalizeCandidateReviewOutcome(raw.candidate_review_outcome),
    finance_review_outcome: normalizeFinanceReviewOutcome(raw.finance_review_outcome),
    outbound_flow_outcome: normalizeOutboundFlowOutcome(raw.outbound_flow_outcome),
    customer_segmentation_outcome: normalizeCustomerSegmentationOutcome(raw.customer_segmentation_outcome),
    sre_diagnosis_outcome: normalizeSREDiagnosisOutcome(raw.sre_diagnosis_outcome),
    ux_prioritization_outcome: normalizeUXPrioritizationOutcome(raw.ux_prioritization_outcome),
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
    business_gate_outcome: normalizeBusinessGateOutcome(raw.business_gate_outcome),
    legal_review_outcome: normalizeLegalReviewOutcome(raw.legal_review_outcome),
    candidate_review_outcome: normalizeCandidateReviewOutcome(raw.candidate_review_outcome),
    finance_review_outcome: normalizeFinanceReviewOutcome(raw.finance_review_outcome),
    outbound_flow_outcome: normalizeOutboundFlowOutcome(raw.outbound_flow_outcome),
    customer_segmentation_outcome: normalizeCustomerSegmentationOutcome(raw.customer_segmentation_outcome),
    sre_diagnosis_outcome: normalizeSREDiagnosisOutcome(raw.sre_diagnosis_outcome),
    ux_prioritization_outcome: normalizeUXPrioritizationOutcome(raw.ux_prioritization_outcome),
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
    narrative_reconciliation: normalizeNarrativeReconciliation(raw.narrative_reconciliation),
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
    && latestRound.next_step.recovery_kind === "source_location"
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
      <header><span>第 {latestRound.round_number} 轮</span><b>{verifiedOutcomeWithAuditPending ? "成果已生成，说明位置待查找" : gateLabel(latestRound.next_step?.decision)}</b></header>
      <ol>{LOOP_PHASES.slice(0, 5).map((phase, index) => <li key={phase.key} className={index < phaseIndex || latestRound.status === "completed" ? "is-complete" : index === phaseIndex ? "is-active" : ""}><span>{index < phaseIndex || latestRound.status === "completed" ? <IconCheck aria-hidden="true" /> : index + 1}</span><b>{phase.label}</b></li>)}</ol>
      {verifiedOutcomeWithAuditPending
        ? <p><IconAlertTriangle aria-hidden="true" />成果的 {state.passedArtifactChecks}/{state.totalArtifactChecks} 项检查已通过；一条 Agent 说明还没定位到原表格行或单元格。</p>
        : latestRound.evidence_gaps[0] && <p><IconAlertTriangle aria-hidden="true" />{latestRound.evidence_gaps[0].label}</p>}
    </section>}
    {latestRound?.next_step?.recovery_kind && <div className="trace-recovery-hint"><IconArrowRight aria-hidden="true" /><span><b>{verifiedOutcomeWithAuditPending ? "只需查找说明位置" : terminalRecovery ? "本次 Run 已结束" : "下一步已准备好"}</b>{verifiedOutcomeWithAuditPending ? "回到主区可以查看成果，或让 Agent 只重新查找这条说明的位置；不会重做成果。" : terminalRecovery ? "回到主区选择一个未完成分支，以它为目标创建新的独立 Run。" : "回到主区选择一个最小分支，可补充方向后继续。"}</span></div>}
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
    const artifactCheckSummary = summarizeArtifactChecks(run?.workspace_artifacts ?? []);
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
      passedArtifactChecks: artifactCheckSummary.passed,
      totalArtifactChecks: artifactCheckSummary.total,
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
          <button type="button" className={view === "result" ? "is-active" : ""} onClick={() => setView("result")}><IconCircleCheck aria-hidden="true" />成果与建议{run?.workspace_artifacts.length ? <b>{run.workspace_artifacts.length}</b> : run?.result ? <b>{run.result.findings.length}</b> : null}</button>
        </nav>
        <div className="workspace-content">
          {view === "data" && <FilePreview preview={preview} file={activeFile} loading={previewLoading} error={previewError} />}
          {view === "loop" && <LoopView run={run} files={allFiles} controlBusy={controlBusy} onControl={controlLoop} onReview={setReviewRequest} onStartTask={startTask} starting={starting} />}
          {view === "result" && <ResultView result={run?.result ?? null} artifacts={run?.artifact_versions ?? []} workspaceArtifacts={run?.workspace_artifacts ?? []} receipts={run?.effect_receipts ?? []} reconciliation={run?.narrative_reconciliation ?? null} commit={run?.last_commit ?? null} decisions={run?.decision_records ?? []} decisionRequests={run?.decision_requests ?? []} files={allFiles} onOpenFile={openFile} onReview={setReviewRequest} onStartTask={startTask} starting={starting} />}
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
  const hasOpenSourceChoice = pendingResolutions.some((resolution) => resolution.status === "ambiguous" && resolution.candidates.length > 1);
  const useUserLanguageLocationRecovery = recoveryKind === "source_location" && !hasOpenSourceChoice;
  const recoveryBranches = roundBranches.filter((branch) => branch.status === "waiting_input").sort((left, right) => left.missing_file_refs.length - right.missing_file_refs.length);
  const verifiedEffectReady = run.effect_receipts.some((receipt) => receipt.status === "passed")
    && run.workspace_artifacts.length > 0
    && run.workspace_artifacts.every((artifact) => artifact.verifier_status === "passed");
  const effectConclusionArtifact = run.workspace_artifacts.find((artifact) => artifact.execution_summary) ?? null;
  const businessGateOutcome = run.workspace_artifacts.find((artifact) => artifact.business_gate_outcome)?.business_gate_outcome
    ?? run.effect_receipts.find((receipt) => receipt.business_gate_outcome)?.business_gate_outcome
    ?? null;
  const candidateReviewOutcome = run.workspace_artifacts.find((artifact) => artifact.candidate_review_outcome)?.candidate_review_outcome
    ?? run.effect_receipts.find((receipt) => receipt.candidate_review_outcome)?.candidate_review_outcome
    ?? null;
  const financeReviewOutcome = run.workspace_artifacts.find((artifact) => artifact.finance_review_outcome)?.finance_review_outcome
    ?? run.effect_receipts.find((receipt) => receipt.finance_review_outcome)?.finance_review_outcome
    ?? null;
  const outboundFlowOutcome = run.workspace_artifacts.find((artifact) => artifact.outbound_flow_outcome)?.outbound_flow_outcome
    ?? run.effect_receipts.find((receipt) => receipt.outbound_flow_outcome)?.outbound_flow_outcome
    ?? null;
  const customerSegmentationOutcome = run.workspace_artifacts.find((artifact) => artifact.customer_segmentation_outcome)?.customer_segmentation_outcome
    ?? run.effect_receipts.find((receipt) => receipt.customer_segmentation_outcome)?.customer_segmentation_outcome
    ?? null;
  const artifactCheckSummary = summarizeArtifactChecks(run.workspace_artifacts);
  const passedArtifactChecks = artifactCheckSummary.passed;
  const totalArtifactChecks = artifactCheckSummary.total;
  const verifiedOutcomeWithAuditPending = verifiedEffectReady
    && recoveryKind === "source_location"
    && selectedRound?.next_step?.decision === "waiting_input"
    && Boolean(selectedRound.evidence_gaps.length);
  const evidenceGapGroups = verifiedOutcomeWithAuditPending && useUserLanguageLocationRecovery
    ? groupEvidenceGaps(selectedRound?.evidence_gaps ?? [])
    : (selectedRound?.evidence_gaps ?? []).map((gap) => ({
        groupKey: gap.gap_id,
        candidateFileRefs: uniqueFileRefs(gap.candidate_file_refs),
        gaps: [gap],
      }));
  const sourceLocationPresentation = !useUserLanguageLocationRecovery || evidenceGapGroups.length === 0
    ? null
    : verifiedOutcomeWithAuditPending
      ? "verified"
      : boundedTerminalRecovery
        ? "terminal"
        : "unverified";
  const selectedRoundGateLabel = sourceLocationPresentation === "verified"
    ? "成果已生成，说明位置待查找"
    : sourceLocationPresentation === "unverified"
      ? "成果尚未通过，说明位置待查找"
      : sourceLocationPresentation === "terminal"
        ? "旧任务已结束，需要新建任务"
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
  const showGeneratedArtifacts = () => {
    document.getElementById("workspace-artifacts-title")?.scrollIntoView({ behavior: "smooth", block: "start" });
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
    {boundedTerminalRecovery && sourceLocationPresentation !== "terminal" && <section className="loop-terminal-recovery" aria-labelledby="terminal-recovery-title">
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
        <small>{round.round_number === selectedRound?.round_number && sourceLocationPresentation ? selectedRoundGateLabel : round.next_step ? gateLabel(round.next_step.decision) : LOOP_PHASES.find((phase) => phase.key === round.phase)?.label}</small>
      </button>) : <span>服务端正在建立第一轮。</span>}
    </nav>
    {(run.workspace_artifacts.length > 0 || run.effect_receipts.length > 0) && <WorkspaceArtifactSection artifacts={run.workspace_artifacts} receipts={run.effect_receipts} />}
    {run.narrative_reconciliation && <NarrativeReconciliationPanel reconciliation={run.narrative_reconciliation} />}
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
        <header><IconAlertTriangle aria-hidden="true" /><div><span>{sourceLocationPresentation === "verified" ? "成果文件和 Agent 说明分开处理" : sourceLocationPresentation === "unverified" ? "还需要找到说明对应的原表格位置" : "这轮需要分支级处理"}</span><h3 id="source-recovery-title">{sourceLocationPresentation === "verified" ? `成果已生成，还有 ${evidenceGapGroups.length} 条说明缺少原表格位置` : sourceLocationPresentation === "unverified" ? `成果尚未通过，还有 ${evidenceGapGroups.length} 条说明缺少原表格位置` : `共有 ${evidenceGapGroups.length} 个待处理，每次处理 1 个`}</h3><p>{sourceLocationPresentation === "verified" ? "成果文件已经通过检查；现在只需要为 Agent 说明找到可跳转、高亮的具体行或单元格。" : sourceLocationPresentation === "unverified" ? "系统已经找到相关文件，但还不能确认成果；需要先找到说明对应的具体行或单元格。" : pendingResolutions.some((item) => item.status === "ambiguous") ? "需要选择原文的分支与可以直接重试的分支已经分开标注。" : "这些分支都不需要你修改文件；选择一条后才会继续。"}</p></div></header>
        <div className="source-recovery-facts"><span><b>{sourceLocationPresentation === "verified" ? `${passedArtifactChecks}/${totalArtifactChecks} 通过` : "已保留"}</b>{sourceLocationPresentation === "verified" ? "成果文件检查" : "任务计划、文件范围和调用记录"}</span><span><b>{sourceLocationPresentation === "verified" ? "需要复核" : sourceLocationPresentation === "unverified" ? "需要查找" : "未采用"}</b>{sourceLocationPresentation === "verified" ? "这条 Agent 说明" : sourceLocationPresentation === "unverified" ? "说明对应的原表格位置" : "无法定位的候选结论"}</span><span><b>未发生</b>原文件修改或外部动作</span></div>
      </section>}
      {roundBranches.length > 0 && sourceLocationPresentation === null && <section className="loop-branches" aria-label={`第 ${selectedRound.round_number} 轮任务分支`}>
        <header><div><span>任务分支现场</span><h3>{roundBranches.length} 条分支，分别保留证据状态</h3></div><b>{roundBranches.filter((branch) => branch.status === "completed").length}/{roundBranches.length} 已核对</b></header>
        <ol>{roundBranches.map((branch, index) => <li key={branch.branch_id} className={`is-${branch.status}${run.active_branch_id === branch.branch_id ? " is-selected" : ""}`}>
          <span>{branch.status === "completed" ? <IconCheck aria-hidden="true" /> : index + 1}</span>
          <div><header><b>{branch.title}</b><small>{verifiedOutcomeWithAuditPending && branch.status === "waiting_input" ? "审计待补充" : branchStatusLabel(branch.status)}</small></header><p>{branch.objective}</p><footer><span>{branch.input_file_refs.length} 份资料</span>{branch.depends_on.length > 0 && <span>{branch.depends_on.length} 条前序依赖</span>}{branch.parent_branch_id && <span>续自上一轮</span>}{branch.missing_file_refs.length > 0 && <strong>{verifiedOutcomeWithAuditPending ? `${branch.missing_file_refs.length} 处来源待定位` : `缺 ${branch.missing_file_refs.length} 份引用`}</strong>}</footer></div>
          {branch.status === "waiting_input" && waitingForBranch && !guidedRecovery && <div className="loop-branch-actions"><button type="button" className="is-review" onClick={() => onReview(branchReviewRequest(branch, selectedRound.evidence_gaps, selectedRound, run))}><IconEye aria-hidden="true" />查看问题</button><button type="button" onClick={() => void onControl("resume", { branchId: branch.branch_id })} disabled={!canResume || controlBusy !== null}><IconPlayerPlay aria-hidden="true" />{controlBusy === "resume" ? "正在启动" : "继续此分支"}</button></div>}
        </li>)}</ol>
      </section>}
      {selectedRound.result && <section className="loop-round-result"><span>本轮核对结果</span><h3>{selectedRound.result.summary}</h3><p>{selectedRound.result.findings.length} 条发现，引用 {selectedRound.verified_file_refs.length} 份文件。</p>{selectedRound.result.findings.length > 0 && <div className="loop-review-links">{selectedRound.result.findings.map((finding, index) => <button type="button" key={`${finding.title}:${index}`} onClick={() => onReview(findingReviewRequest(finding, index, selectedRound.round_number, run.decision_records, decisionRequests))}><IconEye aria-hidden="true" />核对：{finding.title}</button>)}</div>}</section>}
      {evidenceGapGroups.length > 0 && <section className="loop-gap" aria-labelledby={`loop-gap-title-${selectedRound.round_number}`}>
        <header><IconRoute aria-hidden="true" /><div><span>{sourceLocationPresentation ? "还有一项清楚、可恢复的工作" : "待处理分支"}</span><h3 id={`loop-gap-title-${selectedRound.round_number}`}>{sourceLocationPresentation === "verified" ? `成果已生成，还有 ${evidenceGapGroups.length} 条说明缺少原表格位置` : sourceLocationPresentation === "unverified" ? `成果尚未通过，还有 ${evidenceGapGroups.length} 条说明缺少原表格位置` : sourceLocationPresentation === "terminal" ? `这次任务已结束，还有 ${evidenceGapGroups.length} 条说明未定位` : `共有 ${evidenceGapGroups.length} 个待处理，每次处理 1 个`}</h3><p>{sourceLocationPresentation === "verified" ? "这不是文件缺失、日期错误、金额验算失败或成果生成失败。" : sourceLocationPresentation === "unverified" ? "这是说明位置缺口，不代表文件丢失；成果仍需通过后续检查。" : sourceLocationPresentation === "terminal" ? "旧 Run 不能原地继续；已有记录会保留，接下来需要创建新的独立任务。" : boundedTerminalRecovery ? "旧 Run 已结束；先选一条路径创建新任务，其他结果保持不变。" : "先选一条路径继续；没有被选择的分支不会启动，也不会消耗下一轮预算。"}</p></div><b>{sourceLocationPresentation === "verified" ? "成果文件已保留" : sourceLocationPresentation === "unverified" ? "成果尚未通过" : sourceLocationPresentation === "terminal" ? "需要新任务" : "每次 1 个"}</b></header>
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
          const sourceName = primarySource ?? "相关文件";
          if (sourceLocationPresentation) {
            const sourceExplanation = sourceLocationPresentation === "verified"
              ? `系统知道这条说明来自《${sourceName}》，但还没定位到具体行或单元格。`
              : sourceLocationPresentation === "unverified"
                ? `系统知道相关说明来自《${sourceName}》，但还没定位到具体行或单元格；成果仍需继续检查。`
                : `旧任务记录了《${sourceName}》，但没有完成具体行或单元格定位。`;
            const impactTitle = sourceLocationPresentation === "verified"
              ? "成果文件保持不变"
              : sourceLocationPresentation === "unverified"
                ? "成果尚未通过检查"
                : "旧任务已经结束";
            const impactDetail = sourceLocationPresentation === "verified"
              ? "不影响已经生成的成果文件；这条 Agent 说明仍需人工复核。"
              : sourceLocationPresentation === "unverified"
                ? "当前还不能确认成果；这不是文件缺失、日期错误或金额验算失败。"
                : "已保留旧任务与已有结果；不能原地继续，需要创建新任务。";
            const nextAction = sourceLocationPresentation === "verified"
              ? "只重新查找这条说明的位置"
              : sourceLocationPresentation === "unverified"
                ? "找到位置后继续检查成果"
                : "新任务只处理这条说明位置";
            const primaryAction = requiresSourceChoice
              ? "选择原表格位置"
              : sourceLocationPresentation === "terminal"
                ? "创建新任务查找位置"
                : "查找原表格位置";
            const handleLocationAction = () => {
              if (sourceLocationPresentation === "terminal" || requiresSourceChoice || !branch) {
                onReview(reviewRequest);
                return;
              }
              void onControl("resume", { branchId: branch.branch_id });
            };
            return <li key={group.groupKey} className={`is-${branch?.status ?? "waiting_input"} is-source-location`} aria-label={`待复核说明 ${index + 1}：缺少原表格位置`}>
              <section className="loop-gap-branch-identity"><span>待复核说明 {index + 1}</span><h4>这条说明缺少原表格位置</h4><b>{sourceLocationPresentation === "verified" ? "成果文件已保留" : sourceLocationPresentation === "unverified" ? "仍需继续检查" : "旧任务已停止"}</b></section>
              <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
              <section className="loop-gap-branch-stage"><span>已知来源</span><strong>《{sourceName}》</strong><small>{sourceExplanation}</small></section>
              <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
              <section className="loop-gap-branch-stage is-gate"><span>影响</span><strong>{impactTitle}</strong><small>{impactDetail}</small></section>
              <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
              <section className="loop-gap-branch-next"><span>下一步</span><strong>{nextAction}</strong><div className="loop-gap-user-actions"><button type="button" className="is-primary" onClick={handleLocationAction} disabled={controlBusy !== null}>{requiresSourceChoice ? <IconEye aria-hidden="true" /> : <IconRefresh aria-hidden="true" />}{controlBusy === "resume" ? "正在查找" : primaryAction}</button>{sourceLocationPresentation === "verified" && run.workspace_artifacts.length > 0 && <button type="button" onClick={showGeneratedArtifacts}><IconFileDescription aria-hidden="true" />查看已生成成果</button>}</div></section>
              <details className="loop-gap-technical-details"><summary>技术详情</summary><dl><div><dt>内部影响</dt><dd>{affectedBranches.length} 个 Branch / {group.gaps.length} 个 Gap</dd></div><div><dt>原始问题</dt><dd>{gap.detail}</dd></div><div><dt>Resolution</dt><dd>{resolution?.status ?? "unavailable"}</dd></div><div><dt>恢复边界</dt><dd>只恢复受影响 Branch，不重新生成或覆盖 Artifact，不修改原文件，不执行外部动作。</dd></div></dl></details>
            </li>;
          }
          const nextLabel = requiresSourceChoice
            ? "需要你选 1 个位置"
            : boundedTerminalRecovery
              ? "查看后创建新任务"
              : "建议只重试此分支";
          const groupTitle = branch?.title ?? gap.label;
          return <li key={group.groupKey} className={`is-${branch?.status ?? "waiting_input"}`} aria-label={`分支：${groupTitle}`}>
            <section className="loop-gap-branch-identity"><span>分支 {index + 1}</span><h4>{groupTitle}</h4><b>{branch ? branchStatusLabel(branch.status) : "等待处理"}</b></section>
            <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
            <section className="loop-gap-branch-stage"><span>当前材料</span><strong>{primarySource ?? "等待 Agent 重新检索"}</strong><small>{sourceRefs.length > 1 ? `另有 ${sourceRefs.length - 1} 份 · ` : ""}{branch?.verified_file_refs.length ?? 0}/{sourceRefs.length} 份已形成引用</small></section>
            <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
            <section className="loop-gap-branch-stage is-gate"><span>证据门</span><strong>{evidenceGateLabel}</strong><small>{gap.detail}</small></section>
            <IconArrowRight className="loop-gap-branch-arrow" aria-hidden="true" />
            <section className="loop-gap-branch-next"><span>下一步</span><strong>{nextLabel}</strong><button type="button" onClick={() => onReview(reviewRequest)}>{requiresSourceChoice ? <IconEye aria-hidden="true" /> : <IconPlayerPlay aria-hidden="true" />}{requiresSourceChoice ? "选择原文位置" : boundedTerminalRecovery ? "查看如何续办" : "继续此分支"}</button></section>
          </li>;
        })}</ol>
        <footer><IconShieldCheck aria-hidden="true" /><span>{sourceLocationPresentation === "verified" ? "查找原表格位置只恢复受影响的说明检查；已经生成的成果不会被重新生成或覆盖。" : sourceLocationPresentation === "unverified" ? "查找位置后系统继续检查成果；原文件不会被修改，也不会执行外部动作。" : sourceLocationPresentation === "terminal" ? "新任务会重新查找这条说明的位置；旧任务、已有结果和原文件保持不变。" : "已有成果版本和已完成分支不会被覆盖；当前仍是只读核对，不修改文件，也不执行外部动作。"}</span></footer>
      </section>}
      {selectedRound.next_step && <footer className={selectedRound.next_step.decision === "completed" ? "is-complete" : "is-next"}><div><span>{sourceLocationPresentation ? "当前状态" : "服务端决定"}</span><strong>{selectedRoundGateLabel}</strong><p>{sourceLocationPresentation === "verified" ? "成果文件已经通过检查；这条 Agent 说明仍需找到原表格位置并由人复核。" : sourceLocationPresentation === "unverified" ? "成果还不能确认；系统需要先找到说明对应的原表格位置。" : sourceLocationPresentation === "terminal" ? "旧任务不能原地继续；需要创建新的独立任务查找说明位置。" : selectedRound.next_step.reason}</p></div>{selectedRound.next_step.decision === "waiting_input" ? <b>{sourceLocationPresentation === "verified" ? "只处理说明位置" : guidedRecovery ? "选择上方动作继续" : "选择上方分支继续"}</b> : boundedTerminalRecovery ? <b>{sourceLocationPresentation === "terminal" ? "创建新任务继续" : "选择上方分支创建新任务"}</b> : selectedRound.next_step.decision === "next_round" ? <IconArrowRight aria-hidden="true" /> : null}</footer>}
    </article>}
    {run.artifact_versions.length > 0 && <section className="artifact-evolution" aria-label="成果版本">
      <header><div><span>不可变成果历史</span><h3>每轮形成一个可追溯版本</h3></div><b>{currentArtifactVersion ? `当前 v${currentArtifactVersion}` : "尚未提交"}</b></header>
      <ol>{run.artifact_versions.map((artifact) => <li key={`${artifact.artifact_id}:${artifact.version}`} className={currentArtifactVersion === artifact.version ? "is-current" : ""}><span>v{artifact.version}</span><div><b>{currentArtifactVersion === artifact.version ? "当前版本" : artifact.status === "verified" ? "已核对" : "阶段草稿"}</b><p>第 {artifact.round_number} 轮 · {artifact.finding_count} 条发现 · {artifact.source_file_refs.length} 份引用</p></div>{terminal && currentArtifactVersion !== artifact.version && <button type="button" title={`恢复为成果版本 v${artifact.version}`} onClick={() => void onControl("rollback", { artifactVersion: artifact.version })} disabled={controlBusy !== null}><IconRefresh aria-hidden="true" />{controlBusy === "rollback" ? "恢复中" : "恢复"}</button>}</li>)}</ol>
      {run.last_commit && <footer><IconCircleCheck aria-hidden="true" /><span>{run.last_commit.summary}</span><b>{run.commits.length} 次提交记录</b></footer>}
    </section>}
    {run.brief && <section className={`loop-brief is-${run.brief.outcome}`}><IconCircleCheck aria-hidden="true" /><div><span>任务简报</span><h3>{run.brief.summary}</h3><p>外部动作：未发生 · 结果仍需人工复核</p></div></section>}
    {verifiedEffectReady && effectConclusionArtifact && <section className={`loop-effect-conclusion${businessGateOutcome && businessGateOutcome.status !== "passed" ? " is-business-blocked" : candidateReviewOutcome || financeReviewOutcome || outboundFlowOutcome || customerSegmentationOutcome ? " is-human-review" : ""}`} aria-label="本次任务结语">{businessGateOutcome && businessGateOutcome.status !== "passed" || candidateReviewOutcome || financeReviewOutcome || outboundFlowOutcome || customerSegmentationOutcome ? <IconAlertTriangle aria-hidden="true" /> : <IconShieldCheck aria-hidden="true" />}<div><span>{businessGateOutcome && businessGateOutcome.status !== "passed" ? "业务结论" : candidateReviewOutcome ? "招聘辅助结论" : financeReviewOutcome ? "财务复核结论" : outboundFlowOutcome ? "流程设计结论" : customerSegmentationOutcome ? "画像清洗与策略草案" : "本次任务结语"}</span><h3>{businessGateOutcome && businessGateOutcome.status !== "passed" ? businessGateOutcome.decision : candidateReviewOutcome ? candidateReviewOutcome.decision : financeReviewOutcome ? financeReviewOutcome.decision : outboundFlowOutcome ? outboundFlowOutcome.decision : customerSegmentationOutcome ? customerSegmentationOutcome.decision : effectConclusionArtifact.execution_summary}</h3><p>{businessGateOutcome && businessGateOutcome.status !== "passed" ? businessGateOutcome.summary : candidateReviewOutcome ? candidateReviewOutcome.summary : financeReviewOutcome ? financeReviewOutcome.summary : outboundFlowOutcome ? "这是一份流程设计，不是拨号、CRM/短信执行，也不是法律意见。" : customerSegmentationOutcome ? "这是公开样本的清洗和画像事实；重复口径、策略内容与真实客户适用性仍待销售负责人复核。" : effectConclusionArtifact.review_guidance}</p></div><b>{businessGateOutcome && businessGateOutcome.status !== "passed" ? `业务 Gate ${businessGateOutcome.failed_gate_count}/${businessGateOutcome.total_gate_count} 未通过` : candidateReviewOutcome ? "最终 HR 决定尚未发生" : financeReviewOutcome ? "最终财务处置尚未发生" : outboundFlowOutcome ? "最终合规审批与真实动作均未发生" : customerSegmentationOutcome ? "策略审批与客户动作均未发生" : artifactCheckSummary.sameChecklist ? `${run.workspace_artifacts.length} 份成果共享 ${totalArtifactChecks} 项规则检查，${passedArtifactChecks}/${totalArtifactChecks} 通过` : artifactCheckSummary.shared ? `${run.workspace_artifacts.length} 份成果共 ${totalArtifactChecks} 项唯一规则检查，${passedArtifactChecks}/${totalArtifactChecks} 通过` : `${passedArtifactChecks}/${totalArtifactChecks} 项规则检查通过`}</b></section>}
  </section>;
}

function formatBusinessValue(value: number, unit: BusinessGate["unit"] | BusinessMetric["unit"]): string {
  return unit === "percent" ? `${value.toFixed(1)}%` : `${value} 项`;
}

function BusinessGateOutcomePanel({ outcome }: { outcome: BusinessGateOutcome }) {
  const riskLabels: Record<BusinessRecord["final_risk_level"], string> = { none: "无风险项", minor: "次要", major: "主要", severe: "严重" };
  const riskCounts = outcome.records.reduce((counts, record) => ({ ...counts, [record.final_risk_level]: counts[record.final_risk_level] + 1 }), { none: 0, minor: 0, major: 0, severe: 0 });
  const invalid = outcome.status === "invalid";
  const blocked = outcome.status === "failed";
  const legalReview = outcome.outcome_kind === "legal_delegation_review";
  return <section className={`business-gate-outcome is-${outcome.status}`} aria-label="业务 Gate 结论" role="status">
    <header>
      {outcome.status === "passed" ? <IconCircleCheck aria-hidden="true" /> : <IconAlertTriangle aria-hidden="true" />}
      <div><span>{invalid ? "来源数据未通过校验" : "业务 Gate 结论"}</span><h3>{outcome.decision}</h3><p>{outcome.summary}</p></div>
      <b>{invalid ? "不能形成结论" : blocked ? `${outcome.failed_gate_count}/${outcome.total_gate_count} 条未通过` : `${outcome.total_gate_count}/${outcome.total_gate_count} 条通过`}</b>
    </header>
    {outcome.gates.length > 0 && <ol className="business-gate-list">{outcome.gates.map((gate, index) => <li key={gate.gate_id} className={gate.passed ? "is-passed" : "is-failed"}>
      <div className="business-gate-number"><span>{index + 1}</span>{gate.passed ? <IconCheck aria-hidden="true" /> : <IconAlertTriangle aria-hidden="true" />}</div>
      <div><span>{legalReview ? "法务判断条件" : "正式上线条件"}</span><h4>{gate.label}</h4><strong>{formatBusinessValue(gate.actual, gate.unit)} <small>{gate.operator === ">=" ? "至少" : gate.operator === "==" ? "必须等于" : "至多"} {formatBusinessValue(gate.threshold, gate.unit)}</small></strong><p>{gate.result}</p><small>{gate.formula}</small></div>
    </li>)}</ol>}
    {outcome.auxiliary_metrics.length > 0 && <details className="business-metrics"><summary><IconEye aria-hidden="true" />查看辅助质量指标<span>不作为{legalReview ? "法务判断" : "正式上线"} Gate</span></summary><ul>{outcome.auxiliary_metrics.map((metric) => <li key={metric.metric_id}><div><b>{metric.label}</b><small>{metric.formula}</small></div><strong>{formatBusinessValue(metric.value, metric.unit)}</strong><p>{metric.numerator}/{metric.denominator}</p></li>)}</ul></details>}
    {outcome.records.length > 0 && <details className="business-ledger"><summary><IconEye aria-hidden="true" />查看 18 项逐功能台账<span>严重 {riskCounts.severe} · 主要 {riskCounts.major} · 次要 {riskCounts.minor} · 无风险项 {riskCounts.none}</span></summary><ol>{outcome.records.map((record) => <li key={record.record_id} className={`is-${record.final_risk_level}`}>
      <header><b>{record.record_id}</b><div><h4>{record.title}</h4><p>{record.module} · {record.priority} · 负责人 {record.owner}</p></div><strong>{riskLabels[record.final_risk_level]}</strong></header>
      <dl><div><dt>测试与兼容</dt><dd>{record.test_status} · {record.passed_cases}/{record.total_cases} 用例通过 · {record.compatibility_issue_count} 个异常环境</dd></div><div><dt>为什么这样判</dt><dd>{record.rules_hit.length > 0 ? record.rules_hit.join("；") : "当前来源未命中风险规则。"}</dd></div><div><dt>整改与退出</dt><dd>{record.remediation_action} {record.exit_condition}</dd></div><div><dt>来源位置</dt><dd>{record.source_locations.join("；")}</dd></div></dl>
    </li>)}</ol></details>}
    <footer><IconShieldCheck aria-hidden="true" /><span>{legalReview ? "确定性检查只复核来源、规则计算和成果结构；不是正式法律意见，也没有签署或使授权生效。" : "确定性检查只复核公式、来源归属和成果结构；本次没有执行上线、没有修改配置。"}</span></footer>
  </section>;
}

function legalDocumentRiskLabel(level: LegalDocumentReview["highest_triggered_level"]): string {
  return { none: "无已触发风险", low: "低风险文件", medium: "中风险文件", high: "高风险文件" }[level];
}

function legalRuleLevelLabel(level: LegalRuleAssessment["rule_level"]): string {
  return { low: "低", medium: "中", high: "高" }[level];
}

function legalAssessmentStatusLabel(status: LegalRuleAssessment["status"]): string {
  return { triggered: "已触发", not_triggered: "当前未触发", unverifiable: "资料不足" }[status];
}

function legalSigningEvidenceLabel(outcome: LegalReviewOutcome): string {
  if (outcome.signing_evidence_count === 0) return "没有可核对签署证据";
  if (outcome.signing_evidence_count === outcome.document_count) return "全部文件发现可核对签署证据";
  return "部分文件发现可核对签署证据";
}

function LegalReviewOutcomePanel({ outcome, deterministicPassed }: { outcome: LegalReviewOutcome; deterministicPassed: boolean }) {
  return <section className={`legal-review-outcome is-${outcome.status}`} aria-label="授权委托书核查结论">
    <header>
      <IconAlertTriangle aria-hidden="true" />
      <div><span>法务核查结论</span><h3>{outcome.decision}</h3><p>{outcome.summary}</p></div>
      <b>{outcome.high_risk_document_count} 份高风险 · {outcome.critical_unverifiable_count} 项关键资料不足</b>
    </header>
    <ol className="legal-review-statuses" aria-label="文件核验、法务判断与签署状态">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>文件与计算</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>{deterministicPassed ? `${outcome.document_count} 份文件、${outcome.rule_count} 条规则、${outcome.assessment_count} 项核查已完成结构复核。` : "成果文件或核查台账未通过服务端验证，不能采用。"}</p></div></li>
      <li className={outcome.status === "cleared" ? "is-passed" : "is-failed"}><span>2</span><div><b>法务风险</b><strong>{outcome.status === "cleared" ? "法务 Gate 已通过" : "法务 Gate 未通过"}</strong><p>{outcome.high_risk_document_count} 份高风险，{outcome.medium_risk_document_count} 份中风险，{outcome.low_risk_document_count} 份低风险。</p></div></li>
      <li className={outcome.signing_status === "evidence_present" && !outcome.human_review_required ? "is-passed" : "is-pending"}><span>3</span><div><b>签署与人工复核</b><strong>{legalSigningEvidenceLabel(outcome)}</strong><p>{outcome.signing_evidence_count}/{outcome.document_count} 份发现签署对象；仍需法务人员逐项复核，当前没有签署、授权生效或外部动作。</p></div></li>
    </ol>
    <section className="legal-review-summary" aria-label="六份文件核查摘要">
      <div><span>逐项覆盖</span><strong>{outcome.assessment_count}/{outcome.document_count * outcome.rule_count}</strong><p>每份文件都按 21 条来源规则核查</p></div>
      <div><span>签署证据</span><strong>{outcome.signing_evidence_count}/{outcome.document_count}</strong><p>空签署栏不算签字或盖章</p></div>
      <div><span>人工复核</span><strong>{outcome.human_review_required ? "必须" : "无需"}</strong><p>资料不足不会被 Agent 猜测为通过</p></div>
    </section>
    <div className="legal-review-documents">{outcome.documents.map((document) => {
      const attentionItems = document.assessments.filter((assessment) => assessment.status !== "not_triggered");
      return <details key={document.document_id} className={`is-${document.highest_triggered_level}`}>
        <summary>
          <span><b>{document.document_id}</b><strong>{document.document_name}</strong></span>
          <span><em>{legalDocumentRiskLabel(document.highest_triggered_level)}</em><small>{document.triggered_count} 条已触发 · {document.unverifiable_count} 条资料不足</small></span>
          <IconChevronDown aria-hidden="true" />
        </summary>
        <p>{document.summary}</p>
        <ol aria-label={`${document.document_name} 的 21 条规则核查`}>{document.assessments.map((assessment) => <li key={assessment.assessment_id} className={`is-${assessment.status}`}>
          <header><span><b>{assessment.rule_id}</b><strong>{assessment.rule_name}</strong></span><span><em>规则等级：{legalRuleLevelLabel(assessment.rule_level)}</em><mark>{legalAssessmentStatusLabel(assessment.status)}</mark></span></header>
          <dl><div><dt>原文位置</dt><dd>{assessment.source_locator}</dd></div><div><dt>原文摘录</dt><dd>{assessment.excerpt}</dd></div><div><dt>来源事实</dt><dd>{assessment.fact}</dd></div><div><dt>规则判断</dt><dd>{assessment.judgment}</dd></div><div><dt>为什么</dt><dd>{assessment.reason}</dd></div><div><dt>处理与退出</dt><dd>{assessment.owner}：{assessment.remediation_action}；{assessment.exit_condition}</dd></div></dl>
        </li>)}</ol>
        <footer><span>共 21 项：{attentionItems.length} 项需要关注，{21 - attentionItems.length} 项在当前来源下未触发。</span></footer>
      </details>;
    })}</div>
    <footer><IconShieldCheck aria-hidden="true" /><span>这是固定 Legal-020 资料的辅助核查。它不构成正式法律意见，不证明签署有效，不代表授权已生效。</span></footer>
  </section>;
}

function candidateAssessmentStatusLabel(status: CandidateConditionAssessment["status"]): string {
  return {
    met: "有来源支持",
    not_met: "明确不满足",
    unverifiable: "资料不足",
    human_exception_required: "需人工例外判断",
  }[status];
}

function candidateRecommendationLabel(recommendation: CandidateRoleReview["recommendation"]): string {
  return {
    recommended_for_human_review: "建议进入人工复核",
    explicit_hard_gap: "存在明确硬条件缺口",
    insufficient_evidence: "资料不足，需补证",
    exception_review_required: "需决定是否适用例外",
  }[recommendation];
}

function candidateConditionTypeLabel(type: CandidateConditionAssessment["condition_type"]): string {
  return {
    responsibility: "岗位职责",
    default_threshold: "默认门槛",
    required: "必要项",
    preferred: "优先项",
    bonus: "加分项",
  }[type];
}

function CandidateReviewOutcomePanel({ outcome, deterministicPassed }: { outcome: CandidateReviewOutcome; deterministicPassed: boolean }) {
  const roles = Array.from(new Set(outcome.reviews.map((review) => review.role_id)));
  return <section className={`candidate-review-outcome is-${outcome.status}`} aria-label="双岗位候选人辅助筛选结论">
    <header>
      <IconAlertTriangle aria-hidden="true" />
      <div><span>招聘辅助筛选</span><h3>{outcome.decision}</h3><p>{outcome.summary}</p></div>
      <b>{outcome.review_count} 组岗位匹配 · 全部待 HR 决定</b>
    </header>
    <ol className="candidate-review-statuses" aria-label="确定性验证、岗位建议与最终招聘决定">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>来源与成果</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>{deterministicPassed ? `${outcome.role_count} 份 JD、${outcome.candidate_count} 份简历与 ${outcome.assessment_count} 条条件已由服务端重算。` : "来源、解析或成果结构未通过验证，当前建议不能采用。"}</p></div></li>
      <li className="is-review"><span>2</span><div><b>岗位匹配建议</b><strong>有依据，也有缺口</strong><p>有来源支持 {outcome.met_count} 条 · 明确不满足 {outcome.not_met_count} 条 · 资料不足 {outcome.unverifiable_count} 条 · 需例外判断 {outcome.human_exception_count} 条</p></div></li>
      <li className="is-pending"><span>3</span><div><b>最终 HR 决定</b><strong>尚未发生</strong><p>本轮没有录用、淘汰、通知候选人或写入 ATS；所有建议都要由招聘人员复核。</p></div></li>
    </ol>
    <section className="candidate-review-summary" aria-label="岗位匹配建议汇总">
      <div><span>建议人工复核</span><strong>{outcome.recommended_for_human_review_count}</strong><p>只表示必要项已有来源支持</p></div>
      <div><span>明确硬条件缺口</span><strong>{outcome.explicit_hard_gap_count}</strong><p>仍不是自动淘汰决定</p></div>
      <div><span>资料不足</span><strong>{outcome.insufficient_evidence_count}</strong><p>缺失不会被推断为否定</p></div>
      <div><span>人工例外</span><strong>{outcome.exception_review_required_count}</strong><p>服务端不会替 HR 适用例外</p></div>
    </section>
    <div className="candidate-review-roles">{roles.map((roleId) => {
      const reviews = outcome.reviews.filter((review) => review.role_id === roleId);
      const roleName = reviews[0]?.role_name ?? roleId;
      return <section key={roleId} aria-label={`${roleName}岗位候选人建议`}>
        <header><div><span>岗位</span><h4>{roleName}</h4></div><b>{reviews.length} 名候选人</b></header>
        <div className="candidate-review-candidates">{reviews.map((review) => <details key={review.review_id} className={`is-${review.recommendation}`}>
          <summary>
            <span><b>{review.candidate_id}</b><strong>{review.candidate_name}</strong></span>
            <span><em>{candidateRecommendationLabel(review.recommendation)}</em><small>支持 {review.met_count} · 缺口 {review.not_met_count} · 资料不足 {review.unverifiable_count} · 例外 {review.human_exception_count}</small></span>
            <IconChevronDown aria-hidden="true" />
          </summary>
          <p>{review.summary}</p>
          <ol aria-label={`${review.candidate_name}在${roleName}岗位的逐条件核对`}>{review.assessments.map((assessment) => <li key={assessment.assessment_id} className={`is-${assessment.status}`}>
            <header><span><b>{assessment.condition_id}</b><strong>{assessment.condition_label}</strong></span><span><em>{candidateConditionTypeLabel(assessment.condition_type)}</em><mark>{candidateAssessmentStatusLabel(assessment.status)}</mark></span></header>
            <dl>
              <div><dt>JD 原文</dt><dd><b>{assessment.jd_locator}</b>{assessment.jd_excerpt}</dd></div>
              <div><dt>简历原文</dt><dd><b>{assessment.resume_locator}</b>{assessment.resume_excerpt}</dd></div>
              <div><dt>来源事实</dt><dd>{assessment.fact}</dd></div>
              <div><dt>服务端判断</dt><dd>{assessment.judgment} {assessment.reason}</dd></div>
              <div><dt>面试或补证</dt><dd>{assessment.review_action}</dd></div>
              <div><dt>责任与退出</dt><dd>{assessment.owner}：{assessment.exit_condition}</dd></div>
            </dl>
          </li>)}</ol>
        </details>)}</div>
      </section>;
    })}</div>
    <footer><IconShieldCheck aria-hidden="true" /><span>固定 hr-001 辅助筛选只核对公开 JD 与简历事实。它不是正式录用决定、背景调查或公平性证明。</span></footer>
  </section>;
}

function formatFinanceAmount(value: string): string {
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(parsed)
    : value;
}

function FinanceReviewOutcomePanel({ outcome, deterministicPassed }: { outcome: FinanceReviewOutcome; deterministicPassed: boolean }) {
  const hasCandidates = outcome.candidate_count > 0;
  return <section className={`finance-review-outcome is-${hasCandidates ? "candidates" : "clear"}`} aria-label="跨期往来风险候选复核结论">
    <header>
      <IconAlertTriangle aria-hidden="true" />
      <div><span>财务复核结论</span><h3>这是跨期风险候选，不是付款、核销、记账或坏账确认</h3><p>{outcome.decision}</p></div>
      <b>{hasCandidates ? `发现 ${outcome.candidate_count} 条候选` : "当前 0 条候选"}</b>
    </header>
    <ol className="finance-review-statuses" aria-label="确定性验证、风险候选与最终财务处置">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>来源、计算与成果</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>{deterministicPassed ? "三个固定期间、两张 2026 明细和跨期说明均由服务端重新解析复算。" : "来源或成果没有通过服务端复算，当前文件不得采用。"}</p></div></li>
      <li className={hasCandidates ? "is-review" : "is-clear"}><span>2</span><div><b>跨期风险候选</b><strong>{hasCandidates ? `发现 ${outcome.candidate_count} 条，需财务复核` : "当前启发式未发现候选"}</strong><p>{hasCandidates ? "候选不是业务定论；展开可查看三期金额和原表位置。" : "没有发现候选也不等于账务无风险，仍需财务人员复核。"}</p></div></li>
      <li className="is-pending"><span>3</span><div><b>最终财务处置</b><strong>尚未发生</strong><p>本轮没有付款、核销、记账或坏账确认，也没有修改 FORTE 原始工作簿。</p></div></li>
    </ol>
    <section className="finance-review-summary" aria-label="2026 期末与跨期候选摘要">
      <div><span>2026 期末未付</span><strong>{outcome.unpaid_count} 条</strong><p>正数贷方期末余额 · 合计 {formatFinanceAmount(outcome.unpaid_total)}</p></div>
      <div><span>2026 期末未收</span><strong>{outcome.unreceived_count} 条</strong><p>正数借方期末余额 · 合计 {formatFinanceAmount(outcome.unreceived_total)}</p></div>
      <div className={hasCandidates ? "is-candidate" : ""}><span>三期风险候选</span><strong>{outcome.candidate_count} 条</strong><p>{hasCandidates ? "需逐项财务复核" : "当前启发式未发现"}</p></div>
    </section>
    {hasCandidates ? <div className="finance-review-candidates" aria-label="僵尸账款候选明细">{outcome.candidates.map((candidate) => <details key={candidate.candidate_id}>
      <summary><span><b>{candidate.subject}</b><strong>{candidate.customer}</strong></span><span><em>需财务复核</em><small>三期金额完全相同</small></span><IconChevronDown aria-hidden="true" /></summary>
      <ol>{candidate.sources.map((source) => <li key={`${candidate.candidate_id}:${source.period_id}`}><span>{source.period_label}</span><strong>{formatFinanceAmount(source.ending_balance)}</strong><p>{source.file_name}</p><code>{source.locator}</code></li>)}</ol>
      <dl><div><dt>复核动作</dt><dd>{candidate.review_action}</dd></div><div><dt>退出条件</dt><dd>{candidate.exit_condition}</dd></div></dl>
    </details>)}</div> : <section className="finance-review-empty"><IconShieldCheck aria-hidden="true" /><div><strong>当前启发式未发现候选，仍需财务复核</strong><p>0 条候选只表示三期“正数借方期末余额完全相同”的固定条件没有命中。</p></div></section>}
    <details className="finance-review-method"><summary><IconEye aria-hidden="true" />查看方法、局限与处置边界</summary><div><p><b>方法</b>{outcome.method}</p><ul>{outcome.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div></details>
    <footer><IconShieldCheck aria-hidden="true" /><span>固定 Finance-018 启发式适配器只生成可复核候选。最终判断和会计处理必须由财务人员完成。</span></footer>
  </section>;
}

const OUTBOUND_GROUP_LABELS: Record<OutboundRule["group"], string> = {
  TIME: "允许外呼时段", FREQ: "拨打频次", RECORD: "录音与保存", IDENTITY: "身份确认顺序",
  THIRD_PARTY: "第三方边界", PROHIBIT: "禁用话术", CONNECT: "接通与未接通", PTP: "承诺还款",
  SOFT: "软拒绝", HARD: "硬拒绝", DISPUTE: "投诉与异议", INVALID: "无效通话",
  TERMINAL: "流程终态", PAYMENT: "还款引导", REDIAL: "重拨间隔",
};

const OUTBOUND_PARAMETER_LABELS: Record<string, string> = {
  prohibited_start: "禁呼开始", prohibited_end: "允许开始", daily_call_max: "每日上限", hourly_window: "频次窗口",
  hourly_call_max: "窗口上限", recording_retention: "录音保存", emotion_transfer_threshold: "情绪阈值",
  redial_min_interval: "重拨间隔", source_terminal_count: "来源终态", identity_recording_order: "身份与录音顺序",
};

function OutboundFlowOutcomePanel({ outcome, deterministicPassed }: { outcome: OutboundFlowOutcome; deterministicPassed: boolean }) {
  const integrityPassed = Object.values(outcome.graph_integrity).every(Boolean);
  const completeCoverage = outcome.unsupported_count === 0 && outcome.conflict_count === 0;
  const groups = Object.entries(outcome.rules.reduce<Record<string, OutboundRule[]>>((result, rule) => {
    (result[rule.group] ??= []).push(rule);
    return result;
  }, {}));
  return <section className={`outbound-flow-outcome is-${outcome.status}`} aria-label="合规外呼流程设计复核结论">
    <header>
      <IconRoute aria-hidden="true" />
      <div><span>流程设计结论</span><h3>这是流程设计，不是拨号、CRM/短信执行，也不是法律意见</h3><p>{outcome.decision}</p></div>
      <b>{outcome.status === "approval_required" ? "等待业务与合规审批" : "规则或图结构未通过"}</b>
    </header>
    <ol className="outbound-flow-statuses" aria-label="来源验证、规则覆盖、审批与执行状态">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>来源与 DOCX</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>服务端从批准 Markdown 重新推导规则，并解析生成后的 DOCX 逐表核对。</p></div></li>
      <li className={completeCoverage && integrityPassed ? "is-passed" : "is-failed"}><span>2</span><div><b>规则覆盖与状态图</b><strong>{outcome.covered_count}/{outcome.atomic_requirement_count} 条覆盖 · {outcome.reachable_terminal_count}/{outcome.terminal_count} 个终态可达</strong><p>{completeCoverage && integrityPassed ? "当前未发现静默忽略、冲突或不可达路径。" : `不支持 ${outcome.unsupported_count} 条，冲突 ${outcome.conflict_count} 条，需要修复设计。`}</p></div></li>
      <li className="is-review"><span>3</span><div><b>最终合规审批</b><strong>尚未发生</strong><p>来源未提供制度版本或批准主体，业务与合规负责人仍需核对当前有效口径。</p></div></li>
      <li className="is-pending"><span>4</span><div><b>真实系统动作</b><strong>全部未发生</strong><p>未拨号、未写 CRM、未发短信、未写禁呼名单，也未实际转人工。</p></div></li>
    </ol>
    <section className="outbound-flow-summary" aria-label="规则和状态图摘要">
      <div><span>来源规则</span><strong>{outcome.source_rule_group_count} 组 · {outcome.atomic_requirement_count} 条</strong><p>逐条保留原文行号与映射位置</p></div>
      <div><span>状态图</span><strong>{outcome.node_count} 节点 · {outcome.edge_count} 边</strong><p>{outcome.guard_count} 个守卫条件</p></div>
      <div><span>终态可达</span><strong>{outcome.reachable_terminal_count}/{outcome.terminal_count}</strong><p>均从唯一 START 可遍历到达</p></div>
    </section>
    <section className="outbound-flow-parameters" aria-label="来源动态参数">
      {outcome.parameters.map((parameter) => <div key={parameter.name}><span>{OUTBOUND_PARAMETER_LABELS[parameter.name] ?? parameter.name}</span><strong>{parameter.value}{parameter.unit ? ` ${parameter.unit}` : ""}</strong></div>)}
    </section>
    <details className="outbound-flow-rules"><summary><IconEye aria-hidden="true" /><span><b>逐条查看来源规则与流程映射</b><small>{groups.length} 组规则，默认折叠</small></span><IconChevronDown aria-hidden="true" /></summary><div className="outbound-flow-rule-groups">{groups.map(([group, rules]) => <details key={group}>
      <summary><span><b>{OUTBOUND_GROUP_LABELS[group as OutboundRule["group"]] ?? group}</b><small>{rules.length} 条</small></span><IconChevronDown aria-hidden="true" /></summary>
      <ol>{rules.map((rule) => <li key={rule.rule_id} className={`is-${rule.coverage_state}`}>
        <header><code>{rule.rule_id}</code><b>{rule.coverage_state === "covered" ? "已覆盖" : rule.coverage_state === "unsupported" ? "暂不支持" : "存在冲突"}</b></header>
        <blockquote>{rule.excerpt}</blockquote>
        <dl><div><dt>原文位置</dt><dd>{rule.locator}</dd></div><div><dt>流程要求</dt><dd>{rule.expected_action}</dd></div><div><dt>映射位置</dt><dd>{[...rule.mapped_node_ids, ...rule.mapped_edge_ids, ...rule.mapped_guard_ids, ...rule.mapped_terminal_ids].join("、") || "尚未映射"}</dd></div></dl>
      </li>)}</ol>
    </details>)}</div></details>
    <details className="outbound-flow-terminals"><summary><IconRoute aria-hidden="true" />查看可达终态与图完整性</summary><div><ul>{outcome.terminals.map((terminal) => <li key={terminal.terminal_id}><b>{terminal.label}</b><small>{terminal.source_listed ? "来源列出" : "安全补充终态"}</small></li>)}</ul><p>{outcome.summary}</p></div></details>
    <footer><IconShieldCheck aria-hidden="true" /><span>固定 Operations-008 流程设计适配器，不是外呼系统、最新监管验证或生产审批工具。</span></footer>
  </section>;
}

function customerSampleStatus(sample: CustomerSampleDecision): string {
  if (sample.duplicate_of) return `精确重复，保留样本 ${sample.duplicate_of}`;
  if (sample.exclusion_reason === "unclassified") return "未命中画像，已排除";
  return sample.final_label ?? "待复核";
}

function CustomerSegmentationOutcomePanel({ outcome, deterministicPassed }: { outcome: CustomerSegmentationOutcome; deterministicPassed: boolean }) {
  const profileEntries = Object.entries(outcome.profile_counts);
  return <section className={`customer-segmentation-outcome is-${outcome.status}`} aria-label="客户画像清洗与销售策略草案复核">
    <header>
      <IconAdjustments aria-hidden="true" />
      <div><span>公开样本清洗与画像</span><h3>这是画像清洗与策略草案，不是真实客户研究、销售效果证明或 CRM 执行</h3><p>{outcome.decision}</p></div>
      <b>{outcome.source_row_count} 个原始行 · {outcome.classified_count} 条分类</b>
    </header>
    <ol className="customer-segmentation-statuses" aria-label="来源验证、清洗事实、策略复核与外部动作">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>来源与两份成果</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>{deterministicPassed ? "服务端重新读取问卷和规则，再解析最终 Markdown 与 CSV 逐字段核对。" : "来源、清洗或成果结构未通过验证，当前分类不得采用。"}</p></div></li>
      <li className="is-review"><span>2</span><div><b>画像清洗事实</b><strong>{outcome.classified_count} 条分类 · {outcome.excluded_count} 条排除</strong><p>重复口径是公开假设，canonical 中多标签优先级 witness 为 {outcome.priority_witness_count} 个。</p></div></li>
      <li className="is-pending"><span>3</span><div><b>销售策略草案</b><strong>待销售负责人补充和批准</strong><p>规则只批准报告栏目，没有批准话术、主推功能、行业结论或销售优先级。</p></div></li>
      <li className="is-pending"><span>4</span><div><b>客户与 CRM 动作</b><strong>全部未发生</strong><p>未联系客户、未写 CRM、未创建商机，也未触发任何营销动作。</p></div></li>
    </ol>
    <section className="customer-segmentation-summary" aria-label="画像清洗动态摘要">
      <div><span>原始行</span><strong>{outcome.source_row_count}</strong><p>{outcome.unique_payload_count} 条唯一业务载荷</p></div>
      <div><span>精确重复</span><strong>{outcome.duplicate_count}</strong><p>按 exact_non_id_payload 保留第一条</p></div>
      <div><span>完成分类</span><strong>{outcome.classified_count}</strong><p>{profileEntries.map(([label, count]) => `${label} ${count}`).join(" · ")}</p></div>
      <div><span>无法归类</span><strong>{outcome.unclassified_count}</strong><p>连同重复共排除 {outcome.excluded_count} 条</p></div>
    </section>
    <article className="customer-segmentation-assumption"><IconAlertTriangle aria-hidden="true" /><div><b>重复口径仍需业务确认</b><p>来源只说“重复保留第一条”，没有定义重复键。当前固定适配器仅把除样本 ID 外所有原始字段完全相同视为重复。</p></div></article>
    <div className="customer-segmentation-samples" aria-label="逐样本清洗与画像裁决">{outcome.samples.map((sample) => <details key={`${sample.sample_id}:${sample.source_row}`} className={sample.duplicate_of ? "is-duplicate" : sample.exclusion_reason ? "is-excluded" : "is-classified"}>
      <summary><span><b>样本 {sample.sample_id}</b><strong>{customerSampleStatus(sample)}</strong></span><span><small>{sample.industry} · {sample.company_size}</small><em>{sample.source_locator}</em></span><IconChevronDown aria-hidden="true" /></summary>
      <dl>
        <div><dt>原始评分</dt><dd>{Object.entries(sample.raw_scores).map(([field, value]) => `${field}=${value || "空"}`).join(" · ")}</dd></div>
        <div><dt>清洗评分</dt><dd>{Object.entries(sample.cleaned_scores).map(([field, value]) => `${field}=${value}`).join(" · ")}</dd></div>
        <div><dt>清洗转换</dt><dd>{sample.transformations.length > 0 ? sample.transformations.join("；") : "无需转换"}</dd></div>
        <div><dt>画像命中</dt><dd>{sample.matched_profiles.length > 0 ? sample.matched_profiles.join("、") : "未命中"}{sample.priority_applied ? `；按 ${outcome.parameters.profile_priority.join(" > ")} 选出唯一标签` : "；未触发多标签优先级"}</dd></div>
        <div><dt>最终处理</dt><dd>{customerSampleStatus(sample)}</dd></div>
        <div><dt>来源规则</dt><dd>{sample.rule_refs.join("、")}</dd></div>
      </dl>
    </details>)}</div>
    <details className="customer-segmentation-rules"><summary><IconEye aria-hidden="true" /><span><b>查看来源规则与动态参数</b><small>{outcome.rules.length} 条规则 · 缺失值={outcome.parameters.missing_score_default} · 优先级 {outcome.parameters.profile_priority.join(" > ")}</small></span><IconChevronDown aria-hidden="true" /></summary><ol>{outcome.rules.map((rule) => <li key={rule.rule_id}><header><code>{rule.rule_id}</code><b>{rule.locator}</b></header><blockquote>{rule.excerpt}</blockquote><p>{rule.parameters.join(" · ") || "无额外参数"}</p></li>)}</ol></details>
    <footer><IconShieldCheck aria-hidden="true" /><span>固定 Sales-020 公开样本适配器。重复口径和策略内容仍需业务负责人批准，不是 CRM、自动营销、真实客户研究或通用分群引擎。</span></footer>
  </section>;
}

function sreFact(value: unknown): string {
  if (Array.isArray(value)) return value.join("、");
  if (value && typeof value === "object") {
    const range = value as Record<string, unknown>;
    if (typeof range.min === "number" && typeof range.max === "number") return `${range.min}-${range.max}`;
    return JSON.stringify(value);
  }
  return String(value ?? "-");
}

function SREDiagnosisOutcomePanel({ outcome, deterministicPassed }: { outcome: SREDiagnosisOutcome; deterministicPassed: boolean }) {
  const proposalCount = outcome.proposal_count + outcome.business_mitigation_count;
  const metricCards = [
    ["查询 QPS", `${sreFact(outcome.metric_facts.query_qps_baseline)} → ${sreFact(outcome.metric_facts.query_qps)}/s`, `${sreFact(outcome.metric_facts.query_qps_multiplier)} 倍`],
    ["写入 QPS", `${sreFact(outcome.metric_facts.write_qps_baseline)} → ${sreFact(outcome.metric_facts.write_qps)}/s`, `${sreFact(outcome.metric_facts.write_qps_multiplier)} 倍`],
    ["节点口径", `${sreFact(outcome.node_facts.declared_count)} 声明 / ${sreFact(outcome.node_facts.listed_count)} 列表`, `${sreFact(outcome.node_facts.listed_master_count)} master · ${sreFact(outcome.node_facts.listed_data_count)} data`],
    ["分片口径", `${sreFact(outcome.cluster_facts.health_unassigned)} health / ${sreFact(outcome.cluster_facts.detail_unassigned)} 明细`, "来源存在冲突"],
  ];
  return <section className={`sre-diagnosis-outcome is-${outcome.status}`} aria-label="SRE 离线事故复盘与止损提案">
    <header>
      <IconDatabase aria-hidden="true" />
      <div><span>SRE 离线复盘</span><h3>这是固定公开日志的离线复盘与止损提案，不是在线监控、根因定论或命令执行回执</h3><p>{outcome.decision}</p></div>
      <b>{outcome.conflict_count} 组冲突待核实</b>
    </header>
    <ol className="sre-diagnosis-statuses" aria-label="成果验证、来源冲突、SRE 复核与实际动作状态">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>来源与两份成果</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>服务端重读批准日志，并独立解析最终 Markdown 和 CSV 逐字段核对。</p></div></li>
      <li className={outcome.conflict_count > 0 ? "is-review" : "is-passed"}><span>2</span><div><b>观察与来源冲突</b><strong>{outcome.observation_count} 条观察 · {outcome.conflict_count} 组冲突</strong><p>确定性通过表示冲突被识别和保留，不表示日志内部数据一致。</p></div></li>
      <li className="is-review"><span>3</span><div><b>假设与动作提案</b><strong>{outcome.hypothesis_count} 个假设 · {proposalCount} 个提案待 SRE 复核</strong><p>生产 endpoint 仍未解析，参数、风险、前置、回滚和验证都需审批。</p></div></li>
      <li className="is-pending"><span>4</span><div><b>真实集群与业务动作</b><strong>全部未发生</strong><p>未连接 Elasticsearch，未执行 HTTP/ES 命令，也未实施限流或查询降级。</p></div></li>
    </ol>
    <section className="sre-diagnosis-summary" aria-label="动态日志事实摘要">{metricCards.map(([label, value, note]) => <div key={label}><span>{label}</span><strong>{value}</strong><p>{note}</p></div>)}</section>
    <article className="sre-diagnosis-target"><IconAlertTriangle aria-hidden="true" /><div><b>命令目标尚未确定</b><p>日志中的 10.1.1.1 是 dedicated master，不能直接拿来发送客户端请求。所有提案都等待 SRE 提供非 dedicated-master 的批准协调入口。</p></div></article>
    <details className="sre-diagnosis-details sre-conflicts" open><summary><IconAlertTriangle aria-hidden="true" /><span><b>查看 {outcome.conflict_count} 组来源冲突</b><small>冲突被识别，不等于已解决</small></span><IconChevronDown aria-hidden="true" /></summary><ol>{outcome.source_conflicts.map((conflict) => <li key={conflict.conflict_id}>
      <header><code>{conflict.conflict_id}</code><b>{conflict.status === "open" ? "待核实" : "已解决"}</b></header><h4>{conflict.title}</h4><p>{conflict.statement}</p><dl><div><dt>来源位置</dt><dd>{conflict.locators.join(" · ")}</dd></div><div><dt>为什么重要</dt><dd>{conflict.impact}</dd></div></dl>
    </li>)}</ol></details>
    <details className="sre-diagnosis-details sre-hypotheses"><summary><IconEye aria-hidden="true" /><span><b>查看假设、支持与反证</b><small>{outcome.hypothesis_count} 个有边界假设</small></span><IconChevronDown aria-hidden="true" /></summary><ol>{outcome.hypotheses.map((hypothesis) => <li key={hypothesis.hypothesis_id}>
      <header><code>{hypothesis.hypothesis_id}</code><b>置信度 {hypothesis.confidence}</b></header><p>{hypothesis.statement}</p><dl><div><dt>支持位置</dt><dd>{hypothesis.supporting_locators.join(" · ")}</dd></div><div><dt>反证/待核实</dt><dd>{hypothesis.counter_evidence_locators.join(" · ") || "无"}</dd></div><div><dt>当前局限</dt><dd>{hypothesis.limitations.join("；")}</dd></div></dl>
    </li>)}</ol></details>
    <details className="sre-diagnosis-details sre-proposals"><summary><IconRoute aria-hidden="true" /><span><b>查看 {proposalCount} 个未执行提案</b><small>{outcome.proposal_count} 个 ES 提案 · {outcome.business_mitigation_count} 个业务止损提案</small></span><IconChevronDown aria-hidden="true" /></summary><ol>{[...outcome.action_proposals, ...outcome.business_mitigations].map((proposal) => <li key={proposal.proposal_id} className={`is-${proposal.risk_level}`}>
      <header><span><code>{proposal.proposal_id}</code><h4>{proposal.title}</h4></span><b>{proposal.risk_level === "high" ? "高风险" : proposal.risk_level === "medium" ? "中风险" : "低风险"} · 未执行</b></header>
      {proposal.command_template ? <pre><code>{proposal.command_template}</code></pre> : <p>{proposal.action_text}</p>}
      <dl><div><dt>目标</dt><dd>{proposal.target_status === "unresolved" ? "未解析，等待批准入口" : "不使用 ES endpoint"}</dd></div><div><dt>前置条件</dt><dd>{proposal.preconditions.join("；")}</dd></div><div><dt>回滚/停止</dt><dd>{proposal.rollback}</dd></div><div><dt>执行后验证</dt><dd>{proposal.verify_after.join("；")}</dd></div>{proposal.official_reference && <div><dt>官方 API 语义参考</dt><dd>{proposal.official_reference}</dd></div>}</dl>
    </li>)}</ol></details>
    <details className="sre-diagnosis-details sre-observations"><summary><IconFileDescription aria-hidden="true" /><span><b>逐条查看日志观察</b><small>{outcome.observation_count} 条 · {outcome.unclassified_count} 条待人工分类</small></span><IconChevronDown aria-hidden="true" /></summary><ol>{outcome.observations.map((observation) => <li key={observation.observation_id} className={observation.status === "unclassified" ? "is-unclassified" : ""}><header><code>{observation.observation_id}</code><b>{observation.category}</b></header><p>{observation.statement}</p><blockquote>{observation.excerpt}</blockquote><small>{observation.locator}</small></li>)}</ol></details>
    <footer><IconShieldCheck aria-hidden="true" /><span>固定 SRE-010 离线复盘适配器。它不是在线监控、根因确定器、Elasticsearch Connector、命令执行器或生产变更审批。</span></footer>
  </section>;
}

function uxRowStatusLabel(status: UXRowDecision["status"]): string {
  return { included: "进入聚合", excluded: "无痛点，计入分母", manual_review: "待人工核对" }[status];
}

function UXPrioritizationOutcomePanel({ outcome, deterministicPassed }: { outcome: UXPrioritizationOutcome; deterministicPassed: boolean }) {
  const [priorityFilter, setPriorityFilter] = useState("ALL");
  const [pageFilter, setPageFilter] = useState("ALL");
  const pages = Array.from(new Set(outcome.groups.map((group) => group.page_name)));
  const visibleGroups = outcome.groups.filter((group) => (priorityFilter === "ALL" || group.priority === priorityFilter) && (pageFilter === "ALL" || group.page_name === pageFilter));
  const visibleRows = outcome.row_decisions.filter((row) => pageFilter === "ALL" || row.page_name === pageFilter);
  const prioritySummary = ["P0", "P1", "P2", "P3", "P4"].map((label) => `${label} ${outcome.priority_counts[label] ?? 0}`).join(" · ");
  return <section className={`ux-prioritization-outcome is-${outcome.status}`} aria-label="交互痛点全量优先级复核">
    <header>
      <IconAdjustments aria-hidden="true" />
      <div><span>UX 离线优先级排序</span><h3>这是固定公开日志的离线排序，不是用户研究、线上遥测、设计效果证明或自动修复</h3><p>{outcome.decision}</p></div>
      <b>{outcome.analyzed_row_count}/{outcome.source_row_count} 行完整覆盖</b>
    </header>
    <ol className="ux-prioritization-statuses" aria-label="来源验证、全量日志、优先级复核与生产动作">
      <li className={deterministicPassed ? "is-passed" : "is-failed"}><span>1</span><div><b>三份来源与两份成果</b><strong>{deterministicPassed ? "确定性检查通过" : "确定性检查未通过"}</strong><p>服务端读取完整 XLSX，并重新解析规则、页面规范和最终两份 CSV 逐字段核对。</p></div></li>
      <li className="is-review"><span>2</span><div><b>完整日志覆盖与数据质量</b><strong>{outcome.included_pain_row_count} 行有痛点 · {outcome.excluded_no_pain_count} 行无痛点</strong><p>{outcome.success_with_pain_count} 行“成功但有痛点”；{outcome.duplicate_group_count} 个重复组未去重，额外重复事件 {outcome.duplicate_extra_count} 条。</p></div></li>
      <li className="is-review"><span>3</span><div><b>优先级与来源边界</b><strong>{outcome.group_count} 组 · {prioritySummary}</strong><p>{outcome.mappings.length} 个映射是受控适配器假设；{outcome.rule_conflicts.length} 组 3% 来源冲突、{outcome.uncovered_spec_count} 个规范元素未覆盖。</p></div></li>
      <li className="is-pending"><span>4</span><div><b>方案批准与生产动作</b><strong>全部尚未发生</strong><p>没有批准的具体优化方案，也没有修改生产界面、发布版本或创建 A/B 实验。</p></div></li>
    </ol>
    <section className="ux-prioritization-summary" aria-label="全量日志动态摘要">
      <div><span>全量分母</span><strong>{outcome.source_row_count}</strong><p>无痛点和成功记录都保留在分母</p></div>
      <div><span>痛点聚合</span><strong>{outcome.group_count}</strong><p>page × operation × pain</p></div>
      <div><span>成功但有痛点</span><strong>{outcome.success_with_pain_count}</strong><p>不能统称为失败记录</p></div>
      <div><span>待复核映射</span><strong>{outcome.mappings.length}</strong><p>{outcome.unmapped_count} 个操作当前未映射</p></div>
    </section>
    {outcome.rule_conflicts.map((conflict) => <article key={conflict.conflict_id} className="ux-prioritization-conflict"><IconAlertTriangle aria-hidden="true" /><div><b>{conflict.title}</b><p>{conflict.statement}</p><small>{conflict.impact} · {conflict.locators.join("、")}</small></div></article>)}
    <nav className="ux-prioritization-filters" aria-label="优先级和页面筛选">
      <div><span>优先级</span>{["ALL", "P0", "P1", "P2", "P3", "P4"].map((label) => <button key={label} type="button" className={priorityFilter === label ? "is-active" : ""} onClick={() => setPriorityFilter(label)}>{label === "ALL" ? "全部" : `${label} ${outcome.priority_counts[label] ?? 0}`}</button>)}</div>
      <div><span>页面</span><select value={pageFilter} onChange={(event) => setPageFilter(event.target.value)} aria-label="按页面筛选"><option value="ALL">全部页面</option>{pages.map((page) => <option key={page} value={page}>{page}</option>)}</select></div>
    </nav>
    <section className="ux-prioritization-groups" aria-label="优先级组合列表">
      <header><div><span>当前视图</span><h4>{visibleGroups.length} 个聚合组合</h4></div><small>P0 是来源矩阵优先级，不代表已经立项。</small></header>
      <div>{visibleGroups.map((group) => <details key={group.group_id} className={`is-${group.priority?.toLowerCase() ?? "ambiguous"}`}>
        <summary><span><b>{group.priority ?? "待确认"}</b><strong>{group.page_name} · {group.operation}</strong><small>{group.pain_type} · {group.scenario_count}/{group.denominator} · {group.frequency}</small></span><span><em>{group.element_name}</em><IconChevronDown aria-hidden="true" /></span></summary>
        <dl>
          <div><dt>规范要求</dt><dd>{group.spec_requirement}</dd></div>
          <div><dt>来源处置</dt><dd>{group.disposition}</dd></div>
          <div><dt>精确占比</dt><dd>{group.ratio}，分母为全部 {group.denominator} 条操作</dd></div>
          <div className="ux-prioritization-rule-refs"><dt>为何这样分级</dt><dd><ol>{group.rule_refs.map((ref) => <li key={`${ref.role}:${ref.rule_id}`}><span>{ref.role === "severity" ? "严重度" : ref.role === "frequency" ? "频率" : "优先级"}{ref.application === "conflict_side" ? "冲突侧" : "已采用"}</span><code>{ref.rule_id}</code><small>{ref.locator}</small></li>)}</ol>{group.priority === null && <p>当前边界存在两种频率解释，因此未应用优先级矩阵规则。</p>}</dd></div>
          <div><dt>映射依据</dt><dd>{group.mapping_basis}</dd></div>
          <div><dt>具体方案</dt><dd>{group.suggestion_template}</dd></div>
          <div><dt>数据质量</dt><dd>{group.data_quality_flags.length > 0 ? group.data_quality_flags.join("、") : "当前贡献行未标记额外问题"}</dd></div>
        </dl>
        <details className="ux-prioritization-locators"><summary>查看 {group.contributing_row_locators.length} 条贡献来源位置</summary><ol>{group.contributing_row_locators.map((locator) => <li key={locator}><code>{locator}</code></li>)}</ol></details>
      </details>)}</div>
    </section>
    <details className="ux-prioritization-rows"><summary><IconFileDescription aria-hidden="true" /><span><b>逐行查看原始日志裁决</b><small>{visibleRows.length} 行 · included / excluded / manual_review 全部保留</small></span><IconChevronDown aria-hidden="true" /></summary><div>{visibleRows.map((row) => <details key={row.row_number} className={`is-${row.status}`}>
      <summary><span><b>第 {row.row_number} 行</b><strong>{row.page_name} · {row.operation}</strong><small>{row.pain_type} · {uxRowStatusLabel(row.status)}</small></span><IconChevronDown aria-hidden="true" /></summary>
      <dl><div><dt>来源位置</dt><dd><code>{row.locator}</code></dd></div><div><dt>结果与原因</dt><dd>{row.operation_result} · {row.failure_reason || "来源未填写失败原因"}</dd></div><div><dt>误触 / 退出 / 重试</dt><dd>{row.misclick_count} / {row.exit_node || "空"} / {row.retry_count}</dd></div><div><dt>服务端处理</dt><dd>{row.reason}</dd></div><div><dt>数据质量</dt><dd>{row.data_quality_flags.join("、") || "无额外标记"}</dd></div>{row.duplicate_group_id && <div><dt>重复事件</dt><dd>{row.duplicate_group_id} · 第 {row.duplicate_ordinal} 条，仍计入分母</dd></div>}</dl>
    </details>)}</div></details>
    <details className="ux-prioritization-rules"><summary><IconEye aria-hidden="true" /><span><b>查看来源规则、页面规范与映射假设</b><small>{outcome.rules.length} 条规则 · {outcome.specs.length} 个规范元素 · {outcome.mappings.length} 个映射</small></span><IconChevronDown aria-hidden="true" /></summary><div><section><h4>来源规则</h4>{outcome.rules.map((rule) => <article key={rule.rule_id}><code>{rule.rule_id}</code><b>{rule.name}</b><p>{rule.excerpt}</p><small>{rule.locator}</small></article>)}</section><section><h4>映射假设</h4>{outcome.mappings.map((mapping) => <article key={mapping.mapping_id}><code>{mapping.mapping_id}</code><b>{mapping.page_name} · {mapping.operation}</b><p>{mapping.element_name ?? "未映射"} · {mapping.mapping_basis}</p></article>)}</section></div></details>
    <footer><IconShieldCheck aria-hidden="true" /><span>固定 uiux-021 离线优先级适配器。它不是用户研究、线上遥测、通用产品分析、设计效果验证、自动改 UI、A/B 实验或生产发布。</span></footer>
  </section>;
}

function narrativeConflictLabel(kind: NarrativeConflict["kind"]) {
  const labels: Record<NarrativeConflict["kind"], string> = {
    incomplete_coverage: "覆盖范围不完整",
    outcome_count_mismatch: "数量与服务端复算不一致",
    priority_mismatch: "优先级与规则台账不一致",
    unsupported_solution_claim: "把未批准方案写成当前结论",
    redundant_completed_work: "重复要求已经完成的计算",
    outcome_revision_mismatch: "引用了过期成果版本",
  };
  return labels[kind];
}

function NarrativeReconciliationPanel({ reconciliation }: { reconciliation: NarrativeReconciliation }) {
  const isRejected = reconciliation.model_disposition === "rejected";
  const isSupplemental = reconciliation.model_disposition === "supplemental";
  const modelOnly = reconciliation.authority === "model_only";
  const title = isRejected
    ? "成果已完成，模型说明未采用"
    : isSupplemental
      ? "当前结论来自服务端复算，模型说明仅作补充"
      : modelOnly
        ? "当前结论仅来自模型，仍需人工复核"
        : "模型说明已与服务端事实对账";
  const detail = isRejected
    ? "模型已返回，但与当前结构化成果存在冲突。页面只展示服务端全量复算的当前结论，错误发现和后续建议不会进入成果。"
    : isSupplemental
      ? "模型没有提供足够的可比事实，因而不能覆盖确定性成果；它只作为执行轨迹中的补充说明。"
      : modelOnly
        ? "本任务没有可比的服务端确定性成果。模型说明不是已验证事实，仍需结合来源和人工判断。"
        : "模型说明中的可比数字和优先级已与当前服务端复算结果对齐；服务端成果仍是事实权威。";
  return <section className={`narrative-reconciliation is-${reconciliation.model_disposition}`} aria-label="模型说明与服务端事实对账">
    <header>
      {isRejected || isSupplemental || modelOnly ? <IconAlertTriangle aria-hidden="true" /> : <IconShieldCheck aria-hidden="true" />}
      <div><span>说明采用回执</span><h3>{title}</h3><p>{detail}</p></div>
      <b>{isRejected ? "未采用" : isSupplemental ? "仅补充" : "已采用"}</b>
    </header>
    {reconciliation.conflicts.length > 0 && <details>
      <summary><IconRoute aria-hidden="true" />查看未采用原因（{reconciliation.conflicts.length} 项）<IconChevronDown aria-hidden="true" /></summary>
      <ol>{reconciliation.conflicts.map((conflict) => <li key={conflict.conflict_id} className={`is-${conflict.severity}`}>
        <div><b>{narrativeConflictLabel(conflict.kind)}</b><p>{conflict.narrative_excerpt}</p></div>
        <dl><div><dt>服务端事实</dt><dd>{conflict.expected}</dd></div><div><dt>模型说法</dt><dd>{conflict.observed}</dd></div></dl>
      </li>)}</ol>
    </details>}
    <footer><IconShieldCheck aria-hidden="true" /><span>这份回执只核对模型叙事与当前结构化事实是否一致，不证明方案有效或体验已经改善。</span></footer>
  </section>;
}

function WorkspaceArtifactSection({ artifacts, receipts }: { artifacts: WorkspaceArtifact[]; receipts: EffectReceipt[] }) {
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const checkSummary = summarizeArtifactChecks(artifacts);
  const checklistUsage = new Map<string, number>();
  for (const artifact of artifacts) {
    const key = artifactChecklistKey(artifact);
    checklistUsage.set(key, (checklistUsage.get(key) ?? 0) + 1);
  }
  const latestReceipt = receipts.at(-1) ?? null;
  const boundary = latestReceipt && latestReceipt.status !== "passed" ? latestReceipt : null;
  const executionArtifact = artifacts.find((artifact) => artifact.execution_summary) ?? null;
  const businessGateOutcome = artifacts.find((artifact) => artifact.business_gate_outcome)?.business_gate_outcome
    ?? latestReceipt?.business_gate_outcome
    ?? null;
  const legalReviewOutcome = artifacts.find((artifact) => artifact.legal_review_outcome)?.legal_review_outcome
    ?? latestReceipt?.legal_review_outcome
    ?? null;
  const candidateReviewOutcome = artifacts.find((artifact) => artifact.candidate_review_outcome)?.candidate_review_outcome
    ?? latestReceipt?.candidate_review_outcome
    ?? null;
  const financeReviewOutcome = artifacts.find((artifact) => artifact.finance_review_outcome)?.finance_review_outcome
    ?? latestReceipt?.finance_review_outcome
    ?? null;
  const outboundFlowOutcome = artifacts.find((artifact) => artifact.outbound_flow_outcome)?.outbound_flow_outcome
    ?? latestReceipt?.outbound_flow_outcome
    ?? null;
  const customerSegmentationOutcome = artifacts.find((artifact) => artifact.customer_segmentation_outcome)?.customer_segmentation_outcome
    ?? latestReceipt?.customer_segmentation_outcome
    ?? null;
  const sreDiagnosisOutcome = artifacts.find((artifact) => artifact.sre_diagnosis_outcome)?.sre_diagnosis_outcome
    ?? latestReceipt?.sre_diagnosis_outcome
    ?? null;
  const uxPrioritizationOutcome = artifacts.find((artifact) => artifact.ux_prioritization_outcome)?.ux_prioritization_outcome
    ?? latestReceipt?.ux_prioritization_outcome
    ?? null;
  const businessBlocked = Boolean(businessGateOutcome && businessGateOutcome.status !== "passed");
  const deterministicPassed = artifacts.length > 0 && artifacts.every((artifact) => artifact.verifier_status === "passed");
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
  return <section className={`workspace-artifacts${boundary ? " is-bounded" : ""}${businessBlocked || outboundFlowOutcome?.status === "invalid" ? " has-business-block" : ""}`} aria-labelledby="workspace-artifacts-title">
    <header>
      <IconFileDescription aria-hidden="true" />
      <div><span>运行工作区</span><h3 id="workspace-artifacts-title">{artifacts.length > 0 ? `Agent 已生成 ${artifacts.length} 份真实成果文件` : "这项任务尚不能生成可信成果"}</h3><p>{artifacts.length > 0 ? "文件已写入本次 Run 的隔离目录，原始 FORTE 文件没有被修改。" : boundary?.result}</p></div>
      <b>{businessGateOutcome?.status === "failed" ? `业务 Gate ${businessGateOutcome.failed_gate_count}/${businessGateOutcome.total_gate_count} 未通过` : businessGateOutcome?.status === "invalid" ? "来源校验失败" : candidateReviewOutcome ? "最终 HR 决定待人工处理" : financeReviewOutcome ? "最终财务处置待人工处理" : outboundFlowOutcome?.status === "invalid" ? "规则或图结构未通过" : outboundFlowOutcome ? "最终合规审批待人工处理" : customerSegmentationOutcome ? "策略草案待销售负责人复核" : sreDiagnosisOutcome ? `${sreDiagnosisOutcome.conflict_count} 组来源冲突待 SRE 核实` : uxPrioritizationOutcome ? `${uxPrioritizationOutcome.group_count} 组排序待 UX 负责人复核` : artifacts.length > 0 ? checkSummary.sameChecklist ? `${artifacts.length} 份成果共享 ${checkSummary.total} 项确定性检查，${checkSummary.passed}/${checkSummary.total} 通过` : checkSummary.shared ? `${artifacts.length} 份成果共 ${checkSummary.total} 项唯一确定性检查，${checkSummary.passed}/${checkSummary.total} 通过` : `${checkSummary.passed}/${checkSummary.total} 项检查通过` : "未伪造结果"}</b>
    </header>
    {uxPrioritizationOutcome && <UXPrioritizationOutcomePanel outcome={uxPrioritizationOutcome} deterministicPassed={deterministicPassed} />}
    {sreDiagnosisOutcome && <SREDiagnosisOutcomePanel outcome={sreDiagnosisOutcome} deterministicPassed={deterministicPassed} />}
    {customerSegmentationOutcome && <CustomerSegmentationOutcomePanel outcome={customerSegmentationOutcome} deterministicPassed={deterministicPassed} />}
    {outboundFlowOutcome && <OutboundFlowOutcomePanel outcome={outboundFlowOutcome} deterministicPassed={deterministicPassed} />}
    {financeReviewOutcome && <FinanceReviewOutcomePanel outcome={financeReviewOutcome} deterministicPassed={deterministicPassed} />}
    {candidateReviewOutcome && <CandidateReviewOutcomePanel outcome={candidateReviewOutcome} deterministicPassed={deterministicPassed} />}
    {legalReviewOutcome && <LegalReviewOutcomePanel outcome={legalReviewOutcome} deterministicPassed={deterministicPassed} />}
    {businessGateOutcome && <BusinessGateOutcomePanel outcome={businessGateOutcome} />}
    {executionArtifact && <article className={`workspace-action-result${executionArtifact.verifier_status === "failed" ? " is-failed" : ""}`} aria-label="实际执行边界"><IconShieldCheck aria-hidden="true" /><div><span>这次实际发生了什么</span><h4>{executionArtifact.execution_summary}</h4><p>{executionArtifact.purpose}</p>{latestReceipt && <ul>{latestReceipt.prohibited_side_effects.map((item) => <li key={item}>{item}</li>)}</ul>}</div></article>}
    {artifacts.length > 0 && <ol>{artifacts.map((artifact) => <li key={artifact.artifact_id} className={artifact.verifier_status === "passed" ? "is-passed" : "is-failed"}>
      <div className="workspace-artifact-file"><span><IconFile aria-hidden="true" /></span><div><h4>{artifact.title}</h4><p>{artifact.summary}</p><small>文件：{artifact.file_name} · 第 {artifact.round_number} 轮 · {formatSize(artifact.size)} · {artifact.source_file_refs.length} 份内容来源</small></div></div>
      <div className="workspace-artifact-status"><b>{artifact.verifier_status === "passed" ? <><IconCheck aria-hidden="true" />确定性检查通过</> : <><IconAlertTriangle aria-hidden="true" />检查未通过</>}</b><span>{artifact.record_count !== null ? `${artifact.record_count} 条记录 · ` : ""}{artifact.checks.filter((check) => check.passed).length}/{artifact.checks.length} 项检查{(checklistUsage.get(artifactChecklistKey(artifact)) ?? 0) > 1 ? " · 使用同一验证清单" : ""}</span>{artifact.business_gate_outcome && <small>只代表公式、来源和文件结构已复核，不代表业务 Gate 通过。</small>}{artifact.candidate_review_outcome && <small>只代表来源、条件计算和成果结构已复核，不代表录用或淘汰。</small>}{artifact.finance_review_outcome && <small>只代表来源、金额、候选枚举和成果结构已复核，不代表已经付款、核销、记账或确认坏账。</small>}{artifact.outbound_flow_outcome && <small>只代表来源规则、DOCX 和图结构已复核，不代表合规审批或外呼动作发生。</small>}{artifact.customer_segmentation_outcome && <small>只代表来源、清洗、画像裁决与成果结构已复核，不代表策略获批、销售有效或客户动作发生。</small>}{artifact.sre_diagnosis_outcome && <small>只代表日志、观察台账和成果结构已复核，不代表根因已确定、提案获批或任何命令已经执行。</small>}{artifact.ux_prioritization_outcome && <small>只代表完整日志、规则、排序和两份 CSV 结构已复核，不代表方案获批、体验改善或生产 UI 已修改。</small>}</div>
      <button type="button" onClick={() => void downloadArtifact(artifact)} disabled={downloading !== null}><IconDownload aria-hidden="true" />{downloading === artifact.artifact_id ? "正在下载" : "下载成果"}</button>
      {(artifact.deliverable_type || artifact.covered_period || artifact.statistic_basis || artifact.purpose) && <dl className={`workspace-artifact-semantics${artifact.deliverable_type ? " has-deliverable-type" : ""}`}>
        {artifact.deliverable_type && <div><dt>成果类型</dt><dd>{artifact.deliverable_type}</dd></div>}
        {artifact.covered_period && <div><dt>{artifact.finance_review_outcome ? "涵盖期间" : artifact.deliverable_type ? "适用范围" : "涵盖期间"}</dt><dd>{artifact.covered_period}</dd></div>}
        {artifact.statistic_basis && <div><dt>{artifact.finance_review_outcome ? "统计口径" : artifact.deliverable_type ? "采用依据" : "统计口径"}</dt><dd>{artifact.statistic_basis}</dd></div>}
        {artifact.purpose && <div><dt>{artifact.finance_review_outcome ? "用途" : artifact.deliverable_type ? "使用边界" : "用途"}</dt><dd>{artifact.purpose}</dd></div>}
      </dl>}
      {artifact.key_outputs.length > 0 && <section className="workspace-artifact-key-outputs" aria-label={artifact.key_outputs_label ?? "关键输出"}><span>{artifact.key_outputs_label ?? `${artifact.key_outputs.length} 项关键输出`}</span><ul>{artifact.key_outputs.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      {artifact.self_test && <section className="workspace-artifact-self-test" aria-label={`${artifact.scenario_id} 自测卡`}>
        <header><IconRoute aria-hidden="true" /><div><span>下载后可以自己验证</span><h5>{artifact.scenario_id} 自测卡</h5></div></header>
        <dl>
          <div><dt>输入</dt><dd>{artifact.self_test.instruction}</dd></div>
          <div><dt>预期文件</dt><dd>{artifact.self_test.expected_files.join("、")}</dd></div>
        </dl>
        <div className="workspace-artifact-self-test-commands"><b>依次运行</b>{artifact.self_test.commands.map((command) => <code key={command}>{command}</code>)}</div>
        {artifact.self_test.test_suites.length > 0 && <section className="workspace-artifact-test-suites" aria-label="真实测试清单">
          <header><div><span>真实测试清单</span><h6>{artifact.self_test.test_suites.reduce((total, suite) => total + suite.test_count, 0)} 项</h6></div><p>{artifact.self_test.test_manifest_matches_collected ? `页面测试 ID、${artifact.self_test.test_manifest_file ?? "test-manifest.json"} 与实际 collected IDs 是同一集合。` : "测试清单仍需核对。"}</p></header>
          <div>{artifact.self_test.test_suites.map((suite) => <details key={suite.suite_id}>
            <summary><span><b>{suite.label}</b><small>{suite.test_files.join(" · ")}</small></span><strong>{suite.test_count} 项</strong></summary>
            <ol aria-label={`${suite.label} 测试 ID`}>{suite.test_ids.map((testId) => <li key={testId}><code>{testId}</code></li>)}</ol>
          </details>)}</div>
        </section>}
        <details><summary><IconEye aria-hidden="true" />查看应通过的测试与失败信号</summary><div className="workspace-artifact-self-test-detail"><section><b>应通过</b><ul>{artifact.self_test.expected_checks.map((item) => <li key={item}>{item}</li>)}</ul></section><section><b>不要合并</b><ul>{artifact.self_test.failure_signals.map((item) => <li key={item}>{item}</li>)}</ul></section></div></details>
      </section>}
      {artifact.review_guidance && <aside className={`workspace-artifact-review${artifact.verifier_status === "failed" ? " is-failed" : ""}`}><IconAlertTriangle aria-hidden="true" /><div><b>{artifact.verifier_status === "failed" ? "下一步怎么处理" : "为什么仍需人工复核"}</b><p>{artifact.review_guidance}</p></div></aside>}
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
  workspaceArtifacts,
  receipts,
  reconciliation,
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
  workspaceArtifacts: WorkspaceArtifact[];
  receipts: EffectReceipt[];
  reconciliation: NarrativeReconciliation | null;
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
  const hasWorkspaceEvidence = workspaceArtifacts.length > 0 || receipts.length > 0;
  const hasPassedDeterministicEvidence = workspaceArtifacts.some((artifact) => artifact.verifier_status === "passed")
    || receipts.some((receipt) => receipt.status === "passed");
  const hasDeterministicAuthority = reconciliation?.authority === "deterministic_outcome"
    && hasPassedDeterministicEvidence;
  if (!result && !hasWorkspaceEvidence) return <div className="workspace-placeholder"><IconClock aria-hidden="true" /><h2>任务简报尚未形成</h2><p>Agent Control Loop 完成只读分析并通过文件引用校验后，简报会出现在这里。</p></div>;
  const visibleFindings = result ? (expanded ? result.findings : result.findings.slice(0, 3)) : [];
  const latestRoundNumber = artifacts.at(-1)?.round_number ?? null;
  return <div className="result-view-stack">
    {hasWorkspaceEvidence && <WorkspaceArtifactSection artifacts={workspaceArtifacts} receipts={receipts} />}
    {reconciliation && <NarrativeReconciliationPanel reconciliation={reconciliation} />}
    {result ? <article className="result-view">
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
  </article> : hasDeterministicAuthority ? <article className="result-authority-placeholder" aria-label="当前结论来源">
    <IconShieldCheck aria-hidden="true" />
    <div><span>当前结论</span><h2>以服务端确定性成果为准</h2><p>本轮模型说明没有进入发现、建议或成果版本；请直接查看上方经过来源重算和文件校验的结果。</p></div>
  </article> : <article className="result-authority-placeholder is-failed" aria-label="当前没有可采用结论">
    <IconAlertTriangle aria-hidden="true" />
    <div><span>当前结论</span><h2>尚未形成可采用的确定性成果</h2><p>当前只保留了失败或受限回执。请先查看上方失败原因和恢复动作，不要把它当作服务端确认的业务结论。</p></div>
  </article>}
  </div>;
}
