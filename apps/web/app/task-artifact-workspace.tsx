"use client";

import type { ReactNode } from "react";

import type {
  ArtifactStatus,
  ArtifactVersion,
  BranchSnapshot,
  ConflictRecord,
  DeliverableSpec,
  TaskSnapshot,
  VerificationReport,
  VerificationStatus,
} from "./task-types";
import { projectSourceReferences } from "./source-reference";

export type TaskArtifactWorkspaceProps = {
  task: TaskSnapshot | null;
  selectedArtifactVersionId?: string | null;
  selectionMode?: "follow_head" | "pinned_history";
  onSelectArtifact: (
    artifactVersionId: string,
    selectionMode?: "follow_head" | "pinned_history",
  ) => void;
  onPrepareAction?: (artifactVersionId: string) => void;
  actionBusy?: boolean;
};

export type TaskArtifactWorkspaceItem = {
  branch: BranchSnapshot;
  deliverable: DeliverableSpec | null;
  deliverableId: string;
  head: ArtifactVersion | null;
  headVerification: VerificationReport | null;
  lineage: ArtifactVersion[];
  conflicts: ConflictRecord[];
};

const ARTIFACT_STATUS_LABELS: Record<ArtifactStatus, string> = {
  candidate: "候选版本",
  verified: "已验证",
  rejected: "已驳回",
  committed: "已提交",
  invalidated: "已失效",
};

const VERIFICATION_STATUS_LABELS: Record<VerificationStatus, string> = {
  pending: "待验证",
  passed: "验证通过",
  failed: "验证失败",
  conflict: "存在冲突",
};

const CONFLICT_STATUS_LABELS: Record<ConflictRecord["status"], string> = {
  open: "待处理",
  resolved: "已解决",
  dismissed: "已忽略",
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

const ARTIFACT_KIND_LABELS: Record<string, string> = {
  analysis: "经营分析",
  risk_brief: "风险摘要",
  reply_draft: "客户回复草稿",
};

const CONTENT_FIELD_LABELS: Record<string, string> = {
  body: "正文",
  customer: "客户",
  forecast_delta_percent: "预测差异（%）",
  forecast_delta_wan: "预测差异（万元）",
  forecast_revenue_wan: "预测收入（万元）",
  level: "等级",
  mitigation: "缓解措施",
  official_revenue_wan: "正式收入（万元）",
  revenue_basis: "收入依据",
  risks: "风险项",
  selected_revenue_wan: "采用收入（万元）",
  send_status: "发送状态",
  subject: "主题",
  summary: "摘要",
};

const CONTENT_VALUE_LABELS: Record<string, string> = {
  draft_only: "仅草稿，未发送",
  high: "高",
  low: "低",
  medium: "中",
};

const VISIBLE_CONTENT_FIELDS_BY_KIND: Record<string, ReadonlySet<string>> = {
  analysis: new Set([
    "customer",
    "official_revenue_wan",
    "forecast_revenue_wan",
    "selected_revenue_wan",
    "revenue_basis",
    "forecast_delta_wan",
    "forecast_delta_percent",
    "summary",
  ]),
  risk_brief: new Set(["customer", "risks", "level", "summary", "mitigation"]),
  reply_draft: new Set([
    "customer",
    "subject",
    "body",
    "send_status",
    "official_revenue_wan",
    "forecast_revenue_wan",
    "forecast_delta_wan",
    "forecast_delta_percent",
    "revenue_basis",
  ]),
};

const EMPTY_VISIBLE_CONTENT_FIELDS = new Set<string>();

const INTERNAL_CONTENT_FIELD =
  /(^|_)(api_key|chain_of_thought|internal|logs?|prompt|raw_log|reasoning|secret|system_prompt|token|trace|trace_id|worker|worker_id|worker_messages)($|_)/i;

function formatDateTime(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("zh-CN");
}

function formatContentField(field: string) {
  return CONTENT_FIELD_LABELS[field] ?? field.replaceAll("_", " ");
}

function isInternalContentField(field: string) {
  const normalized = field
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-z0-9]+/gi, "_")
    .toLowerCase();
  return INTERNAL_CONTENT_FIELD.test(normalized);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function visibleRecordEntries(value: Record<string, unknown>, visibleFields: ReadonlySet<string>) {
  return Object.entries(value).filter(
    ([field]) => visibleFields.has(field) && !isInternalContentField(field),
  );
}

function StructuredValue({
  value,
  visibleFields,
}: {
  value: unknown;
  visibleFields: ReadonlySet<string>;
}): ReactNode {
  if (value === null || value === undefined || value === "") {
    return <span className="task-artifact-value-empty">尚未填写</span>;
  }

  if (typeof value === "boolean") {
    return <span className="task-artifact-value-primitive">{value ? "是" : "否"}</span>;
  }

  if (typeof value === "number") {
    return <span className="task-artifact-value-primitive">{value.toLocaleString("zh-CN")}</span>;
  }

  if (typeof value === "string") {
    return (
      <span className="task-artifact-value-text">{CONTENT_VALUE_LABELS[value] ?? value}</span>
    );
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return <span className="task-artifact-value-empty">暂无内容</span>;
    }

    return (
      <ol className="task-artifact-content-list">
        {value.map((item, index) => (
          <li key={index}>
            <StructuredValue value={item} visibleFields={visibleFields} />
          </li>
        ))}
      </ol>
    );
  }

  if (isRecord(value)) {
    const entries = visibleRecordEntries(value, visibleFields);
    if (entries.length === 0) {
      return <span className="task-artifact-value-empty">暂无可展示内容</span>;
    }

    return (
      <dl className="task-artifact-content-fields">
        {entries.map(([field, nestedValue]) => (
          <div className="task-artifact-content-field" key={field}>
            <dt>{formatContentField(field)}</dt>
            <dd>
              <StructuredValue value={nestedValue} visibleFields={visibleFields} />
            </dd>
          </div>
        ))}
      </dl>
    );
  }

  return <span className="task-artifact-value-empty">无法展示此字段</span>;
}

function buildLineage(head: ArtifactVersion, artifactsById: Map<string, ArtifactVersion>) {
  const lineage: ArtifactVersion[] = [];
  const seen = new Set<string>();
  let current: ArtifactVersion | undefined = head;

  while (
    current
    && current.artifact_id === head.artifact_id
    && !seen.has(current.artifact_version_id)
  ) {
    lineage.push(current);
    seen.add(current.artifact_version_id);
    current = current.parent_version_id ? artifactsById.get(current.parent_version_id) : undefined;
  }

  return lineage.reverse();
}

export function buildTaskArtifactWorkspace(task: TaskSnapshot): TaskArtifactWorkspaceItem[] {
  const artifactsById = new Map(
    task.artifact_versions.map((artifact) => [artifact.artifact_version_id, artifact]),
  );
  const deliverablesById = new Map(
    task.contract.deliverables.map((deliverable) => [deliverable.deliverable_id, deliverable]),
  );
  const reportsByArtifactId = new Map<string, VerificationReport>();

  for (const report of task.verification_reports) {
    const existing = reportsByArtifactId.get(report.artifact_version_id);
    if (!existing || existing.checked_at < report.checked_at) {
      reportsByArtifactId.set(report.artifact_version_id, report);
    }
  }

  return task.branches.flatMap((branch) => {
    const deliverableIds = Array.from(
      new Set([...branch.deliverable_ids, ...Object.keys(branch.artifact_heads)]),
    );
    const conflicts = task.conflicts.filter((conflict) => conflict.branch_id === branch.branch_id);

    if (deliverableIds.length === 0) {
      return [
        {
          branch,
          deliverable: null,
          deliverableId: "",
          head: null,
          headVerification: null,
          lineage: [],
          conflicts,
        },
      ];
    }

    return deliverableIds.map((deliverableId) => {
      const headId = branch.artifact_heads[deliverableId];
      const head = headId ? artifactsById.get(headId) ?? null : null;
      return {
        branch,
        deliverable: deliverablesById.get(deliverableId) ?? null,
        deliverableId,
        head,
        headVerification: head ? reportsByArtifactId.get(head.artifact_version_id) ?? null : null,
        lineage: head ? buildLineage(head, artifactsById) : [],
        conflicts,
      };
    });
  });
}

function VerificationBadge({ report }: { report: VerificationReport | null }) {
  if (!report) {
    return (
      <span className="task-artifact-verification task-artifact-verification-missing">
        尚无验证记录
      </span>
    );
  }

  return (
    <span
      className={`task-artifact-verification task-artifact-verification-${report.status}`}
      title={`验证于 ${formatDateTime(report.checked_at)}`}
    >
      {VERIFICATION_STATUS_LABELS[report.status]}
    </span>
  );
}

function SourceReferences({ sourceRefs, label }: { sourceRefs: string[]; label: string }) {
  return (
    <details className="task-artifact-sources">
      <summary>
        {label}（{sourceRefs.length}）
      </summary>
      {sourceRefs.length > 0 ? (
        <ul className="task-artifact-source-list">
          {projectSourceReferences(sourceRefs).map((source) => (
            <li key={source.key}>{source.label}</li>
          ))}
        </ul>
      ) : (
        <p className="task-artifact-source-empty">服务端尚未记录来源。</p>
      )}
    </details>
  );
}

function ConflictSummary({
  conflicts,
  historicalVersion,
  currentHeadVersion,
}: {
  conflicts: ConflictRecord[];
  historicalVersion: boolean;
  currentHeadVersion: number;
}) {
  if (conflicts.length === 0) return null;

  return (
    <section className="task-artifact-conflicts" aria-labelledby="task-artifact-conflicts-title">
      <header className="task-artifact-section-header">
        <h3 id="task-artifact-conflicts-title">{historicalVersion ? "当前任务冲突状态" : "证据冲突"}</h3>
        <span>{historicalVersion
          ? `当前分支头 v${currentHeadVersion}`
          : `${conflicts.filter((conflict) => conflict.status === "open").length} 项待处理`}</span>
      </header>
      {historicalVersion && (
        <p className="task-artifact-conflict-context-note">
          下方显示的是本轮任务当前记录的冲突状态；“已解决”不表示解决发生在当前分支头，
          也不代表正在查看的历史材料已经通过核对。
        </p>
      )}
      <ul className="task-artifact-conflict-list">
        {conflicts.map((conflict) => (
          <li
            className={`task-artifact-conflict task-artifact-conflict-${conflict.status}${historicalVersion ? " is-historical-context" : ""}`}
            key={conflict.conflict_id}
          >
            <article>
              <header className="task-artifact-conflict-header">
                <h4>{conflict.subject}</h4>
                <span>{historicalVersion && conflict.status === "resolved"
                  ? "本轮任务当前已解决"
                  : CONFLICT_STATUS_LABELS[conflict.status]}</span>
              </header>
              <p>{conflict.summary}</p>
              {conflict.candidate_values.length > 0 && (
                <div className="task-artifact-conflict-candidates">
                  <strong>候选值</strong>
                  <ul>
                    {conflict.candidate_values.map((value) => (
                      <li key={value}>{value}</li>
                    ))}
                  </ul>
                </div>
              )}
              {conflict.resolution && (
                <p className="task-artifact-conflict-resolution">
                  <strong>{historicalVersion ? "当前任务处理结果：" : "处理结果："}</strong>
                  {conflict.resolution}
                </p>
              )}
              <SourceReferences sourceRefs={conflict.source_refs} label="查看冲突的演示数据来源" />
            </article>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ArtifactDetail({
  item,
  artifact,
  reportsByArtifactId,
  selectedArtifactVersionId,
  onSelectArtifact,
  onPrepareAction,
  actionBusy = false,
  actionEligible = false,
}: {
  item: TaskArtifactWorkspaceItem;
  artifact: ArtifactVersion;
  reportsByArtifactId: Map<string, VerificationReport>;
  selectedArtifactVersionId: string;
  onSelectArtifact: TaskArtifactWorkspaceProps["onSelectArtifact"];
  onPrepareAction?: TaskArtifactWorkspaceProps["onPrepareAction"];
  actionBusy?: boolean;
  actionEligible?: boolean;
}) {
  const report = reportsByArtifactId.get(artifact.artifact_version_id) ?? null;
  const historicalVersion = Boolean(
    item.head && item.head.artifact_version_id !== artifact.artifact_version_id,
  );
  const visibleContentFields = VISIBLE_CONTENT_FIELDS_BY_KIND[artifact.kind]
    ?? EMPTY_VISIBLE_CONTENT_FIELDS;

  return (
    <article className="task-artifact-detail" aria-labelledby="task-artifact-detail-title">
      <header className="task-artifact-detail-header">
        <div>
          <span className="task-artifact-detail-branch">{item.branch.title}</span>
          <h2 id="task-artifact-detail-title">{artifact.title}</h2>
          <p>{item.deliverable?.completion_criteria.join("；") || item.branch.objective}</p>
        </div>
        <div className="task-artifact-detail-statuses" aria-label="工件状态">
          <span className={`task-artifact-status task-artifact-status-${artifact.status}`}>
            v{artifact.version} · {ARTIFACT_STATUS_LABELS[artifact.status]}
          </span>
          <VerificationBadge report={report} />
        </div>
      </header>

      {historicalVersion && item.head && (
        <aside className="task-artifact-history-warning" role="status">
          <div>
            <strong>正在查看历史版本 v{artifact.version}</strong>
            <p>当前分支头为 v{item.head.version}。服务端最新状态未被覆盖。</p>
          </div>
          <button
            type="button"
            onClick={() => onSelectArtifact(item.head!.artifact_version_id, "follow_head")}
          >
            返回当前版本
          </button>
        </aside>
      )}

      {item.branch.status === "waiting_evidence" && (
        <aside className="task-artifact-waiting" role="status">
          <strong>此分支正在等待证据</strong>
          <p>{item.branch.pause_reason || "服务端尚未确认继续执行所需的证据。"}</p>
        </aside>
      )}

      <ConflictSummary
        conflicts={item.conflicts}
        historicalVersion={historicalVersion}
        currentHeadVersion={item.head?.version ?? artifact.version}
      />

      <section className="task-artifact-content" aria-labelledby="task-artifact-content-title">
        <header className="task-artifact-section-header">
          <h3 id="task-artifact-content-title">工件内容</h3>
          <span>{ARTIFACT_KIND_LABELS[item.deliverable?.kind || artifact.kind] ?? "结构化工件"}</span>
        </header>
        {visibleRecordEntries(artifact.content, visibleContentFields).length > 0 ? (
          <StructuredValue value={artifact.content} visibleFields={visibleContentFields} />
        ) : (
          <p className="task-artifact-content-empty">暂无可展示的结构化内容。</p>
        )}
      </section>

      <SourceReferences sourceRefs={artifact.source_refs} label="查看工件的演示数据来源" />

      {report && (
        <details className="task-artifact-checks">
          <summary>查看验证检查（{report.checks.length}）</summary>
          {report.checks.length > 0 ? (
            <ul className="task-artifact-check-list">
              {report.checks.map((check) => (
                <li className={`task-artifact-check task-artifact-check-${check.status}`} key={check.check_id}>
                  <strong>{check.label}</strong>
                  <span>{check.detail}</span>
                  <SourceReferences sourceRefs={check.source_refs} label="查看检查项的演示数据来源" />
                </li>
              ))}
            </ul>
          ) : (
            <p className="task-artifact-check-empty">此验证报告没有逐项检查记录。</p>
          )}
        </details>
      )}

      {artifact.kind === "reply_draft" && report?.status === "passed" && !historicalVersion && actionEligible && (
        <section className="task-artifact-action" aria-labelledby="task-artifact-action-title">
          <div>
            <span>下一步</span>
            <h3 id="task-artifact-action-title">将这份已核对草稿交给动作治理</h3>
            <p>系统只准备发送动作，不会直接发送。收件人、风险和确认要求由服务端重新判断。</p>
          </div>
          <button
            type="button"
            disabled={actionBusy || !onPrepareAction}
            onClick={() => onPrepareAction?.(artifact.artifact_version_id)}
          >
            {actionBusy ? "正在准备" : "准备发送客户回复"}
          </button>
        </section>
      )}

      <section className="task-artifact-lineage" aria-labelledby="task-artifact-lineage-title">
        <header className="task-artifact-section-header">
          <h3 id="task-artifact-lineage-title">版本沿革</h3>
          <span>{item.lineage.length} 个版本</span>
        </header>
        <ol className="task-artifact-lineage-list">
          {item.lineage.map((version) => {
            const versionReport = reportsByArtifactId.get(version.artifact_version_id) ?? null;
            const selected = version.artifact_version_id === selectedArtifactVersionId;
            return (
              <li key={version.artifact_version_id}>
                <button
                  className={`task-artifact-lineage-button task-artifact-lineage-button-${version.status}${selected ? " task-artifact-lineage-button-selected" : ""}`}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => onSelectArtifact(
                    version.artifact_version_id,
                    version.artifact_version_id === item.head?.artifact_version_id
                      ? "follow_head"
                      : "pinned_history",
                  )}
                >
                  <span>v{version.version}</span>
                  <strong>{ARTIFACT_STATUS_LABELS[version.status]}</strong>
                  <small>
                    {versionReport
                      ? VERIFICATION_STATUS_LABELS[versionReport.status]
                      : "尚无验证记录"}
                  </small>
                  <time dateTime={version.created_at}>{formatDateTime(version.created_at)}</time>
                </button>
              </li>
            );
          })}
        </ol>
      </section>
    </article>
  );
}

export function TaskArtifactWorkspace({
  task,
  selectedArtifactVersionId,
  onSelectArtifact,
  onPrepareAction,
  actionBusy = false,
}: TaskArtifactWorkspaceProps) {
  if (!task) {
    return (
      <section className="task-artifact-workspace task-artifact-workspace-empty" aria-live="polite">
        <header className="task-artifact-workspace-header">
          <div>
            <span className="task-artifact-eyebrow">共享工件</span>
            <h2>交付物工作区</h2>
          </div>
        </header>
        <p>选择或创建任务后，这里将显示服务端确认的分支工件。</p>
      </section>
    );
  }

  const items = buildTaskArtifactWorkspace(task);
  const reportsByArtifactId = new Map<string, VerificationReport>();
  for (const report of task.verification_reports) {
    const existing = reportsByArtifactId.get(report.artifact_version_id);
    if (!existing || existing.checked_at < report.checked_at) {
      reportsByArtifactId.set(report.artifact_version_id, report);
    }
  }

  const itemsWithArtifacts = items.filter(
    (item): item is TaskArtifactWorkspaceItem & { head: ArtifactVersion } => item.head !== null,
  );
  const explicitArtifact = selectedArtifactVersionId
    ? task.artifact_versions.find(
        (artifact) => artifact.artifact_version_id === selectedArtifactVersionId,
      ) ?? null
    : null;
  const selectedItem = explicitArtifact
    ? itemsWithArtifacts.find((item) =>
        item.lineage.some(
          (version) => version.artifact_version_id === explicitArtifact.artifact_version_id,
        ),
      ) ?? null
    : itemsWithArtifacts[0] ?? null;
  const selectedArtifact = explicitArtifact && selectedItem
    ? explicitArtifact
    : selectedItem?.head ?? null;
  const effectiveSelectedArtifactId = selectedArtifact?.artifact_version_id ?? "";
  const openConflictCount = task.conflicts.filter((conflict) => conflict.status === "open").length;

  return (
    <section className="task-artifact-workspace" aria-labelledby="task-artifact-workspace-title">
      <header className="task-artifact-workspace-header">
        <div>
          <span className="task-artifact-eyebrow">共享工件</span>
          <h2 id="task-artifact-workspace-title">交付物工作区</h2>
        </div>
        <div className="task-artifact-workspace-summary" aria-label="工作区概况">
          <span>{task.branches.length} 个分支</span>
          <span>{itemsWithArtifacts.length} 个工件</span>
          {openConflictCount > 0 && <strong>{openConflictCount} 项冲突待处理</strong>}
        </div>
      </header>

      {task.status === "waiting_input" && (
        <aside className="task-artifact-task-waiting" role="status">
          任务正在等待你的决定。当前显示的是本轮最近确认的材料状态。
        </aside>
      )}

      <div className="task-artifact-workspace-body">
        <nav className="task-artifact-navigation" aria-label="任务分支与交付物">
          {items.length > 0 ? (
            <ul className="task-artifact-navigation-list">
              {items.map((item) => {
                const openBranchConflicts = item.conflicts.filter(
                  (conflict) => conflict.status === "open",
                ).length;
                const selected = item.head?.artifact_version_id === effectiveSelectedArtifactId;
                const itemKey = `${item.branch.branch_id}:${item.deliverableId || "empty"}`;

                return (
                  <li className="task-artifact-navigation-item" key={itemKey}>
                    <article>
                      <header className="task-artifact-navigation-header">
                        <div>
                          <h3>{item.branch.title}</h3>
                          <p>{item.deliverable?.title || item.deliverableId || "尚未定义交付物"}</p>
                        </div>
                        <span
                          className={`task-artifact-branch-status task-artifact-branch-status-${item.branch.status}`}
                        >
                          {BRANCH_STATUS_LABELS[item.branch.status]}
                        </span>
                      </header>

                      {item.head ? (
                        <button
                          className={`task-artifact-navigation-button${selected ? " task-artifact-navigation-button-selected" : ""}`}
                          type="button"
                          aria-pressed={selected}
                          aria-label={`查看${item.deliverable?.title || item.branch.title}`}
                          onClick={() => onSelectArtifact(item.head!.artifact_version_id, "follow_head")}
                        >
                          <span>v{item.head.version}</span>
                          <strong>{ARTIFACT_STATUS_LABELS[item.head.status]}</strong>
                          <small>
                            {item.headVerification
                              ? VERIFICATION_STATUS_LABELS[item.headVerification.status]
                              : "尚无验证记录"}
                          </small>
                        </button>
                      ) : (
                        <p className="task-artifact-navigation-empty">服务端尚未生成工件版本。</p>
                      )}

                      {openBranchConflicts > 0 && (
                        <p className="task-artifact-navigation-conflict">
                          {openBranchConflicts} 项证据冲突待处理
                        </p>
                      )}
                    </article>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="task-artifact-navigation-empty">此任务尚未建立分支或交付物。</p>
          )}
        </nav>

        <div className="task-artifact-detail-region">
          {selectedItem && selectedArtifact ? (
            <ArtifactDetail
              item={selectedItem}
              artifact={selectedArtifact}
              reportsByArtifactId={reportsByArtifactId}
              selectedArtifactVersionId={effectiveSelectedArtifactId}
              onSelectArtifact={onSelectArtifact}
              onPrepareAction={onPrepareAction}
              actionBusy={actionBusy}
              actionEligible={Boolean(
                task.status === "committed"
                && task.last_commit?.artifact_version_ids.includes(
                  selectedArtifact.artifact_version_id,
                ),
              )}
            />
          ) : (
            <section className="task-artifact-detail-empty" aria-live="polite">
              <h2>尚无可查看的工件</h2>
              <p>分支开始产出版本后，结构化内容、来源和验证结果会显示在这里。</p>
            </section>
          )}
        </div>
      </div>

      <footer className="task-artifact-commit">
        {task.last_commit ? (
          <>
            <div className="task-artifact-commit-heading">
              <span>最终提交</span>
              <strong>{task.last_commit.summary}</strong>
              <time dateTime={task.last_commit.committed_at}>
                {formatDateTime(task.last_commit.committed_at)}
              </time>
            </div>
            <dl className="task-artifact-commit-facts">
              <div>
                <dt>任务版本</dt>
                <dd>v{task.last_commit.task_version}</dd>
              </div>
              <div>
                <dt>提交工件</dt>
                <dd>{task.last_commit.artifact_version_ids.length} 个</dd>
              </div>
              <div>
                <dt>验证报告</dt>
                <dd>{task.last_commit.verification_report_ids.length} 份</dd>
              </div>
              <div>
                <dt>提交证据</dt>
                <dd>
                  <details className="task-artifact-commit-evidence">
                    <summary>查看状态哈希</summary>
                    <code>{task.last_commit.state_hash}</code>
                  </details>
                </dd>
              </div>
            </dl>
          </>
        ) : (
          <div className="task-artifact-commit-empty" role="status">
            <span>最终提交</span>
            <strong>尚未形成最终提交</strong>
            <p>当前进展：{TASK_STATUS_LABELS[task.status]}。</p>
          </div>
        )}
      </footer>
    </section>
  );
}
