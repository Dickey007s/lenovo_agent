import { expect, test } from "@playwright/test";
import { projectTaskResponsibility } from "../app/task-responsibility";
import type { HarnessRun } from "../app/harness-workbench";

// Projection fixtures only: these do not establish server admission or model quality.
function facts() {
  return {
    result: { findings: [{ finding_id: "f1", title: "账面余额", fact_summary: "170万元", detail: "", affected_branch_ids: ["b1"], evidence_anchors: [{ role: "observed" }], review: null }] },
    artifact_versions: [], decision_requests: [], decision_records: [], workspace_artifacts: [], worker_runs: [],
    execution_policy: "manual", status: "completed", branches: [{ branch_id: "b1", title: "核对余额", status: "completed" }], rounds: [],
  } as unknown as HarnessRun;
}

test("responsibility: completed and anchored analysis is not a confidence score", () => {
  const result = projectTaskResponsibility(facts());
  expect(result.system.map(item => item.title)).toEqual(["账面余额"]);
  expect(result.human).toEqual([]);
  expect(result.agent).toEqual([]);
  expect(result.system[0]).not.toHaveProperty("confidence");
});

test("responsibility: pending branch and background-only quote never count as completed", () => {
  const run = facts();
  run.branches[0].status = "waiting_input";
  expect(projectTaskResponsibility(run).system).toEqual([]);
  expect(projectTaskResponsibility(run).agent).toHaveLength(1);
  run.branches[0].status = "completed";
  run.result!.findings[0].evidence_anchors[0].role = "context";
  expect(projectTaskResponsibility(run).system).toEqual([]);
  expect(projectTaskResponsibility(run).agent[0].reason).toContain("只有背景引用");
});

test("responsibility: judgment remains human even when analysis branch completed", () => {
  const run = facts();
  run.result!.findings[0].review = { requires_human_decision: true, question: "是否提出变更申请？", why_human: "需要负责人决定", options: [] } as never;
  expect(projectTaskResponsibility(run).system).toEqual([]);
  expect(projectTaskResponsibility(run).human[0].reason).toBe("需要负责人决定");
  run.decision_requests = [{ finding_id: "f1", resolution_id: null, state: "accepted" }] as never;
  expect(projectTaskResponsibility(run).human).toEqual([]);
  expect(projectTaskResponsibility(run).system).toEqual([]);
  run.result!.findings[0].finding_id = null;
  run.decision_requests = [];
  run.decision_records = [{ finding_id: null, action: "accept" }] as never;
  expect(projectTaskResponsibility(run).human).toHaveLength(1);
});

test("responsibility: missing sources, Agent repair and usage authorization stay separate", () => {
  const run = facts();
  run.status = "waiting_input";
  run.branches[0].status = "waiting_input";
  run.rounds = [{ uncovered_requirements: [{ title: "银行回单", reason: "索引未找到", objective: "" }], next_step: { recovery_kind: "source_location", candidate_branch_ids: ["b1"], ready_branch_ids: [] } }] as never;
  expect(projectTaskResponsibility(run).human[0].kind).toBe("missing");
  expect(projectTaskResponsibility(run).agent[0].kind).toBe("repair");
  run.rounds[0].next_step!.ready_branch_ids = ["b1"];
  expect(projectTaskResponsibility(run).agent[0].kind).toBe("authorization");
  run.execution_policy = "automatic_readonly";
  expect(projectTaskResponsibility(run).agent[0].kind).not.toBe("authorization");
});

test("responsibility: source choice is not business approval and unknown decision stays blocked", () => {
  const run = facts();
  run.decision_requests = [{ request_id: "r1", finding_id: "f1", resolution_id: "res1", branch_id: "b1", state: null }] as never;
  expect(projectTaskResponsibility(run).system).toEqual([]);
  expect(projectTaskResponsibility(run).human[0].kind).toBe("source_choice");
});

test("responsibility: business veto and unanchored output never appear as autonomous success", () => {
  const run = facts();
  run.workspace_artifacts = [{ business_gate_outcome: { status: "failed" } }] as never;
  expect(projectTaskResponsibility(run).businessBlocked).toBe(true);
  expect(projectTaskResponsibility(run).system).toEqual([]);
  run.workspace_artifacts = [];
  run.result!.findings[0].evidence_anchors = [];
  expect(projectTaskResponsibility(run).system).toEqual([]);
});
