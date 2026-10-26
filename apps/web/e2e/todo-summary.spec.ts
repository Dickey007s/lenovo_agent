import { expect, test } from "@playwright/test";
import { todoSummary } from "../app/todo-summary";
import type { HarnessRun } from "../app/harness-workbench";

function facts() {
  return {
    status: "completed", control_state: "running", execution_policy: "automatic_readonly",
    result: { findings: [
      { finding_id: "f1", title: "软件规则", affected_branch_ids: ["b1"], evidence_anchors: [{ role: "observed" }] },
      { finding_id: "f2", title: "软件例外", affected_branch_ids: ["b1"], evidence_anchors: [{ role: "observed" }] },
      { finding_id: "f3", title: "招聘要求", affected_branch_ids: ["b2"], evidence_anchors: [{ role: "observed" }] },
    ] },
    branches: [{ branch_id: "b1", title: "软件规则", status: "completed" }, { branch_id: "b2", title: "招聘要求", status: "completed" }],
    decision_requests: [], decision_records: [], rounds: [], workspace_artifacts: [], artifact_versions: [],
    worker_runs: [], work_units: [], topology_admission: { mode: "adaptive_readonly_workers" },
  } as unknown as HarnessRun;
}

test("todo summary: admission does not claim executed workers", () => {
  const run = facts();
  expect(todoSummary(run).routing).toBe("计划多 Agent · 尚未收到调用回执");
  run.work_units = [{ state: "running" }, { state: "reserved" }] as never;
  expect(todoSummary(run).routing).toBe("多 Agent · 2 个工作包执行中");
  run.worker_runs = [{ model_called: true, output_used: true }, { model_called: true, output_used: false }] as never;
  expect(todoSummary(run).routing).toBe("多 Agent · 2 份调用回执，1 份已采用");
});

test("todo summary: promotion describes admitted work, not fictitious parallel execution", () => {
  const run = facts();
  run.adaptive_reviews = [{ origin: "single_agent", status: "expanded", added_branch_ids: ["new-check"] }] as HarnessRun["adaptive_reviews"];
  expect(todoSummary(run).routing).toBe("单 Agent 起步 · 已追加 1 项核对");
  expect(todoSummary(run).returned).toBe(0);
  run.adaptive_reviews![0].status = "discarded";
  expect(todoSummary(run).routing).toBe("计划多 Agent · 尚未收到调用回执");
});

test("todo summary: previews cover different work rather than repeating first worker", () => {
  const result = todoSummary(facts());
  expect(result.findings).toHaveLength(3);
  expect(result.preview.map(item => item.title)).toEqual(["软件规则", "招聘要求"]);
});

test("todo summary: partial failure preserves accepted work and exposes unfinished work", () => {
  const run = facts();
  run.status = "waiting_input";
  run.branches[1].status = "waiting_input";
  const result = todoSummary(run);
  expect(result.complete).toBe(false);
  expect(result.findings.map(item => item.title)).toEqual(["软件规则", "软件例外"]);
  expect(result.concerns).toEqual(["招聘要求"]);
});

test("todo summary: loop completed never hides missing sources or pending judgment", () => {
  const run = facts();
  run.rounds = [{ uncovered_requirements: [{ title: "缺银行回单", reason: "未找到" }] }] as never;
  expect(todoSummary(run).status).toBe("仍有未完成项");
  expect(todoSummary(run).complete).toBe(false);
  run.rounds = [];
  run.result!.findings[0].review = { requires_human_decision: true, question: "待决定", why_human: "需要授权" } as never;
  expect(todoSummary(run).concerns).toContain("待决定");
});

test("todo summary: same-family fixed workflow is not multiple agents", () => {
  const run = facts();
  run.topology_admission!.mode = "fixed_workflow";
  expect(todoSummary(run).routing).toBe("单控制器 · 顺序处理");
  expect(todoSummary(run).returned).toBe(0);
});

test("todo summary: completed without usable findings is not a green delivery", () => {
  const run = facts();
  run.result!.findings = [];
  expect(todoSummary(run).complete).toBe(false);
  expect(todoSummary(run).status).toBe("暂无可交付分析");
});

test("todo summary: background-only output stays visible as unfinished", () => {
  const run = facts();
  run.result!.findings[2].evidence_anchors[0].role = "context";
  const result = todoSummary(run);
  expect(result.findings).toHaveLength(2);
  expect(result.concerns).toContain("招聘要求");
  expect(result.complete).toBe(false);
  expect(result.status).toBe("仍有未完成项");
});
