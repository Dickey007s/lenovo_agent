import type { HarnessRun } from "./harness-workbench";
import { projectTaskResponsibility } from "./task-responsibility";

// Admission is a plan; only model and contribution receipts establish execution.
export function todoSummary(run: HarnessRun) {
  const division = projectTaskResponsibility(run);
  const mode = run.topology_admission?.mode;
  const returned = run.worker_runs.filter(worker => worker.model_called).length;
  const adopted = run.worker_runs.filter(worker => worker.model_called && worker.output_used).length;
  const active = run.work_units.filter(unit => ["reserved", "running"].includes(unit.state)).length;
  const promotion = run.adaptive_reviews?.find(review => review.origin === "single_agent" && review.status === "expanded" && review.added_branch_ids.length > 0);
  const routing = promotion ? `单 Agent 起步 · 已追加 ${promotion.added_branch_ids.length} 项核对`
    : mode === "adaptive_readonly_workers"
    ? returned ? `多 Agent · ${returned} 份调用回执，${adopted} 份已采用`
      : active ? `多 Agent · ${active} 个工作包执行中` : "计划多 Agent · 尚未收到调用回执"
    : mode === "single_controller" ? "单 Agent · 不额外拆分"
    : mode === "fixed_workflow" ? "单控制器 · 顺序处理" : "正在评估执行方式";
  const concerns = [
    ...(division.businessBlocked ? ["业务条件未通过"] : []),
    ...division.human.map(item => item.title),
    ...division.agent.filter(item => !["queued", "planning", "analyzing", "running"].includes(run.status)).map(item => item.title),
  ];
  const complete = run.status === "completed" && concerns.length === 0 && division.system.length > 0;
  const status = run.status === "failed" ? "执行失败" : run.status === "stopped" ? "已停止"
    : concerns.length ? "仍有未完成项" : complete ? "分析已完成"
    : run.status === "completed" ? "暂无可交付分析" : run.status === "waiting_input" ? "执行受阻" : run.control_state === "paused" ? "已暂停" : "执行中";
  const shownBranches = new Set<string>();
  const preview = division.system.filter(item => {
    const branches = item.finding?.affected_branch_ids ?? [];
    if (branches.every(id => shownBranches.has(id))) return false;
    branches.forEach(id => shownBranches.add(id));
    return true;
  }).slice(0, 3);
  return { routing, returned, adopted, active, complete, status, concerns, findings: division.system, preview };
}
