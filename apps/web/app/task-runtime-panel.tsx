"use client";

import { FormEvent, useState } from "react";

import type { BranchSnapshot, TaskControlCommand, TaskSnapshot } from "./task-types";
import { projectSourceReferences } from "./source-reference";

type SyncState = "loading" | "connecting" | "synced" | "reconnecting" | "offline";

type ControlIntent = {
  kind: TaskControlCommand["kind"];
  branch_id?: string;
  instruction?: string;
  selected_source_ref?: string;
};

type TaskRuntimePanelProps = {
  task: TaskSnapshot | null;
  syncState: SyncState;
  busy: boolean;
  onStart: () => void;
  onControl: (intent: ControlIntent) => Promise<boolean>;
  onOpenArtifact: (artifactVersionId: string) => void;
};

const OFFICIAL_REVENUE_SOURCE = "fixture:crm/customer-a:official-revenue-v3";

const SYNC_LABELS: Record<SyncState, string> = {
  loading: "正在读取任务",
  connecting: "正在连接任务流",
  synced: "状态已同步",
  reconnecting: "连接中断，正在恢复",
  offline: "当前离线",
};

const BRANCH_STATUS_LABELS: Record<BranchSnapshot["status"], string> = {
  queued: "排队中",
  running: "运行中",
  waiting_evidence: "等待证据",
  paused: "已暂停",
  taken_over: "人工接管中",
  verifying: "验证中",
  failed: "失败",
  committed: "已提交",
  cancelled: "已取消",
};

function BranchControls({
  branch,
  disabled,
  onControl,
}: {
  branch: BranchSnapshot;
  disabled: boolean;
  onControl: (intent: ControlIntent) => Promise<boolean>;
}) {
  if (branch.status === "waiting_evidence") {
    return (
      <div className="task-branch-actions" aria-label={`${branch.title}控制`}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => void onControl({ kind: "pause_branch", branch_id: branch.branch_id })}
        >
          暂停分支
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => void onControl({ kind: "take_over", branch_id: branch.branch_id })}
        >
          接管
        </button>
      </div>
    );
  }

  if (branch.status === "paused") {
    return (
      <div className="task-branch-actions" aria-label={`${branch.title}控制`}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => void onControl({ kind: "resume_branch", branch_id: branch.branch_id })}
        >
          恢复分支
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => void onControl({ kind: "take_over", branch_id: branch.branch_id })}
        >
          接管
        </button>
      </div>
    );
  }

  if (branch.status === "taken_over") {
    return (
      <div className="task-branch-actions" aria-label={`${branch.title}控制`}>
        <button
          type="button"
          disabled={disabled}
          onClick={() => void onControl({ kind: "return_control", branch_id: branch.branch_id })}
        >
          交还 Agent
        </button>
      </div>
    );
  }

  return null;
}

export function TaskRuntimePanel({
  task,
  syncState,
  busy,
  onStart,
  onControl,
  onOpenArtifact,
}: TaskRuntimePanelProps) {
  const [steerInstruction, setSteerInstruction] = useState("");
  const taskTerminal = task ? ["committed", "failed", "cancelled"].includes(task.status) : false;
  const controlsDisabled = syncState !== "synced" || busy || taskTerminal;

  async function submitSteer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const instruction = steerInstruction.trim();
    if (!instruction || controlsDisabled) return;
    const accepted = await onControl({ kind: "steer", instruction });
    if (accepted) setSteerInstruction("");
  }

  if (!task) {
    return (
      <section
        className="task-runtime-panel task-runtime-panel-empty"
        aria-busy={syncState === "loading" || syncState === "connecting" || syncState === "reconnecting"}
      >
        <header className="task-runtime-header">
          <div>
            <span className="task-runtime-eyebrow">持续任务</span>
            <h2>任务运行状态</h2>
          </div>
          <span className={`runtime-sync-label is-${syncState}`} role="status" aria-live="polite">
            {SYNC_LABELS[syncState]}
          </span>
        </header>
        <p>{syncState === "offline" ? "无法读取任务状态。" : "正在获取服务端任务快照。"}</p>
      </section>
    );
  }

  const openConflicts = task.conflicts.filter((conflict) => conflict.status === "open");

  return (
    <section className="task-runtime-panel" aria-labelledby="task-runtime-title">
      <header className="task-runtime-header">
        <div>
          <span className="task-runtime-eyebrow">任务分支与证据</span>
          <h2 id="task-runtime-title">执行明细</h2>
        </div>
        <span className={`runtime-sync-label is-${syncState}`} role="status" aria-live="polite">
          {SYNC_LABELS[syncState]}
        </span>
      </header>

      {task.status === "ready" && (
        <div className="task-runtime-start">
          <button type="button" disabled={controlsDisabled} onClick={onStart}>
            启动任务
          </button>
        </div>
      )}

      {openConflicts.length > 0 && (
        <section className="task-conflicts" aria-labelledby="task-conflicts-title">
          <header>
            <h3 id="task-conflicts-title">待处理的证据冲突</h3>
            <span>{openConflicts.length} 项</span>
          </header>
          <div className="task-conflict-list">
            {openConflicts.map((conflict) => (
              <article className="task-conflict" key={conflict.conflict_id}>
                <header>
                  <h4>{conflict.subject}</h4>
                  <span>待处理</span>
                </header>
                <p>{conflict.summary}</p>
                <button
                  type="button"
                  disabled={controlsDisabled}
                  onClick={() => void onControl({
                    kind: "resolve_evidence",
                    branch_id: conflict.branch_id,
                    selected_source_ref: OFFICIAL_REVENUE_SOURCE,
                  })}
                >
                  采用正式收入来源
                </button>
                <details className="task-conflict-details">
                  <summary>查看候选值与演示数据来源</summary>
                  <div className="task-conflict-values">
                    <strong>候选值</strong>
                    <ul>
                      {conflict.candidate_values.map((value) => <li key={value}>{value}</li>)}
                    </ul>
                  </div>
                  <div className="task-conflict-sources">
                    <strong>来源</strong>
                    <ul>
                      {projectSourceReferences(conflict.source_refs).map((source) => (
                        <li key={source.key}>{source.label}</li>
                      ))}
                    </ul>
                  </div>
                </details>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="task-branches" aria-labelledby="task-branches-title">
        <header>
          <h3 id="task-branches-title">任务分支</h3>
          <span>{task.branches.length} 个</span>
        </header>
        <ul className="task-branch-list">
          {task.branches.map((branch) => (
            <li className={`task-branch is-${branch.status}`} key={branch.branch_id}>
              <article>
                <header className="task-branch-header">
                  <div>
                    <h4>{branch.title}</h4>
                    <p>{branch.objective}</p>
                  </div>
                  <span className={`task-branch-status is-${branch.status}`}>
                    {BRANCH_STATUS_LABELS[branch.status]}
                  </span>
                </header>
                {branch.pause_reason && <p className="task-branch-reason">{branch.pause_reason}</p>}
                {Object.entries(branch.artifact_heads).length > 0 && (
                  <div className="task-branch-artifacts" aria-label={`${branch.title}共享工件`}>
                    {Object.entries(branch.artifact_heads).map(([deliverableId, artifactVersionId]) => {
                      const deliverable = task.contract.deliverables.find(item => item.deliverable_id === deliverableId);
                      return (
                        <button
                          type="button"
                          key={artifactVersionId}
                          onClick={() => onOpenArtifact(artifactVersionId)}
                        >
                          查看{deliverable?.title ?? "工件"}
                        </button>
                      );
                    })}
                  </div>
                )}
                <BranchControls branch={branch} disabled={controlsDisabled} onControl={onControl} />
              </article>
            </li>
          ))}
        </ul>
      </section>

      {!taskTerminal && <form className="task-steer-form" onSubmit={submitSteer}>
        <label htmlFor="task-steer-instruction">方向指令</label>
        <div>
          <input
            id="task-steer-instruction"
            type="text"
            value={steerInstruction}
            onChange={(event) => setSteerInstruction(event.target.value)}
            placeholder="输入新的目标、范围或处理口径"
            disabled={controlsDisabled}
          />
          <button type="submit" disabled={controlsDisabled || !steerInstruction.trim()}>
            记录指令
          </button>
        </div>
      </form>}

      {task.last_commit && (
        <footer className="task-last-commit">
          <span>最近提交</span>
          <strong>{task.last_commit.summary}</strong>
          <time dateTime={task.last_commit.committed_at}>
            {new Date(task.last_commit.committed_at).toLocaleString("zh-CN")}
          </time>
        </footer>
      )}
    </section>
  );
}

export type { ControlIntent, SyncState, TaskRuntimePanelProps };
