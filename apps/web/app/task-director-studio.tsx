"use client";

import { FormEvent, KeyboardEvent, useMemo, useRef, useState } from "react";
import {
  IconAlertTriangle,
  IconArrowRight,
  IconArrowsExchange,
  IconBolt,
  IconCheck,
  IconCircleCheck,
  IconClock,
  IconFileDescription,
  IconGitBranch,
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
  IconUser,
} from "@tabler/icons-react";

import { formatSourceReference } from "./source-reference";
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
  onStart: () => void;
  onRetry: () => void;
  onControl: (intent: ControlIntent) => Promise<boolean>;
  onOpenArtifact: (artifactVersionId: string) => void;
};

const TASK_STATUS_LABELS: Record<TaskSnapshot["status"], string> = {
  ready: "等待启动",
  running: "运行中",
  waiting_input: "等待你的决定",
  paused: "已暂停",
  taken_over: "由你接管",
  verifying: "正在验证",
  committed: "已验证并提交",
  failed: "任务失败",
  cancelled: "已取消",
};

const BRANCH_STATUS_LABELS: Record<BranchSnapshot["status"], string> = {
  queued: "排队中",
  running: "运行中",
  waiting_evidence: "等待证据",
  paused: "已暂停",
  taken_over: "人工接管",
  verifying: "验证中",
  failed: "失败",
  committed: "已提交",
  cancelled: "已取消",
};

const PHASES: { key: Exclude<TaskPhase, "contract">; label: string; summary: string }[] = [
  { key: "observe", label: "观察", summary: "读取允许来源" },
  { key: "plan", label: "计划", summary: "拆解交付分支" },
  { key: "act", label: "执行", summary: "生成版本工件" },
  { key: "verify", label: "验证", summary: "核对事实与冲突" },
  { key: "commit", label: "提交", summary: "汇总已验证结果" },
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
        <span className="task-director-product-label">LONG-RUN OFFICE AGENT</span>
        <div className="task-director-heading-row">
          <h1>{task?.contract.title ?? "持续任务工作台"}</h1>
          {task && <span className="task-director-version">v{task.version}</span>}
        </div>
        <p>{task?.contract.objective ?? "创建任务契约后，这里会显示分支、工件、验证与人工决策。"}</p>
      </div>

      <div className="task-director-header-actions">
        <div className="task-director-mode-switch" role="tablist" aria-label="任务工作区视图">
          {([
            ["director", "指挥台", IconLayoutDashboard],
            ["artifacts", "共享工件", IconFileDescription],
            ["manual", "待办", IconListCheck],
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
        {(!task || terminal) && (
          <button
            className="task-director-create-button"
            type="button"
            disabled={busy || creating}
            onClick={onCreate}
          >
            <IconPlayerPlay aria-hidden="true" />
            <span>{creating ? "正在创建" : terminal ? "再次演示" : "创建任务"}</span>
          </button>
        )}
      </div>
    </header>
  );
}

function TaskSummaryBar({
  task,
  syncState,
  transportState,
  onRetry,
  onShowDecisions,
}: {
  task: TaskSnapshot;
  syncState: SyncState;
  transportState: TaskTransportState;
  onRetry: () => void;
  onShowDecisions: () => void;
}) {
  const openConflicts = task.conflicts.filter((conflict) => conflict.status === "open").length;
  const verified = verifiedBranchCount(task);
  const connected = transportState === "connected";
  return (
    <section className="task-director-summary" aria-label="任务事实摘要">
      <div>
        <IconUser aria-hidden="true" />
        <span>所有者</span>
        <strong>当前工作区用户</strong>
      </div>
      <div>
        <IconBolt aria-hidden="true" />
        <span>任务状态</span>
        <strong>{TASK_STATUS_LABELS[task.status]}</strong>
      </div>
      <div>
        <IconGitBranch aria-hidden="true" />
        <span>验证分支</span>
        <strong>{verified} / {task.branches.length}</strong>
      </div>
      <div className={syncState === "synced" && connected ? "is-confirmed" : "is-attention"}>
        <IconHistory aria-hidden="true" />
        <span>服务端 Snapshot</span>
        <strong>v{task.version}</strong>
        <small>{syncState === "synced" && connected ? "浏览器已同步" : "浏览器正在对账"}</small>
        {syncState !== "synced" && (
          <button type="button" onClick={onRetry}>立即对账</button>
        )}
      </div>
      <div className={openConflicts > 0 ? "is-blocked" : "is-confirmed"}>
        {openConflicts > 0 ? <IconAlertTriangle aria-hidden="true" /> : <IconCircleCheck aria-hidden="true" />}
        <span>需要你的决定</span>
        <strong>{openConflicts > 0 ? `${openConflicts} 个证据冲突` : "暂无阻塞项"}</strong>
        {openConflicts > 0 && (
          <button
            type="button"
            onClick={onShowDecisions}
          >
            查看决策
          </button>
        )}
      </div>
      <div>
        <IconClock aria-hidden="true" />
        <span>循环步数</span>
        <strong>{task.budget.steps_used} / {task.contract.budget.max_steps}</strong>
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
    <button className={`task-director-stage-card is-${tone ?? "neutral"}`} type="button" onClick={onClick}>
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
  const deliverable = task.contract.deliverables.find((item) => branch.deliverable_ids.includes(item.deliverable_id));
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
            <span>分支 v{branch.version}</span>
          </div>
        </div>
        <b>{BRANCH_STATUS_LABELS[branch.status]}</b>
        <p>{branch.objective}</p>
        <time dateTime={branch.updated_at}>更新于 {formatTime(branch.updated_at)}</time>
      </header>

      <StageCard
        eyebrow="任务契约"
        title="输入口径与范围"
        detail={`${task.contract.source_scope.length} 个允许来源`}
        meta={`契约 v${task.contract.contract_version}`}
      />
      <IconArrowRight className="task-director-lane-arrow" aria-hidden="true" />
      <StageCard
        eyebrow="交付定义"
        title={deliverable?.title ?? branch.title}
        detail={deliverable ? `${deliverable.completion_criteria.length} 条完成条件` : "等待交付定义"}
        meta={deliverable ? "任务契约定义" : "尚未定义类型"}
      />
      <IconArrowRight className="task-director-lane-arrow" aria-hidden="true" />
      <StageCard
        eyebrow="最新工件"
        title={head?.title ?? "等待生成"}
        detail={head ? `v${head.version} · ${head.status === "verified" ? "已验证" : "候选版本"}` : "此分支尚无服务端工件"}
        meta={head ? `${head.source_refs.length} 个来源` : "等待执行"}
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
        <strong>{includedInFinalCommit ? "已汇入最终提交" : branchCheckpointReady ? "分支已提交" : "等待汇聚"}</strong>
        <span>{includedInFinalCommit
          ? "该版本包含在最终提交"
          : branchCheckpointReady
            ? "检查点已形成，等待最终提交"
            : openConflict
              ? "先完成证据决策"
              : "等待后续阶段"}</span>
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
    return (
      <section className="task-director-empty">
        <IconTargetArrow aria-hidden="true" />
        <h2>把持续任务变成可见的协作过程</h2>
        <p>创建任务后，分支、工件、验证、冲突与人工控制都会由服务端事实驱动显示。</p>
        <button type="button" disabled={busy || creating} onClick={onCreate}>
          <IconPlayerPlay aria-hidden="true" />
          <span>{creating ? "正在创建" : "创建 Demo 1 任务"}</span>
        </button>
      </section>
    );
  }

  return (
    <section className="task-director-canvas" aria-labelledby="task-director-board-title">
      <TaskSummaryBar
        task={task}
        syncState={syncState}
        transportState={transportState}
        onRetry={onRetry}
        onShowDecisions={onShowDecisions}
      />
      <div className="task-director-board-header">
        <div>
          <span>ORCHESTRATION BOARD</span>
          <h2 id="task-director-board-title">任务编排与分支状态</h2>
        </div>
        <div className="task-director-board-actions">
          {task.status === "ready" && (
            <button className="task-director-primary-action" type="button" disabled={busy || syncState !== "synced"} onClick={onStart}>
              <IconPlayerPlay aria-hidden="true" />
              <span>启动任务</span>
            </button>
          )}
        </div>
      </div>
      <PhaseRail task={task} />
      <ol className="task-director-lanes" aria-label="任务分支泳道">
        {task.branches.map((branch) => (
          <BranchLane key={branch.branch_id} task={task} branch={branch} onOpenArtifact={onOpenArtifact} />
        ))}
      </ol>
      <footer className="task-director-commit-bar">
        <div>
          {task.last_commit ? <IconCircleCheck aria-hidden="true" /> : <IconListCheck aria-hidden="true" />}
          <span>{task.last_commit ? "最终提交" : "提交条件"}</span>
        </div>
        <strong>{task.last_commit?.summary ?? formatCompletionCriteria(task.contract.completion_criteria)}</strong>
        <span className="task-director-commit-evidence">{task.last_commit ? "提交证据已记录" : "等待最终提交"}</span>
      </footer>
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
  onControl,
}: {
  task: TaskSnapshot;
  disabled: boolean;
  onControl: (intent: ControlIntent) => Promise<boolean>;
}) {
  if (task.status === "committed" && task.last_commit) {
    return (
      <section className="task-decision-empty is-complete">
        <IconCircleCheck aria-hidden="true" />
        <h3>当前没有待决策项</h3>
        <p>{task.last_commit.summary}</p>
        <details className="task-decision-commit-evidence">
          <summary>查看提交证据</summary>
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
      <p>Agent 正在依据当前任务契约运行。</p>
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
  onStart,
  onRetry,
  onControl,
  onOpenArtifact,
}: TaskDecisionPaneProps) {
  const [steerInstruction, setSteerInstruction] = useState("");
  const steerRef = useRef<HTMLTextAreaElement>(null);
  const openConflicts = task?.conflicts.filter((conflict) => conflict.status === "open") ?? [];
  const terminal = isTerminal(task);
  const controlsDisabled = !task || syncState !== "synced" || busy || pending || terminal;

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
          <span>DECISION INBOX</span>
          <h2>待我决定</h2>
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
            <IconTargetArrow aria-hidden="true" />
            <h3>尚无持续任务</h3>
            <p>先在左侧创建任务契约。</p>
          </section>
        )}

        {task?.status === "ready" && (
          <section className="task-decision-start">
            <IconPlayerPlay aria-hidden="true" />
            <h3>任务已准备好</h3>
            <p>启动后会一次生成固定 Demo 1 的分支、工件与验证记录。</p>
            <button type="button" disabled={controlsDisabled} onClick={onStart}>启动任务</button>
          </section>
        )}

        {openConflicts.length > 0 && (
          <section className="task-decision-group" aria-labelledby="task-decision-conflicts-title">
            <div className="task-decision-group-title">
              <h3 id="task-decision-conflicts-title" tabIndex={-1}>需要你的决定</h3>
              <span>{openConflicts.length} 项</span>
            </div>
            {openConflicts.map((conflict) => {
              const branch = branchById.get(conflict.branch_id);
              const headId = branch ? Object.values(branch.artifact_heads)[0] : undefined;
              const hasOfficialSource = conflict.source_refs.includes(OFFICIAL_REVENUE_SOURCE);
              const branchAllowsResolution = branch?.status === "waiting_evidence";
              const canResolve = hasOfficialSource && branchAllowsResolution;
              return (
                <article className="task-decision-card" key={conflict.conflict_id}>
                  <header>
                    <div>
                      <IconAlertTriangle aria-hidden="true" />
                      <span>证据冲突</span>
                    </div>
                    <b>{branch?.title ?? "任务分支"}</b>
                  </header>
                  <h4>{conflict.subject}</h4>
                  <p>{conflict.summary}</p>
                  <dl>
                    {conflict.candidate_values.map((value, index) => (
                      <div key={value}>
                        <dt>候选 {index + 1}</dt>
                        <dd>{value}</dd>
                      </div>
                    ))}
                  </dl>
                  <details>
                    <summary>查看来源依据</summary>
                    <ul>
                      {conflict.source_refs.map((sourceRef, index) => (
                        <li key={`${sourceRef}:${index}`}>{formatSourceReference(sourceRef, index)}</li>
                      ))}
                    </ul>
                  </details>
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
                      <span>采用正式口径并保留差异</span>
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
                    {headId && (
                      <button type="button" onClick={() => onOpenArtifact(headId)}>
                        <IconFileDescription aria-hidden="true" />
                        <span>查看相关工件</span>
                      </button>
                    )}
                    <button type="button" disabled={controlsDisabled} onClick={() => prepareEvidenceInstruction(conflict)}>
                      <IconRobot aria-hidden="true" />
                      <span>准备补证指令</span>
                    </button>
                    {branch && <BranchControls branch={branch} disabled={controlsDisabled} onControl={onControl} />}
                  </div>
                </article>
              );
            })}
          </section>
        )}

        {task && task.status !== "ready" && openConflicts.length === 0 && (
          <TaskNoDecisionState task={task} disabled={controlsDisabled} onControl={onControl} />
        )}
      </div>

      <form className="task-decision-composer" onSubmit={submitSteer}>
        <label htmlFor="task-director-steer">给当前任务下达方向指令</label>
        <div>
          <textarea
            ref={steerRef}
            id="task-director-steer"
            aria-label="方向指令"
            value={steerInstruction}
            onChange={(event) => setSteerInstruction(event.target.value)}
            placeholder={terminal ? "任务已结束；创建新一轮后可继续下达指令" : "例如：补充预测口径的历史依据"}
            disabled={controlsDisabled}
          />
          <button type="submit" aria-label="记录方向指令" title="记录方向指令" disabled={controlsDisabled || !steerInstruction.trim()}>
            <IconSend2 aria-hidden="true" />
          </button>
        </div>
        <small>指令提交后先记录为待应用，不会伪装成已完成。</small>
      </form>
    </div>
  );
}
