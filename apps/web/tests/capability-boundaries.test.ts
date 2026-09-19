import { describe, expect, it } from "vitest";
import { projectCopilotBoundaries, type CopilotBoundaryFacts } from "../app/capability-boundaries";

const base: CopilotBoundaryFacts = { readOnly: false, terminal: false, status: "running", controlState: "running", candidateCount: 0, hasDecision: false, unavailableDecisions: 0, readyWorkers: 0, waitingBranch: false, businessDecision: null, businessInvalid: false };
const notices = (patch: Partial<CopilotBoundaryFacts>) => projectCopilotBoundaries({ ...base, ...patch });

describe("server-fact copilot explanation, not a permission engine", () => {
  it("does not create an approval for ordinary bounded work", () => {
    expect(notices({}).map((item) => item.key)).toEqual(["bounded"]);
  });
  it("keeps historical pending facts read-only", () => {
    expect(notices({ readOnly: true, hasDecision: true, candidateCount: 2, readyWorkers: 3 }).map((item) => item.key)).toEqual(["history"]);
  });
  it("explains evidence choice without business approval", () => {
    const [notice] = notices({ hasDecision: true, candidateCount: 3 });
    expect(notice.key).toBe("evidence");
    expect(notice.agent).toContain("3 个候选");
    expect(notice.limit).toContain("不是批准业务结论");
  });
  it("does not invent source positions for a judgment decision", () => {
    expect(notices({ hasDecision: true })[0].key).toBe("judgment");
  });
  it("keeps terminal choice recording separate from continuation", () => {
    expect(notices({ terminal: true, hasDecision: true, candidateCount: 2 })[0].limit).toContain("同一任务的新 Run");
  });
  it("does not replace incomplete decision data with a generic retry", () => {
    expect(notices({ unavailableDecisions: 1, waitingBranch: true }).map((item) => item.key)).toEqual(["incomplete"]);
  });
  it("scopes worker consent to the ready wave and never expands permission", () => {
    const [notice] = notices({ readyWorkers: 2, waitingBranch: true });
    expect(notice.key).toBe("workers");
    expect(notice.agent).toContain("2 个工作包");
    expect(notice.limit).toContain("不扩大文件范围");
    expect(notices({ readyWorkers: 2, terminal: true }).some((item) => item.key === "workers")).toBe(false);
  });
  it("keeps a no-ready-wave branch in branch recovery", () => {
    expect(notices({ waitingBranch: true })[0].key).toBe("retry");
    expect(notices({ waitingBranch: true, terminal: true })[0].limit).toContain("不覆盖旧结果");
  });
  it("keeps business failure and evidence choice visible together", () => {
    const items = notices({ businessDecision: "业务条件尚未满足", hasDecision: true, candidateCount: 2 });
    expect(items.map((item) => item.key)).toEqual(["business", "evidence"]);
    expect(items[0].agent).toBe("业务条件尚未满足");
    expect(items[0].limit).toContain("不执行上线");
  });
  it("does not present invalid business judgment as a proven failure", () => {
    expect(notices({ businessDecision: "", businessInvalid: true })[0].title).toBe("业务判断尚不成立");
  });
  it("does not turn a failed execution with no decision into success", () => {
    expect(notices({ status: "failed", terminal: true })[0].key).toBe("failed");
  });
  it("does not claim a pause request already cancelled the in-flight call", () => {
    expect(notices({ controlState: "pause_requested" })[0].limit).toContain("不等于批准");
    expect(notices({ controlState: "pause_requested" })[0].agent).toContain("不宣称在途调用已被取消");
    expect(notices({ controlState: "paused" })[0].title).toBe("执行已暂停");
  });
  it("does not mutate the facts or add authority fields", () => {
    const input = Object.freeze({ ...base, hasDecision: true, candidateCount: 2 });
    const before = JSON.stringify(input);
    projectCopilotBoundaries(input);
    expect(JSON.stringify(input)).toBe(before);
  });
});
