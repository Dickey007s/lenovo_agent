"use client";

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconArrowLeft,
  IconArrowRight,
  IconArrowsExchange,
  IconBolt,
  IconCheck,
  IconCircleCheck,
  IconFileDescription,
  IconGitCompare,
  IconHandStop,
  IconHistory,
  IconLayoutDashboard,
  IconListCheck,
  IconPlayerPause,
  IconPlayerPlay,
  IconRefresh,
  IconRobot,
  IconSend2,
  IconShieldCheck,
  IconTargetArrow,
} from "@tabler/icons-react";

import { projectSourceReferences } from "./source-reference";
import type { ControlIntent, SyncState } from "./task-runtime-panel";
import type {
  ArtifactVersion,
  BranchSnapshot,
  ConflictRecord,
  ConflictResolutionOption,
  ImpactChange,
  ImpactReceipt,
  TaskPhase,
  TaskStageRecord,
  TaskSnapshot,
  VerificationReport,
} from "./task-types";

export type TaskDirectorViewMode = "cockpit" | "director" | "artifacts" | "manual";
export type TaskTransportState = "connecting" | "connected" | "interrupted";

type TaskWorkspaceHeaderProps = {
  task: TaskSnapshot | null;
  mode: TaskDirectorViewMode;
  syncState: SyncState;
  busy: boolean;
  creating: boolean;
  onModeChange: (mode: TaskDirectorViewMode) => void;
  onRefresh: () => void;
  onCreate: () => void;
};

type TaskDirectorCanvasProps = {
  task: TaskSnapshot | null;
  syncState: SyncState;
  transportState: TaskTransportState;
  busy: boolean;
  creating: boolean;
  onCreate: () => void;
  onStart: () => void;
  onRetry: () => void;
  onShowDecisions: () => void;
  onOpenArtifact: (artifactVersionId: string) => void;
};

type TaskDecisionPaneProps = {
  task: TaskSnapshot | null;
  syncState: SyncState;
  transportState: TaskTransportState;
  busy: boolean;
  pending: boolean;
  errorMessage: string;
  onRetry: () => void;
  onControl: (intent: ControlIntent) => Promise<boolean>;
  onOpenArtifact: (artifactVersionId: string) => void;
  onPrepareAction: (artifactVersionId: string) => void;
};

const TASK_STATUS_LABELS: Record<TaskSnapshot["status"], string> = {
  ready: "尚未开始",
  running: "正在准备",
  waiting_input: "等待你的决定",
  paused: "已暂停",
  taken_over: "由你接管",
  verifying: "正在核对",
  committed: "已完成",
  failed: "需要处理",
  cancelled: "已取消",
};

const BRANCH_STATUS_LABELS: Record<BranchSnapshot["status"], string> = {
  queued: "等待处理",
  running: "正在准备",
  waiting_evidence: "等待确认",
  paused: "已暂停",
  taken_over: "人工接管",
  verifying: "正在核对",
  failed: "需要处理",
  committed: "已准备",
  cancelled: "已取消",
};

const PHASES: { key: Exclude<TaskPhase, "contract">; label: string; summary: string }[] = [
  { key: "observe", label: "读取资料", summary: "读取本轮允许来源" },
  { key: "plan", label: "拆分任务", summary: "明确三份交付材料" },
  { key: "act", label: "生成材料", summary: "形成可核对的内容" },
  { key: "verify", label: "核对事实", summary: "发现差异时暂停" },
  { key: "commit", label: "准备完成", summary: "汇总已核对结果" },
];

const STAGE_LABELS: Record<TaskPhase, string> = {
  contract: "确认任务",
  observe: "读取资料",
  plan: "拆分任务",
  act: "生成材料",
  verify: "核对事实",
  commit: "准备完成",
};

const PHASE_ORDER: Record<TaskPhase, number> = {
  contract: -1,
  observe: 0,
  plan: 1,
  act: 2,
  verify: 3,
  commit: 4,
};

const OFFICIAL_REVENUE_SOURCE = "fixture:crm/customer-a:official-revenue-v3";

function formatTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "时间待确认"
    : date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function formatCompletionCriteria(criteria: string[]) {
  return criteria.map((criterion) => criterion.replace(/state hash/gi, "状态指纹")).join("；");
}

function isTerminal(task: TaskSnapshot | null) {
  return Boolean(task && ["committed", "failed", "cancelled"].includes(task.status));
}

function latestHead(task: TaskSnapshot, branch: BranchSnapshot) {
  const headIds = new Set(Object.values(branch.artifact_heads));
  return task.artifact_versions
    .filter((artifact) => headIds.has(artifact.artifact_version_id))
    .sort((a, b) => b.version - a.version)[0] ?? null;
}

function latestVerification(task: TaskSnapshot, artifact: ArtifactVersion | null) {
  if (!artifact) return null;
  return task.verification_reports
    .filter((report) => report.artifact_version_id === artifact.artifact_version_id)
    .sort((a, b) => b.checked_at.localeCompare(a.checked_at))[0] ?? null;
}

function verificationLabel(report: VerificationReport | null) {
  if (!report) return "尚无验证记录";
  if (report.status === "passed") return "验证通过";
  if (report.status === "conflict") return "发现证据冲突";
  if (report.status === "failed") return "验证失败";
  return "等待验证";
}

function verifiedBranchCount(task: TaskSnapshot) {
  return task.branches.filter((branch) => {
    const head = latestHead(task, branch);
    return latestVerification(task, head)?.status === "passed";
  }).length;
}

function deliverableTitle(task: TaskSnapshot, deliverableId: string) {
  return task.contract.deliverables.find((item) => item.deliverable_id === deliverableId)?.title
    ?? "本轮材料";
}

function latestImpactReceipt(task: TaskSnapshot) {
  const receipt = [...task.controls]
    .reverse()
    .find((control) => control.status === "applied" && control.impact_receipt)?.impact_receipt ?? null;
  if (!receipt) return null;
  const artifactIds = new Set(task.artifact_versions.map((artifact) => artifact.artifact_version_id));
  if (receipt.changed_artifact_version_ids.some((artifactId) => !artifactIds.has(artifactId))) return null;
  if (receipt.commit_created && (!task.last_commit || receipt.commit_id !== task.last_commit.commit_id)) return null;
  return receipt;
}

function impactVerificationLabel(receipt: ImpactReceipt) {
  if (receipt.verification_status === "passed") return "核对通过";
  if (receipt.verification_status === "partial") return "部分核对完成";
  if (receipt.verification_status === "failed") return "核对未通过";
  return "尚未核对";
}

function impactChangeLabel(change: ImpactChange, applied: boolean) {
  if (change.change_kind === "will_change") return applied ? "已改变" : "会改变";
  if (change.change_kind === "will_recheck") return applied ? "已重新核对" : "会重新核对";
  if (change.change_kind === "unchanged") return "保持不变";
  return applied ? "未发生" : "不会发生";
}

function ImpactChangeList({ changes, applied }: { changes: ImpactChange[]; applied: boolean }) {
  return (
    <ol className="task-impact-change-list">
      {changes.map((change, index) => (
        <li className={`is-${change.change_kind}`} key={`${change.label}-${index}`}>
          <span>{impactChangeLabel(change, applied)}</span>
          <strong>{change.label}</strong>
          <div>
            {change.before && !["unchanged", "no_external_action"].includes(change.change_kind) && <small>{change.before}</small>}
            {change.before && change.after && !["unchanged", "no_external_action"].includes(change.change_kind) && <IconArrowRight aria-hidden="true" />}
            {change.after && <b>{change.after}</b>}
          </div>
        </li>
      ))}
    </ol>
  );
}

function phaseState(task: TaskSnapshot, phase: Exclude<TaskPhase, "contract">) {
  const stageRecord = task.stage_records?.find((record) => record.phase === phase);
  if (task.stage_records?.length && stageRecord) {
    if (stageBlocked(task, phase)) return "current";
    if (stageRecord.status === "completed") return "complete";
    if (stageRecord.status === "running" || stageRecord.status === "failed") return "current";
    return "pending";
  }
  const current = PHASE_ORDER[task.phase];
  const target = PHASE_ORDER[phase];
  if (task.status === "committed" || target < current) return "complete";
  if (target === current) return "current";
  return "pending";
}

function stageBlocked(task: TaskSnapshot, phase: TaskPhase) {
  return task.status === "waiting_input" && phase === "verify"
    && task.conflicts.some((conflict) => conflict.status === "open");
}

function currentStageRecord(task: TaskSnapshot, phase = task.phase): TaskStageRecord | null {
  return task.stage_records?.find((record) => record.phase === phase) ?? null;
}

function progressiveTask(task: TaskSnapshot) {
  return Boolean(task.stage_records?.length);
}

function stageDetailItems(task: TaskSnapshot, phase: TaskPhase, detail: Record<string, unknown> | undefined) {
  if (!detail) return [];
  const deliverableTitles = new Map(
    task.contract.deliverables.map((item) => [item.deliverable_id, item.title]),
  );
  if (phase === "observe" && Array.isArray(detail.source_labels)) {
    return detail.source_labels
      .filter((value): value is string => typeof value === "string")
      .map((value) => ({ title: value, detail: "已纳入本轮允许读取范围" }));
  }
  if (phase === "plan") {
    const plan = detail.plan;
    if (plan && typeof plan === "object" && !Array.isArray(plan)) {
      const packages = (plan as Record<string, unknown>).work_packages;
      if (Array.isArray(packages)) {
        return packages.flatMap((item) => {
          if (!item || typeof item !== "object" || Array.isArray(item)) return [];
          const record = item as Record<string, unknown>;
          if (typeof record.deliverable_id !== "string" || typeof record.approach !== "string") return [];
          return [{
            title: deliverableTitles.get(record.deliverable_id) ?? "本轮交付材料",
            detail: record.approach,
          }];
        });
      }
    }
    if (Array.isArray(detail.deliverable_ids)) {
      const deliverables = new Map(task.contract.deliverables.map((item) => [item.deliverable_id, item]));
      return detail.deliverable_ids.flatMap((value) => {
        if (typeof value !== "string") return [];
        const deliverable = deliverables.get(value);
        return deliverable ? [{
          title: deliverable.title,
          detail: `完成条件：${deliverable.completion_criteria[0]}`,
        }] : [];
      });
    }
  }
  if (phase === "act" && Array.isArray(detail.deliverable_ids)) {
    return detail.deliverable_ids
      .filter((value): value is string => typeof value === "string")
      .map((value) => ({
        title: deliverableTitles.get(value) ?? "本轮交付材料",
        detail: "候选内容生成后仍需进入事实核对",
      }));
  }
  if (phase === "verify") {
    const conflictCount = Array.isArray(detail.conflict_ids) ? detail.conflict_ids.length : 0;
    const candidateCount = Array.isArray(detail.candidate_artifact_ids)
      ? detail.candidate_artifact_ids.length
      : 0;
    if (conflictCount) return [{ title: `发现 ${conflictCount} 项需确认事实`, detail: "只暂停受影响材料，其他材料保留已核对状态" }];
    if (candidateCount) return [{ title: `正在核对 ${candidateCount} 份候选材料`, detail: "逐项检查来源、内容和交付条件" }];
  }
  return [];
}

function branchTone(branch: BranchSnapshot, conflicts: ConflictRecord[]) {
  if (conflicts.some((conflict) => conflict.status === "open")) return "blocked";
  if (branch.status === "committed") return "complete";
  if (["failed", "cancelled"].includes(branch.status)) return "failed";
  if (["paused", "taken_over", "waiting_evidence"].includes(branch.status)) return "attention";
  return "active";
}

function BranchStatusIcon({ tone }: { tone: ReturnType<typeof branchTone> }) {
  if (tone === "complete") return <IconCircleCheck aria-hidden="true" />;
  if (tone === "blocked" || tone === "attention") return <IconAlertTriangle aria-hidden="true" />;
  if (tone === "failed") return <IconHandStop aria-hidden="true" />;
  return <IconBolt aria-hidden="true" />;
}

export function TaskWorkspaceHeader({
  task,
  mode,
  syncState,
  busy,
  creating,
  onModeChange,
  onRefresh,
  onCreate,
}: TaskWorkspaceHeaderProps) {
  const terminal = isTerminal(task);
  const modes = ["cockpit", "director", "artifacts", "manual"] as const;
  const cockpitMode = mode === "cockpit";

  function moveModeFocus(event: KeyboardEvent<HTMLButtonElement>, current: TaskDirectorViewMode) {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const currentIndex = modes.indexOf(current);
    const nextIndex = event.key === "Home"
      ? 0
      : event.key === "End"
        ? modes.length - 1
        : (currentIndex + (event.key === "ArrowRight" ? 1 : -1) + modes.length) % modes.length;
    const nextMode = modes[nextIndex];
    onModeChange(nextMode);
    window.requestAnimationFrame(() => document.getElementById(`task-view-tab-${nextMode}`)?.focus());
  }

  return (
    <header className="task-director-workspace-header">
      <div className="task-director-title">
        <span className="task-director-product-label">{cockpitMode ? "智能工作驾驶舱" : "持续任务协作"}</span>
        <div className="task-director-heading-row">
          <h1 id="task-director-workspace-title" tabIndex={-1}>
            {cockpitMode ? "今天的工作，应该怎么处理" : task?.contract.title ?? "经营汇报协作"}
          </h1>
        </div>
        <p>{cockpitMode
          ? "先比较工作价值、资料范围和并行收益，再决定用工具、单 Agent、固定流程还是协作群组。"
          : task?.contract.objective ?? "把长任务拆成可核对的材料，只在必须由你判断时暂停。"}</p>
        {!cockpitMode && task && (
          <div className="task-director-deliverables" aria-label="本轮产出">
            <span>本轮产出</span>
            {task.contract.deliverables.map((deliverable) => (
              <b key={deliverable.deliverable_id}>{deliverable.title}</b>
            ))}
          </div>
        )}
      </div>

      <div className="task-director-header-actions">
        <div className="task-director-mode-switch" role="tablist" aria-label="任务工作区视图">
          {([
            ["cockpit", "今日工作", IconLayoutDashboard],
            ["director", "长任务", IconTargetArrow],
            ["artifacts", "成果", IconFileDescription],
            ["manual", "执行记录", IconListCheck],
          ] as const).map(([target, label, ModeIcon]) => (
            <button
              key={target}
              id={`task-view-tab-${target}`}
              type="button"
              role="tab"
              aria-controls="task-view-panel"
              aria-selected={mode === target}
              tabIndex={mode === target ? 0 : -1}
              className={mode === target ? "active" : ""}
              onClick={() => onModeChange(target)}
              onKeyDown={(event) => moveModeFocus(event, target)}
            >
              <ModeIcon aria-hidden="true" />
              <span>{label}</span>
            </button>
          ))}
        </div>
        {(task || cockpitMode) && (
          <button
            className="task-director-icon-button"
            type="button"
            title={cockpitMode ? "刷新今日工作" : "刷新服务端状态"}
            aria-label={cockpitMode ? "刷新今日工作" : "刷新服务端状态"}
            disabled={busy || syncState === "loading"}
            onClick={onRefresh}
          >
            <IconRefresh aria-hidden="true" />
          </button>
        )}
        {!cockpitMode && terminal && (
          <button
            className="task-director-create-button"
            type="button"
            title="保留上一轮成果和记录，并创建、启动一项新的经营汇报任务"
            disabled={busy || creating}
            onClick={onCreate}
          >
            <IconPlayerPlay aria-hidden="true" />
            <span>{creating ? "正在准备" : "开始新一轮汇报"}</span>
          </button>
        )}
      </div>
    </header>
  );
}

function committedArtifacts(task: TaskSnapshot) {
  const committedIds = new Set(task.last_commit?.artifact_version_ids ?? []);
  const deliverableOrder = new Map(
    task.contract.deliverables.map((deliverable, index) => [deliverable.deliverable_id, index]),
  );
  return task.artifact_versions
    .filter((artifact) => committedIds.has(artifact.artifact_version_id))
    .sort((a, b) => (deliverableOrder.get(a.deliverable_id) ?? 999) - (deliverableOrder.get(b.deliverable_id) ?? 999));
}

function TaskNextStepBanner({
  task,
  disabled,
  onStart,
  onRetry,
  onShowDecisions,
  onOpenArtifact,
}: {
  task: TaskSnapshot;
  disabled: boolean;
  onStart: () => void;
  onRetry: () => void;
  onShowDecisions: () => void;
  onOpenArtifact: (artifactVersionId: string) => void;
}) {
  const openConflicts = task.conflicts.filter((conflict) => conflict.status === "open");
  const verified = verifiedBranchCount(task);
  const firstCommittedArtifact = committedArtifacts(task)[0] ?? null;

  let tone = "active";
  let label = TASK_STATUS_LABELS[task.status];
  let title = `正在准备 ${task.contract.title}`;
  let detail = `${verified} / ${task.branches.length} 份材料已核对。`;
  let action: { label: string; onClick: () => void } | null = null;

  if (task.status === "ready") {
    tone = "ready";
    label = "尚未开始";
    title = `准备 ${task.contract.deliverables.length} 份经营汇报材料`;
    detail = "系统会先生成经营分析、风险页和客户回复草稿；遇到必须由你判断的事实时会暂停。";
    action = { label: "开始准备汇报", onClick: onStart };
  } else if (["failed", "cancelled"].includes(task.status)) {
    tone = "failed";
    title = task.status === "failed" ? "任务需要处理后才能继续" : "本轮任务已取消";
    detail = task.last_error?.message ?? "当前没有可继续执行的步骤。";
    if (task.status === "failed" && task.last_error?.recoverable) {
      action = { label: "重新读取状态", onClick: onRetry };
    }
  } else if (task.status === "committed" && task.last_commit) {
    tone = "complete";
    label = "已完成";
    title = `${task.contract.title}已准备完成`;
    detail = task.last_commit.summary;
    if (firstCommittedArtifact) {
      action = { label: "查看成果", onClick: () => onOpenArtifact(firstCommittedArtifact.artifact_version_id) };
    }
  } else if (task.status === "waiting_input" && openConflicts.length > 0) {
    tone = "attention";
    label = "需要你确认";
    title = `还差 ${openConflicts.length} 个决定，确认后继续核对`;
    detail = `${verified} 份材料已核对；${openConflicts[0].subject}存在不同来源，需要你选择正式依据。`;
    action = { label: "查看待确认项", onClick: onShowDecisions };
  } else if (task.status === "paused") {
    tone = "attention";
    title = "任务已暂停";
    detail = "相关材料保持在最后确认状态，恢复后才会继续。";
  } else if (task.status === "taken_over") {
    tone = "attention";
    title = "当前分支由你接管";
    detail = "交还 Agent 后，系统才会继续准备后续材料。";
  }

  return (
    <section className={`task-next-step is-${tone}`} aria-labelledby="task-next-step-title">
      <div className="task-next-step-icon" aria-hidden="true">
        {tone === "complete"
          ? <IconCircleCheck />
          : tone === "attention" || tone === "failed"
            ? <IconAlertTriangle />
            : <IconTargetArrow />}
      </div>
      <div>
        <span>{label}</span>
        <h2 id="task-next-step-title">{title}</h2>
        <p>{detail}</p>
      </div>
      {action && (
        <button type="button" disabled={disabled} onClick={action.onClick}>
          {tone === "complete"
            ? <IconFileDescription aria-hidden="true" />
          : tone === "attention"
              ? <IconArrowRight aria-hidden="true" />
            : <IconPlayerPlay aria-hidden="true" />}
          <span>{action.label}</span>
        </button>
      )}
    </section>
  );
}

function TaskSummaryBar({
  task,
  syncState,
  transportState,
  onRetry,
}: {
  task: TaskSnapshot;
  syncState: SyncState;
  transportState: TaskTransportState;
  onRetry: () => void;
}) {
  const verified = verifiedBranchCount(task);
  const connected = transportState === "connected";
  const synced = syncState === "synced" && connected;
  return (
    <section className="task-director-summary" aria-label="任务状态摘要">
      <div>
        <IconListCheck aria-hidden="true" />
        <span>材料已核对</span>
        <strong>{verified} / {task.branches.length}</strong>
      </div>
      <div className={task.status === "waiting_input" ? "is-attention" : task.status === "committed" ? "is-confirmed" : ""}>
        <IconBolt aria-hidden="true" />
        <span>当前状态</span>
        <strong>{TASK_STATUS_LABELS[task.status]}</strong>
      </div>
      <div className={synced ? "is-confirmed" : "is-attention"}>
        <IconHistory aria-hidden="true" />
        <span>同步状态</span>
        <strong>{synced ? `已同步 v${task.version}` : "正在对账"}</strong>
        {!synced && <button type="button" onClick={onRetry}>立即对账</button>}
      </div>
    </section>
  );
}

function PhaseRail({
  task,
  selectedPhase,
  onSelect,
}: {
  task: TaskSnapshot;
  selectedPhase: TaskPhase;
  onSelect: (phase: TaskPhase) => void;
}) {
  return (
    <ol className="task-director-phases" aria-label="任务阶段">
      {PHASES.map((phase, index) => {
        const state = phaseState(task, phase.key);
        const selected = selectedPhase === phase.key;
        return (
          <li className={`is-${state}`} key={phase.key} aria-current={state === "current" ? "step" : undefined}>
            <button
              type="button"
              className={selected ? "is-selected" : ""}
              aria-label={`${phase.label}：${state === "complete" ? "已完成" : state === "current" ? "当前阶段" : "待处理"}`}
              aria-pressed={selected}
              disabled={state === "pending"}
              onClick={() => onSelect(phase.key)}
            >
              <span className="task-director-phase-icon">
                {state === "complete" ? <IconCheck aria-hidden="true" /> : index + 1}
              </span>
              <span>
                <strong>{phase.label}</strong>
                <small>{phase.summary}</small>
              </span>
            </button>
            {index < PHASES.length - 1 && <IconArrowRight className="task-director-phase-arrow" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

function StageDetail({
  task,
  phase,
  reviewing,
  onReturnCurrent,
}: {
  task: TaskSnapshot;
  phase: TaskPhase;
  reviewing: boolean;
  onReturnCurrent: () => void;
}) {
  const record = currentStageRecord(task, phase);
  const label = STAGE_LABELS[phase];
  const items = stageDetailItems(task, phase, record?.detail);
  const copy: Record<TaskPhase, string> = {
    contract: "任务目标和交付物已由服务端确认。",
    observe: "正在读取本轮允许的业务来源，不会读取未授权的系统。",
    plan: "服务端已将本轮目标拆成三份可独立核对的材料。",
    act: "候选材料正在生成，候选版本不会被当作已核对成果。",
    verify: "逐项核对来源；发现冲突时只暂停受影响的材料。",
    commit: "等待所有必需材料通过核对并形成不可变提交。",
  };
  return (
    <section className="task-stage-detail" aria-live="polite">
      <div>
        <span>{reviewing ? "阶段回看" : "当前阶段"}</span>
        <h2>{label}</h2>
        <p>{record?.summary ?? copy[phase]}</p>
        {record?.generation_source === "template_fallback" && (
          <small className="task-stage-detail-copy">模型结果未通过协议，本阶段使用安全模板继续。</small>
        )}
        {stageBlocked(task, phase) && <strong className="task-stage-blocked">等待你的决定后继续</strong>}
        {reviewing && (
          <button type="button" className="task-stage-return" onClick={onReturnCurrent}>
            <IconArrowLeft aria-hidden="true" />
            返回当前阶段
          </button>
        )}
      </div>
      <div>
        <span>{items.length ? "本阶段记录" : "本阶段会影响"}</span>
        <ul>
          {items.length
            ? items.map((item) => (
                <li key={`${item.title}:${item.detail}`}>
                  <strong>{item.title}</strong>
                  <small>{item.detail}</small>
                </li>
              ))
            : task.contract.deliverables.map((deliverable) => <li key={deliverable.deliverable_id}>{deliverable.title}</li>)}
        </ul>
      </div>
    </section>
  );
}

function TaskImpactPreview({
  conflict,
  option,
}: {
  conflict: ConflictRecord;
  option: ConflictResolutionOption;
}) {
  const impact = option.expected_impact;
  const titleId = `task-impact-preview-${conflict.conflict_id}`;
  const taskOutcome = impact.commit_created
    ? "核对通过后形成本轮成果"
    : impact.task_status
      ? TASK_STATUS_LABELS[impact.task_status]
      : "等待服务端返回下一状态";

  return (
    <section className="task-impact-preview" aria-labelledby={titleId}>
      <header>
        <IconGitCompare aria-hidden="true" />
        <div>
          <span>确认后会发生什么</span>
          <strong id={titleId}>影响预演：你的决定会怎样改变本轮工作</strong>
        </div>
      </header>

      <div className="task-impact-choice">
        <span>你的决定</span>
        <strong>{option.label}</strong>
        <small>{option.description}</small>
      </div>

      <ImpactChangeList changes={impact.changes} applied={false} />

      <div className="task-impact-outcome">
        <IconShieldCheck aria-hidden="true" />
        <div>
          <span>任务随后</span>
          <strong>{taskOutcome}</strong>
          <small>{impact.creates_verification_reports > 0
            ? `服务端预计重新核对 ${impact.creates_verification_reports} 项结果`
            : "不会用前端动画代替服务端核对"}</small>
        </div>
      </div>
    </section>
  );
}

function TaskImpactReceiptView({ task, receipt }: { task: TaskSnapshot; receipt: ImpactReceipt }) {
  const changed = receipt.changed_deliverable_ids.map((id) => deliverableTitle(task, id));
  const changedIds = new Set(receipt.changed_deliverable_ids);
  const preserved = task.contract.deliverables
    .filter((item) => !changedIds.has(item.deliverable_id))
    .map((item) => item.title);

  return (
    <section className="task-impact-receipt" role="status" aria-live="polite" aria-labelledby="task-impact-receipt-title">
      <header>
        <span className="task-impact-receipt-icon"><IconCircleCheck aria-hidden="true" /></span>
        <div>
          <span>服务端变化回执</span>
          <h2 id="task-impact-receipt-title">你的决定已经落实到材料中</h2>
          <p>{receipt.summary}</p>
        </div>
      </header>
      <ImpactChangeList changes={receipt.changes} applied />
      <dl>
        <div className="is-change">
          <dt>已改变</dt>
          <dd>{changed.length ? changed.join("、") : "没有材料被改写"}</dd>
          <small>{receipt.changed_artifact_version_ids.length > 0
            ? `生成 ${receipt.changed_artifact_version_ids.length} 个新材料版本`
            : "没有生成新版本"}</small>
        </div>
        <div className="is-verified">
          <dt>核对结果</dt>
          <dd>{impactVerificationLabel(receipt)}</dd>
          <small>{receipt.verification_report_ids.length} 项服务端核对记录</small>
        </div>
        <div className="is-preserved">
          <dt>保持不变</dt>
          <dd>{preserved.length ? preserved.join("、") : "无"}</dd>
          <small>未被这次决定重新生成</small>
        </div>
        <div className="is-boundary">
          <dt>外部动作</dt>
          <dd>{receipt.external_side_effect === "none" ? "未执行" : "进入独立治理"}</dd>
          <small>{receipt.commit_created ? "本轮成果已形成，客户回复仍是草稿" : "任务仍按服务端状态继续"}</small>
        </div>
      </dl>
      <details>
        <summary>查看运行记录</summary>
        <p>任务从 v{receipt.from_task_version} 更新到 v{receipt.to_task_version}{receipt.commit_id ? "，并形成最终提交" : ""}。</p>
      </details>
    </section>
  );
}

function CandidateMaterials({
  task,
  reviewing,
  onReturnCurrent,
}: {
  task: TaskSnapshot;
  reviewing: boolean;
  onReturnCurrent: () => void;
}) {
  const stage = currentStageRecord(task, "act");
  const stageIds = new Set(stage?.artifact_version_ids ?? []);
  const candidates = task.artifact_versions.filter((artifact) =>
    artifact.status === "candidate" && (!stageIds.size || stageIds.has(artifact.artifact_version_id)),
  );
  return (
    <section className="task-candidate-materials" aria-labelledby="task-candidate-materials-title">
      <div>
        <span>{reviewing ? "阶段回看" : "候选材料"}</span>
        <h2 id="task-candidate-materials-title">{candidates.length ? "已生成，等待事实核对" : "正在生成候选材料"}</h2>
        <p>{candidates.length
          ? "候选版本可以查看，但不会被当作本轮完成成果。"
          : "服务端确认候选版本后会逐份展示；当前不会提前标记为已生成。"}</p>
        {reviewing && (
          <button type="button" className="task-stage-return" onClick={onReturnCurrent}>
            <IconArrowLeft aria-hidden="true" />
            返回当前阶段
          </button>
        )}
      </div>
      <ul>
        {candidates.length
          ? candidates.map((artifact) => (
              <li key={artifact.artifact_version_id}>
                <strong>{artifact.title}</strong>
                <span>候选版本 v{artifact.version} · {artifact.source_refs.length} 个来源</span>
              </li>
            ))
          : <li><strong>候选材料尚未返回</strong><span>等待服务端确认生成结果。</span></li>}
      </ul>
    </section>
  );
}

function StageCard({
  eyebrow,
  title,
  detail,
  meta,
  tone,
  onClick,
}: {
  eyebrow: string;
  title: string;
  detail: string;
  meta: string;
  tone?: "neutral" | "success" | "warning" | "muted";
  onClick?: () => void;
}) {
  const content = (
    <>
      <span>{eyebrow}</span>
      <strong>{title}</strong>
      <p>{detail}</p>
      <small>{meta}</small>
    </>
  );
  return onClick ? (
    <button aria-label={`查看当前材料：${title}`} className={`task-director-stage-card is-${tone ?? "neutral"}`} type="button" onClick={onClick}>
      {content}
    </button>
  ) : (
    <article className={`task-director-stage-card is-${tone ?? "neutral"}`}>
      {content}
    </article>
  );
}

function BranchLane({
  task,
  branch,
  onOpenArtifact,
  collapsed = false,
}: {
  task: TaskSnapshot;
  branch: BranchSnapshot;
  onOpenArtifact: (artifactVersionId: string) => void;
  collapsed?: boolean;
}) {
  const conflicts = task.conflicts.filter((conflict) => conflict.branch_id === branch.branch_id);
  const openConflict = conflicts.find((conflict) => conflict.status === "open") ?? null;
  const head = latestHead(task, branch);
  const report = latestVerification(task, head);
  const tone = branchTone(branch, conflicts);
  const branchCheckpointReady = branch.status === "committed" && report?.status === "passed";
  const includedInFinalCommit = Boolean(
    head && task.last_commit?.artifact_version_ids.includes(head.artifact_version_id),
  );

  if (collapsed) {
    return (
      <li className={`task-director-lane task-director-lane-collapsed is-${tone}`}>
        <details>
          <summary>
            <BranchStatusIcon tone={tone} />
            <span><strong>{branch.title}</strong><small>{BRANCH_STATUS_LABELS[branch.status]} · 已核对</small></span>
            <b>展开</b>
          </summary>
          <div>
            <p>{branch.objective}</p>
            {head && <button type="button" onClick={() => onOpenArtifact(head.artifact_version_id)}>查看当前材料</button>}
          </div>
        </details>
      </li>
    );
  }

  return (
    <li className={`task-director-lane is-${tone}`}>
      <header className="task-director-branch-card">
        <div className="task-director-branch-title">
          <BranchStatusIcon tone={tone} />
          <div>
            <strong>{branch.title}</strong>
            <span>本轮交付材料</span>
          </div>
        </div>
        <b>{BRANCH_STATUS_LABELS[branch.status]}</b>
        <p>{branch.objective}</p>
        <time dateTime={branch.updated_at}>更新于 {formatTime(branch.updated_at)}</time>
      </header>

      <StageCard
        eyebrow="当前材料"
        title={head?.title ?? "等待生成"}
        detail={head ? (head.status === "verified" ? "内容已经过事实核对" : "内容已生成，等待事实核对") : "系统尚未生成此材料"}
        meta={head ? `${head.source_refs.length} 个来源 · v${head.version}` : "等待开始"}
        tone={head?.status === "verified" ? "success" : head ? "warning" : "muted"}
        onClick={head ? () => onOpenArtifact(head.artifact_version_id) : undefined}
      />
      <IconArrowRight className="task-director-lane-arrow" aria-hidden="true" />
      {openConflict ? (
        <article className="task-director-stage-card task-director-conflict-card is-warning">
          <span>证据冲突</span>
          <strong>{openConflict.subject}</strong>
          <p>{openConflict.summary}</p>
          <div className="task-director-candidate-values">
            {openConflict.candidate_values.map((value) => <small key={value}>{value}</small>)}
          </div>
        </article>
      ) : (
        <StageCard
          eyebrow="验证结果"
          title={verificationLabel(report)}
          detail={report?.checks[0]?.detail ?? "等待服务端验证记录"}
          meta={report ? `${report.checks.length} 项检查` : "无检查记录"}
          tone={report?.status === "passed" ? "success" : report ? "warning" : "muted"}
        />
      )}
      <IconArrowRight className="task-director-lane-arrow" aria-hidden="true" />
      <article className={`task-director-merge-card ${branchCheckpointReady ? "is-ready" : "is-waiting"}`}>
        {branchCheckpointReady ? <IconCircleCheck aria-hidden="true" /> : <IconArrowsExchange aria-hidden="true" />}
        <strong>{includedInFinalCommit ? "已纳入本轮成果" : branchCheckpointReady ? "材料已准备" : "等待完成"}</strong>
        <span>{includedInFinalCommit
          ? "当前版本已纳入本轮结果"
          : branchCheckpointReady
            ? "已核对，等待其他材料"
            : openConflict
              ? "先确认事实口径"
              : "等待后续处理"}</span>
      </article>
    </li>
  );
}

export function TaskDirectorCanvas({
  task,
  syncState,
  transportState,
  busy,
  creating,
  onCreate,
  onStart,
  onRetry,
  onShowDecisions,
  onOpenArtifact,
}: TaskDirectorCanvasProps) {
  const [selectedPhase, setSelectedPhase] = useState<TaskPhase | null>(null);

  useEffect(() => {
    setSelectedPhase(null);
  }, [task?.task_id, task?.version, task?.phase]);

  if (!task) {
    if (syncState !== "synced") {
      const unavailable = syncState === "offline";
      return (
        <section className="task-director-empty is-loading" aria-live="polite">
          {unavailable ? <IconAlertTriangle aria-hidden="true" /> : <IconHistory aria-hidden="true" />}
          <span>{unavailable ? "暂时无法读取" : "正在读取"}</span>
          <h2>{unavailable ? "经营汇报任务暂时不可用" : "正在读取经营汇报任务"}</h2>
          <p>{unavailable ? "保留当前页面，重新连接后会恢复最近确认的任务。" : "正在确认是否已有进行中的任务，请稍候。"}</p>
          {unavailable && <button type="button" onClick={onRetry}>重新连接</button>}
        </section>
      );
    }
    return (
      <section className="task-director-empty">
        <IconTargetArrow aria-hidden="true" />
        <span>本轮任务</span>
        <h2>准备客户 A 的经营汇报</h2>
        <p>系统会准备经营分析、风险页和客户回复草稿；遇到来源冲突时停下来请你确认。</p>
        <ul aria-label="本轮产出">
          <li>经营分析</li>
          <li>风险页</li>
          <li>客户回复草稿</li>
        </ul>
        <small>只生成和核对材料，不会替你发送邮件或写入外部系统。</small>
        <button type="button" disabled={busy || creating} onClick={onCreate}>
          <IconPlayerPlay aria-hidden="true" />
          <span>{creating ? "正在准备" : "开始准备汇报"}</span>
        </button>
      </section>
    );
  }

  const progressive = progressiveTask(task);
  const displayedPhase = selectedPhase ?? task.phase;
  const impactReceipt = latestImpactReceipt(task);
  const showingEarlyStage = progressive && ["observe", "plan"].includes(displayedPhase);
  const showingCandidates = progressive && displayedPhase === "act";
  const showingActiveVerification = progressive
    && displayedPhase === "verify"
    && task.status === "verifying";
  const decisionFocused = progressive
    && displayedPhase === "verify"
    && task.status === "waiting_input";
  const blockingBranchIds = new Set(
    task.conflicts.filter((conflict) => conflict.status === "open").map((conflict) => conflict.branch_id),
  );
  const visibleBranches = decisionFocused
    ? task.branches.filter((branch) => blockingBranchIds.has(branch.branch_id))
    : task.branches;
  const backgroundBranches = decisionFocused
    ? task.branches.filter((branch) => !blockingBranchIds.has(branch.branch_id))
    : [];

  return (
    <section className="task-director-canvas" aria-label="持续任务进度" aria-busy={Boolean(busy || creating)}>
      <TaskNextStepBanner
        task={task}
        disabled={busy || syncState !== "synced"}
        onStart={onStart}
        onRetry={onRetry}
        onShowDecisions={onShowDecisions}
        onOpenArtifact={onOpenArtifact}
      />
      <TaskSummaryBar
        task={task}
        syncState={syncState}
        transportState={transportState}
        onRetry={onRetry}
      />
      {impactReceipt && <TaskImpactReceiptView task={task} receipt={impactReceipt} />}
      {task.status === "ready" ? (
        <section className="task-ready-brief" aria-labelledby="task-ready-brief-title">
          <div>
            <span>本轮会得到</span>
            <h2 id="task-ready-brief-title">三份可以直接审阅的材料</h2>
            <ul>
              {task.contract.deliverables.map((deliverable) => (
                <li key={deliverable.deliverable_id}>
                  <IconFileDescription aria-hidden="true" />
                  <div><strong>{deliverable.title}</strong><small>{deliverable.completion_criteria[0]}</small></div>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <span>何时算完成</span>
            <h3>材料经过核对，冲突都有明确处理</h3>
            <p>{formatCompletionCriteria(task.contract.completion_criteria)}</p>
            <small>客户回复始终保留为草稿，不会由本轮任务直接发送。</small>
          </div>
        </section>
      ) : progressive && (showingEarlyStage || showingCandidates || showingActiveVerification) ? (
        <>
          <PhaseRail task={task} selectedPhase={displayedPhase} onSelect={setSelectedPhase} />
          {showingCandidates
            ? (
                <CandidateMaterials
                  task={task}
                  reviewing={displayedPhase !== task.phase}
                  onReturnCurrent={() => setSelectedPhase(null)}
                />
              )
            : (
                <StageDetail
                  task={task}
                  phase={displayedPhase}
                  reviewing={displayedPhase !== task.phase}
                  onReturnCurrent={() => setSelectedPhase(null)}
                />
              )}
        </>
      ) : (
        <>
          <div className="task-director-board-header">
            <div>
              <span>任务进展</span>
              <h2 id="task-director-board-title">三份材料的当前状态</h2>
            </div>
          </div>
          <PhaseRail task={task} selectedPhase={displayedPhase} onSelect={setSelectedPhase} />
          <ol className="task-director-lanes" aria-label="三份交付材料">
            {visibleBranches.map((branch) => (
              <BranchLane
                key={branch.branch_id}
                task={task}
                branch={branch}
                onOpenArtifact={onOpenArtifact}
                collapsed={false}
              />
            ))}
          </ol>
          {backgroundBranches.length > 0 && (
            <details className="task-background-materials">
              <summary>{backgroundBranches.length} 份材料已核对，展开查看</summary>
              <ol className="task-director-lanes" aria-label="已核对材料">
                {backgroundBranches.map((branch) => (
                  <BranchLane
                    key={branch.branch_id}
                    task={task}
                    branch={branch}
                    onOpenArtifact={onOpenArtifact}
                    collapsed
                  />
                ))}
              </ol>
            </details>
          )}
          <footer className="task-director-commit-bar">
            <div>
              {task.last_commit ? <IconCircleCheck aria-hidden="true" /> : <IconListCheck aria-hidden="true" />}
              <span>{task.last_commit ? "本轮结果" : "完成条件"}</span>
            </div>
            <strong>{task.last_commit?.summary ?? formatCompletionCriteria(task.contract.completion_criteria)}</strong>
            <span className="task-director-commit-evidence">{task.last_commit ? "审计记录已保存" : "等待全部材料完成"}</span>
          </footer>
        </>
      )}
    </section>
  );
}

function BranchControls({
  branch,
  disabled,
  onControl,
}: {
  branch: BranchSnapshot;
  disabled: boolean;
  onControl: (intent: ControlIntent) => Promise<boolean>;
}) {
  if (branch.status === "paused") {
    return (
      <button type="button" disabled={disabled} onClick={() => void onControl({ kind: "resume_branch", branch_id: branch.branch_id })}>
        <IconPlayerPlay aria-hidden="true" />
        <span>恢复分支</span>
      </button>
    );
  }
  if (branch.status === "taken_over") {
    return (
      <button type="button" disabled={disabled} onClick={() => void onControl({ kind: "return_control", branch_id: branch.branch_id })}>
        <IconRobot aria-hidden="true" />
        <span>交还 Agent</span>
      </button>
    );
  }
  if (["waiting_evidence", "running", "verifying", "queued"].includes(branch.status)) {
    return (
      <div className="task-decision-branch-controls">
        <button type="button" disabled={disabled} onClick={() => void onControl({ kind: "take_over", branch_id: branch.branch_id })}>
          <IconHandStop aria-hidden="true" />
          <span>接管此分支</span>
        </button>
        <button type="button" disabled={disabled} onClick={() => void onControl({ kind: "pause_branch", branch_id: branch.branch_id })}>
          <IconPlayerPause aria-hidden="true" />
          <span>暂停分支</span>
        </button>
      </div>
    );
  }
  return null;
}

function TaskNoDecisionState({
  task,
  disabled,
  actionDisabled,
  onControl,
  onOpenArtifact,
  onPrepareAction,
}: {
  task: TaskSnapshot;
  disabled: boolean;
  actionDisabled: boolean;
  onControl: (intent: ControlIntent) => Promise<boolean>;
  onOpenArtifact: (artifactVersionId: string) => void;
  onPrepareAction: (artifactVersionId: string) => void;
}) {
  if (task.status === "committed" && task.last_commit) {
    const artifacts = committedArtifacts(task);
    const replyDraft = artifacts.find(
      (artifact) => artifact.kind === "reply_draft" && artifact.content.send_status === "draft_only",
    );
    return (
      <section className="task-decision-empty is-complete">
        <IconCircleCheck aria-hidden="true" />
        <h3>本轮成果已准备好</h3>
        <p>{task.last_commit.summary}</p>
        <ul className="task-outcome-list" aria-label="本轮成果">
          {artifacts.map((artifact) => (
            <li key={artifact.artifact_version_id}>
              <button
                type="button"
                aria-label={`查看${artifact.title}`}
                onClick={() => onOpenArtifact(artifact.artifact_version_id)}
              >
                <IconFileDescription aria-hidden="true" />
                <span><strong>{artifact.title}</strong><small>已核对 · 查看成果</small></span>
              </button>
            </li>
          ))}
        </ul>
        {replyDraft && (
          <>
            <strong className="task-outcome-boundary">客户回复仍是草稿，未发送</strong>
            <div className="task-outcome-next-action">
              <div>
                <strong>下一步：准备发送客户回复</strong>
                <span>先创建受控动作，再显示风险、目标和确认要求。此时不会发送。</span>
              </div>
              <button
                type="button"
                disabled={actionDisabled}
                onClick={() => onPrepareAction(replyDraft.artifact_version_id)}
              >
                准备发送客户回复
              </button>
              <small>固定演示收件人为 customer@example.com；只在模拟环境执行，不会触达真实邮箱。</small>
            </div>
          </>
        )}
        <details className="task-decision-commit-evidence">
          <summary>查看运行与审计</summary>
          <code>{task.last_commit.state_hash}</code>
        </details>
      </section>
    );
  }
  if (["failed", "cancelled"].includes(task.status)) {
    return (
      <section className="task-decision-empty is-failed">
        <IconAlertTriangle aria-hidden="true" />
        <h3>{task.status === "failed" ? "任务未能继续" : "任务已取消"}</h3>
        <p>{task.last_error ? "查看上方失败原因与恢复建议。" : "可从左侧创建新一轮任务。"}</p>
      </section>
    );
  }
  if (task.status === "paused") {
    const pausedBranch = task.branches.find((branch) => branch.status === "paused");
    return (
      <section className="task-decision-empty is-warning">
        <IconPlayerPause aria-hidden="true" />
        <h3>任务已暂停</h3>
        <p>恢复相关分支后，服务端才会继续处理。</p>
        {pausedBranch && (
          <div className="task-decision-empty-controls">
            <BranchControls branch={pausedBranch} disabled={disabled} onControl={onControl} />
          </div>
        )}
      </section>
    );
  }
  if (task.status === "taken_over") {
    const takenOverBranch = task.branches.find((branch) => branch.status === "taken_over");
    return (
      <section className="task-decision-empty is-warning">
        <IconHandStop aria-hidden="true" />
        <h3>任务由你接管</h3>
        <p>交还 Agent 后，服务端才会继续自动处理。</p>
        {takenOverBranch && (
          <div className="task-decision-empty-controls">
            <BranchControls branch={takenOverBranch} disabled={disabled} onControl={onControl} />
          </div>
        )}
      </section>
    );
  }
  if (task.status === "waiting_input") {
    return (
      <section className="task-decision-empty is-warning">
        <IconAlertTriangle aria-hidden="true" />
        <h3>任务仍在等待输入</h3>
        <p>服务端尚未提供可操作的结构化冲突，请刷新状态后复核。</p>
      </section>
    );
  }
  const stage = currentStageRecord(task);
  if (progressiveTask(task) && stage && ["observe", "plan", "act", "verify"].includes(task.phase)) {
    return (
      <section className="task-decision-empty is-progress" role="status" aria-live="polite">
        <IconBolt aria-hidden="true" />
        <span>服务端已确认当前阶段</span>
        <h3>{STAGE_LABELS[task.phase]}进行中</h3>
        <p>{task.phase === "verify"
          ? "系统正在逐项核对 3 份候选材料；只有服务端确认冲突后，才会请求你做决定。"
          : stage.status === "running"
            ? "系统正在准备下一阶段，完成后会继续更新。"
            : "当前阶段已记录，正在等待下一次服务端确认。"}</p>
        <small>不会把本地动画或客户端计时当作任务完成。</small>
      </section>
    );
  }
  return (
    <section className="task-decision-empty">
      <IconBolt aria-hidden="true" />
      <h3>当前没有待决策项</h3>
      <p>系统正在依据本轮目标准备材料。</p>
    </section>
  );
}

export function TaskDecisionPane({
  task,
  syncState,
  transportState,
  busy,
  pending,
  errorMessage,
  onRetry,
  onControl,
  onOpenArtifact,
  onPrepareAction,
}: TaskDecisionPaneProps) {
  const [steerInstruction, setSteerInstruction] = useState("");
  const steerRef = useRef<HTMLTextAreaElement>(null);
  const openConflicts = task?.status === "waiting_input"
    ? task.conflicts.filter((conflict) => conflict.status === "open")
    : [];
  const terminal = isTerminal(task);
  const controlsDisabled = !task || syncState !== "synced" || busy || pending || terminal;
  const actionDisabled = !task || syncState !== "synced" || busy || pending;

  const branchById = useMemo(
    () => new Map(task?.branches.map((branch) => [branch.branch_id, branch]) ?? []),
    [task],
  );

  async function submitSteer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const instruction = steerInstruction.trim();
    if (!instruction || controlsDisabled) return;
    const accepted = await onControl({ kind: "steer", instruction });
    if (accepted) setSteerInstruction("");
  }

  function prepareEvidenceInstruction(conflict: ConflictRecord) {
    setSteerInstruction(`请补充“${conflict.subject}”两种口径的适用范围、更新时间与历史依据。`);
    window.requestAnimationFrame(() => steerRef.current?.focus());
  }

  return (
    <div id="task-side-panel" className="task-decision-layout" role="tabpanel" aria-labelledby="task-side-tab-decisions" tabIndex={-1}>
      <header className="task-decision-header">
        <div>
          <span>{openConflicts.length > 0 ? "需要你处理" : task && progressiveTask(task) ? "当前阶段" : "需要你处理"}</span>
          <h2>{openConflicts.length > 0 ? "现在需要你做什么" : task && progressiveTask(task) ? `${STAGE_LABELS[task.phase]}进展` : "现在需要你做什么"}</h2>
        </div>
        <b>{openConflicts.length}</b>
      </header>

      <div className="task-decision-transport" role="status" aria-live="polite">
        <i className={transportState === "connected" ? "is-online" : "is-interrupted"} />
        <span>{transportState === "connected"
          ? `已连接当前工作区${task ? ` · v${task.version}` : ""}`
          : transportState === "connecting"
            ? "正在连接当前工作区"
            : "连接中断，保留最后确认状态"}</span>
        {(syncState === "reconnecting" || syncState === "offline") && (
          <button type="button" onClick={onRetry}>立即对账</button>
        )}
      </div>

      <div className="task-decision-scroll">
        {errorMessage && <div className="task-decision-error" role="alert" aria-live="assertive">{errorMessage}</div>}

        {task?.last_error && (
          <section className="task-decision-failure" role="status" aria-live="polite">
            <IconAlertTriangle aria-hidden="true" />
            <div>
              <h3>{task.last_error.recoverable ? "任务需要恢复" : "任务未能继续"}</h3>
              <p>{task.last_error.message}</p>
              {task.last_error.user_action && <strong>{task.last_error.user_action}</strong>}
              {task.last_error.recoverable && <button type="button" onClick={onRetry}>重新读取状态</button>}
            </div>
          </section>
        )}

        {!task && (
          <section className="task-decision-empty">
            {syncState === "offline" ? <IconAlertTriangle aria-hidden="true" /> : <IconTargetArrow aria-hidden="true" />}
            <h3>{syncState === "synced"
              ? "还没有经营汇报任务"
              : syncState === "offline"
                ? "经营汇报任务暂时不可用"
                : "正在读取经营汇报任务"}</h3>
            <p>{syncState === "synced"
              ? "开始后，需要你判断的事实会集中显示在这里。"
              : syncState === "offline"
                ? "连接恢复后，这里会显示最近确认的待处理事项。"
                : "正在确认是否已有进行中的任务，请稍候。"}</p>
          </section>
        )}

        {task?.status === "ready" && (
          <section className="task-decision-start">
            <IconCircleCheck aria-hidden="true" />
            <h3>开始前无需确认</h3>
            <p>本轮尚未开始，目前没有需要你判断的事实。</p>
          </section>
        )}

        {openConflicts.length > 0 && (
          <section className="task-decision-group" aria-labelledby="task-decision-conflicts-title">
            <div className="task-decision-group-title">
              <h3 id="task-decision-conflicts-title" tabIndex={-1}>请确认 {openConflicts.length} 件事</h3>
              <span>确认后继续核对</span>
            </div>
            {openConflicts.map((conflict) => {
              const branch = branchById.get(conflict.branch_id);
              const head = task && branch ? latestHead(task, branch) : null;
              const headId = head?.artifact_version_id;
              const report = task ? latestVerification(task, head) : null;
              const decisionReason = report?.checks.find((check) => check.status === "conflict")?.detail
                ?? conflict.summary;
              const resolutionOption = conflict.resolution_options.find(
                (option) => option.selected_source_ref === OFFICIAL_REVENUE_SOURCE && option.executable,
              ) ?? null;
              const hasOfficialSource = conflict.source_refs.includes(OFFICIAL_REVENUE_SOURCE)
                && (conflict.resolution_options.length === 0 || Boolean(resolutionOption));
              const branchAllowsResolution = branch?.status === "waiting_evidence";
              const firstOpenConflict = openConflicts.find((item) => item.branch_id === conflict.branch_id);
              const isNextConflictForBranch = firstOpenConflict?.conflict_id === conflict.conflict_id;
              const hasRemainingConflictAfterThis = openConflicts.some(
                (item) => item.conflict_id !== conflict.conflict_id,
              );
              const canResolve = hasOfficialSource && branchAllowsResolution && isNextConflictForBranch;
              return (
                <article className="task-decision-card" key={conflict.conflict_id}>
                  <header>
                    <div>
                      <IconAlertTriangle aria-hidden="true" />
                      <span>需要确认</span>
                    </div>
                    <b>{branch?.title ?? "任务分支"}</b>
                  </header>
                  <h4>{conflict.subject}</h4>
                  <p>{conflict.summary}</p>
                  <section className="task-decision-why">
                    <strong>为什么需要你</strong>
                    <p>{decisionReason}</p>
                  </section>
                  <dl>
                    {conflict.candidate_values.map((value, index) => (
                      <div key={value}>
                        <dt>候选 {index + 1}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <details>
                    <summary>查看演示数据来源</summary>
                    <ul>
                      {projectSourceReferences(conflict.source_refs).map((source) => (
                        <li key={source.key}>{source.label}</li>
                      ))}
                    </ul>
                  </details>
                  {resolutionOption ? (
                    <TaskImpactPreview conflict={conflict} option={resolutionOption} />
                  ) : (
                    <section className="task-decision-impact">
                      <strong>确认后会发生什么</strong>
                      <p>{hasRemainingConflictAfterThis
                        ? "本次只会更新经营分析并保留其余待确认项；全部冲突处理完后，客户回复草稿才会重新核对。风险页保持已核对状态，客户回复不会发送。"
                        : "经营分析会改用 CRM 正式口径，客户回复草稿会同步核对；风险页保持已核对状态。页面会等待服务端返回新结果，客户回复不会发送。"}</p>
                    </section>
                  )}
                  <div className="task-decision-actions">
                    <button
                      className="is-primary"
                      type="button"
                      aria-describedby={resolutionOption ? `task-impact-preview-${conflict.conflict_id}` : undefined}
                      disabled={controlsDisabled || !canResolve}
                      onClick={() => void onControl({
                        kind: "resolve_evidence",
                        branch_id: conflict.branch_id,
                        resolution_option_id: resolutionOption?.option_id,
                        selected_source_ref: OFFICIAL_REVENUE_SOURCE,
                      })}
                    >
                      <IconCheck aria-hidden="true" />
                      <span>采用正式口径并继续核对</span>
                    </button>
                    {hasOfficialSource && branch && !branchAllowsResolution && (
                      <p className="task-decision-action-hint">
                        {branch.status === "paused"
                          ? "先恢复分支，再提交证据决定。"
                          : branch.status === "taken_over"
                            ? "先交还 Agent，再提交证据决定。"
                            : "当前分支状态不接受证据决定。"}
                      </p>
                    )}
                    {hasOfficialSource && branchAllowsResolution && !isNextConflictForBranch && (
                      <p className="task-decision-action-hint">请先处理同一材料中较早的待确认项。</p>
                    )}
                    {headId && (
                      <button type="button" onClick={() => onOpenArtifact(headId)}>
                        <IconFileDescription aria-hidden="true" />
                        <span>查看相关材料</span>
                      </button>
                    )}
                    <details className="task-decision-more-actions">
                      <summary>其他处理方式</summary>
                      <div>
                        <button type="button" disabled={controlsDisabled} onClick={() => prepareEvidenceInstruction(conflict)}>
                          <IconRobot aria-hidden="true" />
                          <span>补充更多依据</span>
                        </button>
                        {branch && <BranchControls branch={branch} disabled={controlsDisabled} onControl={onControl} />}
                      </div>
                    </details>
                  </div>
                </article>
              );
            })}
          </section>
        )}

        {task && task.status !== "ready" && openConflicts.length === 0 && (
      <TaskNoDecisionState
        task={task}
        disabled={controlsDisabled}
        actionDisabled={actionDisabled}
        onControl={onControl}
        onOpenArtifact={onOpenArtifact}
        onPrepareAction={onPrepareAction}
      />
        )}
      </div>

      {task && task.status !== "ready" && !terminal && (
        <form className="task-decision-composer" onSubmit={submitSteer}>
          <label htmlFor="task-director-steer">给当前任务下达方向指令</label>
          <div>
            <textarea
              ref={steerRef}
              id="task-director-steer"
              aria-label="方向指令"
              value={steerInstruction}
              onChange={(event) => setSteerInstruction(event.target.value)}
              placeholder="例如：补充预测口径的历史依据"
              disabled={controlsDisabled}
            />
            <button type="submit" aria-label="记录方向指令" title="记录方向指令" disabled={controlsDisabled || !steerInstruction.trim()}>
              <IconSend2 aria-hidden="true" />
            </button>
          </div>
          <small>指令提交后先记录为待应用，不会伪装成已完成。</small>
        </form>
      )}
    </div>
  );
}
