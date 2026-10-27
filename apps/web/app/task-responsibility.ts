import type { HarnessRun } from "./harness-workbench";

type Finding = NonNullable<HarnessRun["result"]>["findings"][number];
export type ResponsibilityItem = {
  id: string;
  title: string;
  reason: string;
  kind: "analysis" | "judgment" | "source_choice" | "missing" | "repair" | "authorization" | "pending";
  finding?: Finding;
};

// Project existing receipts, not model confidence or new execution permissions.
export function projectTaskResponsibility(run: HarnessRun) {
  const latest = run.rounds.at(-1);
  const findings = run.result?.findings ?? run.artifact_versions.at(-1)?.findings ?? [];
  const system: ResponsibilityItem[] = [];
  const human: ResponsibilityItem[] = [];
  const agent: ResponsibilityItem[] = [];
  const open = run.decision_requests.filter(item => item.state === "pending" || item.state === "deferred" || item.state === null);
  const businessBlocked = run.workspace_artifacts.some(item => item.business_gate_outcome && item.business_gate_outcome.status !== "passed");
  const decisionFindingIds = new Set(open.map(item => item.finding_id));
  for (const [index, finding] of findings.entries()) {
    const id = finding.finding_id ?? `finding-${index}`;
    if (finding.review?.requires_human_decision) {
      const request = finding.finding_id ? [...run.decision_requests].reverse().find(item => item.finding_id === finding.finding_id && !item.resolution_id) : undefined;
      const record = finding.finding_id ? [...run.decision_records].reverse().find(item => item.finding_id === finding.finding_id) : undefined;
      const pending = request ? ["pending", "deferred"].includes(request.state ?? "") : !record || record.action === "defer";
      if (pending) human.push({ id, kind: "judgment", title: finding.review.question || finding.title, reason: finding.review.why_human, finding });
      continue;
    }
    const completed = finding.affected_branch_ids.length > 0 && finding.affected_branch_ids.every(id => run.branches.some(branch => branch.branch_id === id && branch.status === "completed"));
    const hasBusinessSource = finding.evidence_anchors.some(anchor => anchor.role !== "context");
    if (!decisionFindingIds.has(id) && completed && hasBusinessSource && !businessBlocked) {
      system.push({ id, kind: "analysis", title: finding.title, reason: finding.detail || finding.fact_summary || finding.title, finding });
    } else if ((!completed || !hasBusinessSource) && !decisionFindingIds.has(id) && !businessBlocked && !finding.affected_branch_ids.some(id => run.branches.some(branch => branch.branch_id === id && branch.status !== "completed"))) {
      agent.push({ id, kind: "pending", title: finding.title, reason: finding.evidence_anchors.length && !hasBusinessSource ? "当前只有背景引用，尚无直接支持结论的依据，不列为已交付分析。" : "当前分析缺少完成的工作项或直接依据，不列为系统已完成。", finding });
    }
  }
  for (const request of open) {
    if (human.some(item => item.finding?.finding_id === request.finding_id)) continue;
    const resolution = [...run.rounds].reverse().flatMap(round => round.next_step?.evidence_resolutions ?? [])
      .find(item => item.resolution_id === request.resolution_id);
    human.push({ id: request.request_id, kind: request.resolution_id ? "source_choice" : "judgment",
      title: resolution?.finding_title ?? "待决资料尚未完整展示",
      reason: resolution?.candidates.length ? `同一引用有 ${resolution.candidates.length} 个候选位置，需要对照原文；这不是业务批准。` : "已有待决记录，但可选择的依据尚未完整展示；不能用重试代替人的决定。" });
  }
  const missing = new Map(run.rounds.flatMap(round => round.uncovered_requirements ?? []).map(item => [item.title, item]));
  for (const item of missing.values()) human.push({ id: `missing-${item.title}`, kind: "missing", title: item.title, reason: `${item.reason} 当前不能据此下结论，也没有自动补齐材料。` });
  const ready = new Set(latest?.next_step?.ready_branch_ids ?? []);
  for (const branch of run.branches.filter(item => item.status !== "completed")) {
    if (open.some(item => item.branch_id === branch.branch_id) || human.some(item => item.finding?.affected_branch_ids.includes(branch.branch_id))) continue;
    const worker = [...run.worker_runs].reverse().find(item => item.branch_id === branch.branch_id);
    const technical = ["source_location", "analysis_output"].includes(latest?.next_step?.recovery_kind ?? "") && latest?.next_step?.candidate_branch_ids.includes(branch.branch_id);
    const authorization = run.status === "waiting_input" && ready.has(branch.branch_id) && run.execution_policy !== "automatic_readonly";
    const disputed = worker?.dependency_assessments.some(item => item.verdict !== "supported");
    const partial = findings.find(item => item.affected_branch_ids.includes(branch.branch_id));
    agent.push({ id: branch.branch_id, title: branch.title,
      kind: authorization ? "authorization" : technical ? "repair" : "pending",
      reason: authorization ? "等待协作用量授权，不是结论可信度低。尚未派发本批 Agent。"
        : technical ? "Agent 尚未完成原文定位或结构校验；不需要你猜答案或改原文件。已有内容保留，重试仍需按现有控制执行。"
        : disputed ? "下游核对未通过，当前不能把分歧当作已解决；先查看回执。"
        : branch.status === "running" ? "正在处理批准范围内的资料，尚无完成回执。"
        : partial ? `当前分析提示：${partial.fact_summary || partial.title} 该工作项尚未通过，不能当作已完成；原文位置不证明此判断正确。`
        : "此项尚未完成。仅凭暂停状态不能认定需要业务判断，请查看具体原因。" });
  }
  return { system, human, agent, businessBlocked };
}
