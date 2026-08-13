"use client";

import { FormEvent, KeyboardEvent, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconArrowsExchange,
  IconBolt,
  IconCheck,
  IconCircleCheck,
  IconFileDescription,
  IconHandStop,
  IconHistory,
  IconLayoutDashboard,
  IconListCheck,
  IconPlayerPause,
  IconPlayerPlay,
  IconRefresh,
  IconRobot,
  IconSend2,
  IconTargetArrow,
} from "@tabler/icons-react";

import { projectSourceReferences } from "./source-reference";
import type { ControlIntent, SyncState } from "./task-runtime-panel";
import type {
  ArtifactVersion,
  BranchSnapshot,
  ConflictRecord,
  TaskPhase,
  TaskSnapshot,
  VerificationReport,
} from "./task-types";

export type TaskDirectorViewMode = "director" | "artifacts" | "manual";
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

function phaseState(task: TaskSnapshot, phase: Exclude<TaskPhase, "contract">) {
  const current = PHASE_ORDER[task.phase];
  const target = PHASE_ORDER[phase];
  if (task.status === "committed" || target < current) return "complete";
  if (target === current) return "current";
  return "pending";
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
  const modes = ["director", "artifacts", "manual"] as const;

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
        <span className="task-director-product-label">持续任务协作</span>
        <div className="task-director-heading-row">
          <h1 id="task-director-workspace-title" tabIndex={-1}>{task?.contract.title ?? "经营汇报协作"}</h1>
        </div>
        <p>{task?.contract.objective ?? "把长任务拆成可核对的材料，只在必须由你判断时暂停。"}</p>
        {task && (
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
            ["director", "进度", IconLayoutDashboard],
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
        {task && (
          <button
            className="task-director-icon-button"
            type="button"
            title="刷新服务端状态"
            aria-label="刷新服务端状态"
            disabled={busy || syncState === "loading"}
            onClick={onRefresh}
          >
            <IconRefresh aria-hidden="true" />
          </button>
        )}
        {terminal && (
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
  onShowDecisions,
  onOpenArtifact,
}: {
  task: TaskSnapshot;
  disabled: boolean;
  onStart: () => void;
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

function PhaseRail({ task }: { task: TaskSnapshot }) {
  return (
    <ol className="task-director-phases" aria-label="任务阶段">
      {PHASES.map((phase, index) => {
        const state = phaseState(task, phase.key);
        return (
          <li className={`is-${state}`} key={phase.key} aria-current={state === "current" ? "step" : undefined}>
            <span className="task-director-phase-icon">
              {state === "complete" ? <IconCheck aria-hidden="true" /> : index + 1}
            </span>
            <div>
              <strong>{phase.label}</strong>
              <small>{phase.summary}</small>
            </div>
            {index < PHASES.length - 1 && <IconArrowRight className="task-director-phase-arrow" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
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
}: {
  task: TaskSnapshot;
  branch: BranchSnapshot;
  onOpenArtifact: (artifactVersionId: string) => void;
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

  return (
    <section className="task-director-canvas" aria-label="持续任务进度">
      <TaskNextStepBanner
        task={task}
        disabled={busy || syncState !== "synced"}
        onStart={onStart}
        onShowDecisions={onShowDecisions}
        onOpenArtifact={onOpenArtifact}
      />
      <TaskSummaryBar
        task={task}
        syncState={syncState}
        transportState={transportState}
        onRetry={onRetry}
      />
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
      ) : (
        <>
          <div className="task-director-board-header">
            <div>
              <span>任务进展</span>
              <h2 id="task-director-board-title">三份材料的当前状态</h2>
            </div>
          </div>
          <PhaseRail task={task} />
          <ol className="task-director-lanes" aria-label="三份交付材料">
            {task.branches.map((branch) => (
              <BranchLane key={branch.branch_id} task={task} branch={branch} onOpenArtifact={onOpenArtifact} />
            ))}
          </ol>
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
          <span>需要你处理</span>
          <h2>现在需要你做什么</h2>
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
              const hasOfficialSource = conflict.source_refs.includes(OFFICIAL_REVENUE_SOURCE);
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
                    <section className="task-decision-impact">
                      <strong>确认后会发生什么</strong>
                      <p>{hasRemainingConflictAfterThis
                        ? "本次只会更新经营分析并保留其余待确认项；全部冲突处理完后，客户回复草稿才会重新核对。风险页保持已核对状态，客户回复不会发送。"
                        : "经营分析会改用 CRM 正式口径，客户回复草稿会同步核对；风险页保持已核对状态。页面会等待服务端返回新结果，客户回复不会发送。"}</p>
                    </section>
                  <div className="task-decision-actions">
                    <button
                      className="is-primary"
                      type="button"
                      disabled={controlsDisabled || !canResolve}
                      onClick={() => void onControl({
                        kind: "resolve_evidence",
                        branch_id: conflict.branch_id,
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
