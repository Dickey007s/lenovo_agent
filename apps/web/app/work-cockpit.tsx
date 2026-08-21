import {
  IconAlertTriangle,
  IconArrowRight,
  IconBolt,
  IconCheck,
  IconClock,
  IconFileDescription,
  IconLoader,
  IconRefresh,
  IconRobot,
  IconShieldCheck,
  IconSparkles,
  IconUsersGroup,
} from "@tabler/icons-react";
import { useEffect, useRef } from "react";

import { AgentCallTrace, type AgentCallStep } from "./agent-call-trace";
import type {
  Demo2CockpitSnapshot,
  Demo2RouteMode,
  Demo2RouteImpactChange,
  Demo2RouteProfile,
  Demo2RouteSelectionReceipt,
  Demo2ExecutionSnapshot,
  Demo2ArtifactVersion,
  Demo2WorkerRun,
  Demo2WorkUnitStatus,
  Demo2WorkItem,
  WorkCockpitDecisionPaneProps,
  WorkCockpitProps,
} from "./demo2-types";

const ROUTE_LABELS: Record<Demo2RouteMode, string> = {
  tool_call: "工具调用",
  single_agent: "单 Agent",
  fixed_workflow: "固定流程",
  adaptive_swarm: "自适应协作群组",
};

const ROUTE_ICONS: Record<Demo2RouteMode, typeof IconBolt> = {
  tool_call: IconBolt,
  single_agent: IconRobot,
  fixed_workflow: IconShieldCheck,
  adaptive_swarm: IconUsersGroup,
};

type DisplayRouteOption = Demo2RouteProfile & { available: boolean; recommended: boolean };

const BUSINESS_STATUS_LABELS: Record<Demo2WorkItem["business_status"], string> = {
  attention: "需要确定执行方式",
  ready: "已准备好路由",
  waiting: "等待处理",
};

const EXECUTION_STATUS_LABELS: Record<Demo2ExecutionSnapshot["status"], string> = {
  not_started: "待启动",
  queued: "已排队",
  running: "运行中",
  verifying: "验证中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

const UNIT_STATUS_LABELS: Record<Demo2WorkUnitStatus, string> = {
  queued: "待处理",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消",
};

function processingLabel(unit: Demo2WorkerRun) {
  if (unit.status === "failed") return "处理失败";
  const processing = unit.processing;
  if (!processing) return "处理来源待服务端回执";
  if (processing.output_used === "template_fallback") return "模板回退";
  if (
    processing.path === "language_model"
    && processing.kind === "language_model"
    && processing.model_called
    && processing.model
    && processing.output_used === "model"
  ) {
    return `模型已调用 · ${processing.model}`;
  }
  if (
    processing.path === "deterministic"
    && processing.kind === "deterministic"
    && !processing.model_called
    && processing.output_used === "deterministic"
  ) {
    return "确定性处理";
  }
  return "处理事实待核对";
}

function processingCategory(unit: Demo2WorkerRun) {
  if (unit.status === "failed") return "failed" as const;
  if (unit.processing?.output_used === "template_fallback") return "fallback" as const;
  if (
    unit.processing?.path === "language_model"
    && unit.processing.model_called
    && unit.processing.model
    && unit.processing.output_used === "model"
  ) return "model" as const;
  if (
    unit.processing?.path === "deterministic"
    && !unit.processing.model_called
    && unit.processing.output_used === "deterministic"
  ) return "deterministic" as const;
  return "pending" as const;
}

function executionHeading(status: Demo2ExecutionSnapshot["status"]) {
  if (status === "completed") return "业务工作包已收敛";
  if (status === "failed") return "业务工作包未完成";
  if (status === "cancelled") return "本次协作已取消";
  if (status === "verifying") return "业务工作包正在验证";
  if (status === "queued") return "业务工作包等待启动";
  return "业务工作包正在收敛";
}

function executionTone(status: Demo2ExecutionSnapshot["status"] | Demo2WorkUnitStatus) {
  return `is-${status.replaceAll("_", "-")}`;
}

function routeLabel(mode: Demo2RouteMode) {
  return ROUTE_LABELS[mode];
}

function routeOptions(item: Demo2WorkItem): DisplayRouteOption[] {
  return item.route_profiles.map((profile) => ({
    ...profile,
    available: item.allowed_modes.includes(profile.mode),
    recommended: profile.mode === item.recommendation.mode,
  }));
}

function routeOption(item: Demo2WorkItem, mode: Demo2RouteMode) {
  return routeOptions(item).find((option) => option.mode === mode) ?? null;
}

function formatRuntime(seconds: number) {
  if (seconds < 60) return `${seconds} 秒`;
  const minutes = Math.round(seconds / 60);
  return minutes < 60 ? `${minutes} 分钟` : `${Math.round(minutes / 60)} 小时`;
}

function statusLabel(item: Demo2WorkItem) {
  if (item.execution && item.execution.status !== "not_started") return EXECUTION_STATUS_LABELS[item.execution.status];
  if (item.execution_status !== "not_started") return EXECUTION_STATUS_LABELS[item.execution_status];
  return item.admission_status === "route_selected"
    ? "执行方式已记录"
    : BUSINESS_STATUS_LABELS[item.business_status];
}

function Demo2AgentCallTrace({ item }: { item: Demo2WorkItem }) {
  const receipt = item.selection_receipt;
  const routeStatus: AgentCallStep["status"] = receipt ? "complete" : "waiting";
  const processing = receipt?.processing;
  const execution = item.execution;
  const hasExecution = Boolean(execution && execution.status !== "not_started");
  const workersCreated = Boolean(execution?.worker_runs.length);
  const processingCounts = execution?.worker_runs.reduce((counts, worker) => {
    counts[processingCategory(worker)] += 1;
    return counts;
  }, { model: 0, fallback: 0, deterministic: 0, failed: 0, pending: 0 }) ?? { model: 0, fallback: 0, deterministic: 0, failed: 0, pending: 0 };
  const workerRuntimeStatus: AgentCallStep["status"] = !hasExecution
    ? "not_called"
    : execution?.status === "failed" || execution?.status === "cancelled"
      ? "blocked"
      : !workersCreated
        ? "waiting"
        : execution?.status === "completed"
          ? "complete"
          : execution?.worker_runs.some((worker) => worker.status === "running")
            ? "active"
            : "complete";
  const steps: AgentCallStep[] = [
    {
      id: "admission",
      label: "比较工作条件",
      component: "任务条件评估",
      kind: "rule",
      status: "complete",
      detail: `规则已根据价值、资料广度、并行性、时限、风险和资源边界给出“${routeLabel(item.recommendation.mode)}”建议。`,
      meta: "Admission Policy · 演示路由规则 v1 · 不调用大模型",
    },
    {
      id: "route",
      label: "记录本轮工作方式",
      component: "工作方式决策规则",
      kind: "rule",
      status: routeStatus,
      detail: receipt
        ? `服务端已记录“${routeLabel(receipt.selected_mode)}”，来源为${receipt.selection_source === "admission" ? "接受规则推荐" : "用户仅覆盖本轮"}。`
        : "服务端已生成推荐与影响预演，正在等待你决定是否记录本轮方式。",
      meta: processing
        ? `Route Policy Engine · ${processing.elapsed_ms} ms · 未调用大模型`
        : receipt
          ? "旧回执未提供处理耗时；路由语义仍由服务端规则产生"
          : "尚未提交本轮路由决定",
    },
    {
      id: "workers",
      label: "创建业务工作包",
      component: "受控协作运行时",
      kind: "runtime",
      status: workerRuntimeStatus,
      detail: workersCreated ? `服务端已创建 ${execution?.worker_runs.length ?? 0} 个受限业务工作包；前台只展示状态、允许来源与产物。` : hasExecution ? "执行记录已建立，服务端尚未返回业务工作包。" : "当前只预演并记录工作组织方式，没有创建或启动任何实际 Agent、Worker 或协作群组。",
      meta: hasExecution ? `模型采用 ${processingCounts.model} · 模板回退 ${processingCounts.fallback} · 确定性 ${processingCounts.deterministic} · 待回执 ${processingCounts.pending}` : "Worker Runtime · 尚未启动",
    },
    {
      id: "tools",
      label: "执行外部动作",
      component: "外部工具",
      kind: "tool",
      status: "not_called",
      detail: "路由选择不会写入邮件、CRM、日历或其他外部系统。",
      meta: "Connector / Tool Gateway · 未进入 · 外部副作用为零",
    },
  ];

  return <AgentCallTrace
    demo="Demo 2"
    summary={hasExecution ? "本轮先由 Admission 选择组织方式，再由受控协作运行时推进业务工作包；模型、回退和确定性处理只按服务端回执计数。" : "本轮只调用服务端 Admission 与路由规则；大模型、Worker 和外部工具都没有被调用。"}
    metrics={hasExecution ? [
      { label: `模型采用 ${processingCounts.model}`, tone: processingCounts.model ? "model" : "safe" },
      { label: `模型回退 ${processingCounts.fallback}`, tone: processingCounts.fallback ? "warning" : "safe" },
      { label: `确定性 ${processingCounts.deterministic}`, tone: "rule" },
      { label: processingCounts.failed ? `处理失败 ${processingCounts.failed}` : processingCounts.pending ? `待回执 ${processingCounts.pending}` : "外部工具 0", tone: processingCounts.failed ? "warning" : "safe" },
    ] : [
      { label: "规则引擎已调用", tone: "rule" },
      { label: "大模型 0", tone: "safe" },
      { label: "Worker 0", tone: "safe" },
      { label: "外部工具 0", tone: "safe" },
    ]}
    steps={steps}
    boundary="这里的预计时间、工具次数和并行单元来自演示策略预测，不是实际运行、真实账单或 SLA。"
  />;
}

function sourceLabel(sourceId: string) {
  const normalized = sourceId.toLowerCase();
  if (normalized.includes("forecast")) return "销售预测";
  if (normalized.includes("crm") || normalized.includes("revenue")) return "CRM 财务记录";
  if (normalized.includes("project") || normalized.includes("status")) return "项目周报";
  if (normalized.includes("mail") || normalized.includes("request")) return "客户邮件";
  if (normalized.includes("calendar")) return "日历";
  return "受限业务资料";
}

function replanReason(reason: string | undefined) {
  if (reason === "recognized_revenue_vs_forecast_revenue") {
    return "正式收入与预测收入存在口径冲突，需要增加专项核验。";
  }
  if (reason && !/^[a-z0-9_.:-]+$/i.test(reason)) return reason;
  return "服务端根据当前工作包事实调整了协作计划。";
}

function WorkUnitCard({ unit, artifacts }: { unit: Demo2WorkerRun; artifacts: Demo2ArtifactVersion[] }) {
  const artifact = unit.artifact_version_id ? artifacts.find((candidate) => candidate.artifact_version_id === unit.artifact_version_id) : null;
  return (
    <article className={`demo2-work-unit ${executionTone(unit.status)}`} aria-label={`${unit.label} · ${UNIT_STATUS_LABELS[unit.status]}`}>
      <header>
        <div className="demo2-work-unit-mark" aria-hidden="true">
          {unit.status === "running" ? <IconLoader /> : unit.status === "completed" ? <IconCheck /> : unit.status === "failed" || unit.status === "cancelled" ? <IconAlertTriangle /> : <IconClock />}
        </div>
        <div>
          <strong>{unit.label}</strong>
          <span className="demo2-execution-status">{UNIT_STATUS_LABELS[unit.status]}</span>
        </div>
      </header>
      <p>{unit.objective}</p>
      <div className="demo2-work-unit-sources">
        <span>允许来源</span>
        <div>{unit.source_document_ids.map((source) => <b key={source}>{sourceLabel(source)}</b>)}</div>
      </div>
      <div className="demo2-work-unit-processing">
        <IconSparkles aria-hidden="true" />
        <span>{processingLabel(unit)}</span>
        {unit.processing?.elapsed_ms !== null && unit.processing?.elapsed_ms !== undefined && <small>{unit.processing.elapsed_ms} ms</small>}
      </div>
      {unit.status !== "completed" && unit.status !== "queued" && <div className="demo2-work-unit-detail">{unit.status === "running" ? "正在处理允许来源。" : "服务端已记录当前工作包状态。"}</div>}
      {artifact && (
        <div className={`demo2-work-unit-artifact is-${artifact.status === "validated" ? "verified" : "draft"}`}>
          <IconFileDescription aria-hidden="true" />
          <div><span>产物 · {artifact.title}</span><strong>{artifact.status === "validated" ? "已通过服务端来源验证。" : "已生成，等待共享工件验证。"}</strong></div>
        </div>
      )}
    </article>
  );
}

function Demo2ExecutionBoard({ execution }: { execution: Demo2ExecutionSnapshot }) {
  const terminal = execution.status === "completed" || execution.status === "failed" || execution.status === "cancelled";
  const verifiedArtifact = execution.artifacts.find((artifact) => artifact.kind === "verified_report_bundle");
  const workerArtifacts = execution.artifacts.filter((artifact) => artifact.kind === "worker_finding");
  const verifiedCount = workerArtifacts.filter((artifact) => artifact.status === "validated").length;
  const replanEvents = execution.events.filter((event) => event.event_type === "DYNAMIC_REPLAN" || event.event_type === "WORKER_ADDED");
  return (
    <section className="demo2-execution-board" aria-labelledby="demo2-execution-title" aria-live="polite">
      <header className="demo2-execution-header">
        <div>
          <span className="work-cockpit-eyebrow">本次协作</span>
          <h3 id="demo2-execution-title">{executionHeading(execution.status)}</h3>
          <p>服务端按允许来源创建受限业务工作包，完成后汇总为共享工件并进行统一验证。</p>
        </div>
        <strong className={`demo2-execution-status ${executionTone(execution.status)}`}>{EXECUTION_STATUS_LABELS[execution.status]}</strong>
      </header>

      <section className="demo2-work-plan" aria-labelledby="demo2-work-plan-title">
        <div className="demo2-execution-section-heading"><span>协作计划</span><strong id="demo2-work-plan-title">{execution.worker_runs.filter((unit) => unit.trigger !== "verification").length} 个工作包</strong></div>
        <div className="demo2-work-unit-grid">
          {execution.worker_runs.filter((unit) => unit.trigger !== "verification").map((unit) => <WorkUnitCard key={unit.worker_run_id} unit={unit} artifacts={execution.artifacts} />)}
        </div>
      </section>

      {replanEvents.length > 0 && (
        <details className="demo2-replan-log">
          <summary><span>调度变化</span><strong>{replanEvents.length} 条服务端记录</strong></summary>
          <ol>
            {replanEvents.map((event) => <li key={event.sequence}><b>{event.message}</b><span>{replanReason(event.details.reason)}</span></li>)}
          </ol>
        </details>
      )}

      {verifiedArtifact && (
        <section className="demo2-shared-artifact is-verified" aria-labelledby="demo2-shared-artifact-title">
          <div className="demo2-execution-section-heading"><span>共享工件验证</span><strong id="demo2-shared-artifact-title">{verifiedArtifact.title}</strong></div>
          <div className="demo2-shared-artifact-body">
            <div className="demo2-shared-progress" aria-label={`已验证 ${verifiedCount} 个，共 ${execution.worker_runs.filter((unit) => unit.trigger !== "verification").length} 个`}>
              <span style={{ width: `${execution.worker_runs.length ? Math.round(verifiedCount / Math.max(1, execution.worker_runs.filter((unit) => unit.trigger !== "verification").length) * 100) : 0}%` }} />
            </div>
            <strong>{verifiedCount}/{Math.max(1, execution.worker_runs.filter((unit) => unit.trigger !== "verification").length)} 个工作包已验证</strong>
            <p>{verifiedArtifact.status === "validated" ? "共享工件已通过服务端来源和一致性验证。" : "工作包产物已汇入，等待最终共享工件验证。"}</p>
          </div>
        </section>
      )}

      {terminal && execution.receipt && (
        <section className={`demo2-execution-receipt ${execution.receipt.status === "completed" ? "is-completed" : "is-failed"}`} aria-labelledby="demo2-execution-receipt-title">
          <div className="demo2-execution-section-heading"><span>内部执行回执</span><strong id="demo2-execution-receipt-title">{execution.receipt.status === "completed" ? "本次协作已完成" : "本次协作未完成"}</strong></div>
          <p>{execution.receipt.summary}</p>
          <div className="demo2-receipt-boundaries"><b>不会发生</b><span>不会发送邮件、写入 CRM 或调用外部业务系统</span><b>保持不变</b><span>原始资料、任务内容与外部系统状态保持不变</span></div>
        </section>
      )}

      <details className="demo2-execution-audit">
        <summary><span>查看处理来源</span><strong>技术信息</strong></summary>
        <p>仅展示服务端已返回的处理类型和状态，不展示 Prompt、思维链、Worker 对话或内部标识。</p>
        <ul>{execution.worker_runs.map((unit) => <li key={unit.worker_run_id}><span>{unit.label}</span><b>{processingLabel(unit)}</b></li>)}</ul>
      </details>
    </section>
  );
}

const IMPACT_KIND_LABELS = {
  change: "会改变",
  preserve: "保持不变",
  no_external_action: "不会发生",
} as const;

const IMPACT_ICONS: Record<Demo2RouteImpactChange["aspect"], typeof IconBolt> = {
  route_decision: IconArrowRight,
  work_allocation: IconBolt,
  coordination: IconUsersGroup,
  human_control: IconCheck,
  policy_forecast: IconSparkles,
  execution_boundary: IconShieldCheck,
  external_action: IconAlertTriangle,
};

function ImpactRows({ changes, applied }: { changes: Demo2RouteImpactChange[]; applied: boolean }) {
  return (
    <dl className="work-cockpit-impact-rows">
      {changes.map((change) => (
        <div className={`is-${change.change_kind}`} key={`${change.aspect}-${change.label}`}>
          <dt>
            <span>{applied && change.change_kind === "change" ? "已记录" : IMPACT_KIND_LABELS[change.change_kind]}</span>
            <strong>{change.label}</strong>
          </dt>
          <dd>
            {change.before && <small>{change.before}</small>}
            <IconArrowRight aria-hidden="true" />
            <b>{change.after}</b>
            {change.detail && <em>{change.detail}</em>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function RouteImpactCanvas({
  option,
  receipt,
  isServerSelected,
  previewingOverride,
}: {
  option: Demo2RouteProfile;
  receipt: Demo2RouteSelectionReceipt | null;
  isServerSelected: boolean;
  previewingOverride: boolean;
}) {
  const preview = option.impact_preview;
  if (!preview) return null;
  const appliedReceipt = receipt?.selected_mode === option.mode ? receipt : null;
  const changes = appliedReceipt?.changes ?? preview.changes;
  const stateClass = appliedReceipt ? " is-recorded" : isServerSelected ? " is-server-selected" : "";
  const title = appliedReceipt
    ? `本次已选择${routeLabel(option.mode)}`
    : previewingOverride
      ? `如果改为${routeLabel(option.mode)}，工作会怎样展开`
      : isServerSelected
        ? `服务端当前方式：${routeLabel(option.mode)}`
        : `如果选择${routeLabel(option.mode)}，工作会怎样展开`;
  return (
    <section className={`work-cockpit-impact-canvas${stateClass}`} aria-live="polite" aria-labelledby="work-cockpit-impact-canvas-title">
      <header>
        <div>
          <span>{appliedReceipt ? "选择后的影响" : isServerSelected ? "服务端当前方式" : "工作方式影响地图"}</span>
          <h3 id="work-cockpit-impact-canvas-title">{title}</h3>
          <p>{appliedReceipt?.summary ?? preview.summary}</p>
        </div>
        <b>{appliedReceipt ? "已记录 · 未执行" : isServerSelected ? "当前方式 · 未执行" : "选择前预演"}</b>
      </header>
      <div className="work-cockpit-impact-canvas-grid">
        {changes.map((change) => {
          const ImpactIcon = IMPACT_ICONS[change.aspect];
          return (
          <article className={`is-${change.change_kind}`} key={`${change.aspect}-${change.label}`}>
            <span><ImpactIcon aria-hidden="true" /></span>
            <div>
              <small>{appliedReceipt && change.change_kind === "change" ? "已记录" : IMPACT_KIND_LABELS[change.change_kind]}</small>
              <strong>{change.label}</strong>
              {change.before && <span className="work-cockpit-impact-before">{change.before}<IconArrowRight aria-hidden="true" /></span>}
              <p>{change.after}</p>
              {change.detail && <em>{change.detail}</em>}
            </div>
          </article>
          );
        })}
      </div>
    </section>
  );
}

function RouteSelectionReceiptView({ receipt, historyCount }: { receipt: Demo2RouteSelectionReceipt; historyCount: number }) {
  const receiptRef = useRef<HTMLElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    receiptRef.current?.scrollIntoView({ block: "nearest" });
    titleRef.current?.focus({ preventScroll: true });
  }, [receipt.receipt_id]);
  return (
    <section ref={receiptRef} className="work-cockpit-selection-receipt" role="status" aria-live="polite" aria-labelledby="work-cockpit-selection-receipt-title">
      <header>
        <div>
          <span>服务端路由回执</span>
          <h3 id="work-cockpit-selection-receipt-title" ref={titleRef} tabIndex={-1}>本次工作方式已记录</h3>
        </div>
        <b>尚未执行</b>
      </header>
      <p>{receipt.summary}</p>
      <div className="work-cockpit-receipt-meta">
        <strong>{routeLabel(receipt.selected_mode)}</strong>
        <span>{receipt.selection_source === "admission" ? "接受服务端推荐" : "本次覆盖服务端推荐"}</span>
        <span>仅本次运行</span>
      </div>
      <details>
        <summary>查看记录版本与选择历史</summary>
        <p>工作项 v{receipt.from_item_version} → v{receipt.to_item_version}；驾驶舱 v{receipt.from_cockpit_version} → v{receipt.to_cockpit_version}。本轮服务端共保留 {historyCount} 次选择记录；规则预测仍不是实际运行结果。</p>
      </details>
    </section>
  );
}

function DecisionStatus({ item, selectedMode }: { item: Demo2WorkItem; selectedMode: Demo2RouteMode }) {
  const recordedMode = item.admission_status === "route_selected" ? item.selected_mode : null;
  if (!recordedMode) {
    return (
      <p className="work-cockpit-not-started" role="status">
        <IconShieldCheck aria-hidden="true" />
        确认后只记录执行方式，任务尚未启动。
      </p>
    );
  }

  if (recordedMode !== selectedMode) {
    return (
      <p className="work-cockpit-not-started" role="status">
        <IconArrowRight aria-hidden="true" />
        服务端当前为“{routeLabel(recordedMode)}”；改为“{routeLabel(selectedMode)}”尚未提交。
      </p>
    );
  }

  return (
    <p className="work-cockpit-recorded" role="status">
      <IconCheck aria-hidden="true" />
      已记录为“{routeLabel(selectedMode)}” · 尚未启动本次任务
    </p>
  );
}

export function WorkCockpitDecisionPane({
  item,
  saving,
  error,
  draftMode,
  onDraftMode,
  onConfirm,
  onRefresh,
  onStartExecution,
}: WorkCockpitDecisionPaneProps) {
  if (!item) {
    return (
      <section className="work-cockpit-decision-pane is-empty" aria-live="polite">
        <IconSparkles aria-hidden="true" />
        <h2>选择一项工作</h2>
        <p>选择左侧工作项后，这里会解释推荐的执行方式和可调整的范围。</p>
      </section>
    );
  }

  const selectedMode = draftMode ?? item.selected_mode ?? item.recommendation.mode;
  const selectedOption = routeOption(item, selectedMode);
  const selectedDisabled = !selectedOption || !selectedOption.available;
  const executionPending = item.execution_status === "not_started";
  const fixedByAdmission = item.admission_status === "route_selected" && item.allowed_modes.length === 1;
  const alreadyRecorded = item.admission_status === "route_selected" && item.selected_mode === selectedMode;
  const visibleReceipt = alreadyRecorded ? item.selection_receipt : null;
  const previewingOverride = item.selected_mode !== null && item.selected_mode !== selectedMode;
  const canStartSwarm = selectedMode === "adaptive_swarm"
    && item.admission_status === "route_selected"
    && item.selected_mode === "adaptive_swarm"
    && item.execution_status === "not_started"
    && Boolean(onStartExecution);
  const execution = item.execution;

  return (
    <section className="work-cockpit-decision-pane" aria-labelledby="work-cockpit-decision-title">
      <div className="work-cockpit-decision-scroll">
        <header className="work-cockpit-decision-header">
        <div>
          <span className="work-cockpit-eyebrow">执行方式建议</span>
          <h2 id="work-cockpit-decision-title">怎么完成这项工作</h2>
          <p>{item.objective}</p>
        </div>
        <span className="work-cockpit-status">{previewingOverride ? "新选择尚未提交" : statusLabel(item)}</span>
        </header>

        <section className="work-cockpit-recommendation" aria-labelledby="work-cockpit-recommendation-title">
        <div className="work-cockpit-recommendation-heading">
          <div className="work-cockpit-recommendation-icon" aria-hidden="true"><IconSparkles /></div>
          <div>
            <span>服务端推荐</span>
            <h3 id="work-cockpit-recommendation-title">{routeLabel(item.recommendation.mode)}</h3>
          </div>
        </div>
        <p className="work-cockpit-recommendation-copy">建议依据来自当前资料范围、业务价值、风险和时限。</p>
        <ul className="work-cockpit-reason-list" aria-label="推荐理由">
          {item.recommendation.reasons.map((reason) => <li key={`${reason.factor}-${reason.label}`}><IconCheck aria-hidden="true" /><span><strong>{reason.label}</strong> · {reason.detail}</span></li>)}
        </ul>
        </section>

        {!fixedByAdmission && (
          <footer className="work-cockpit-confirm-bar is-inline">
            <span>规则路由，不调用大模型。这里只记录“{routeLabel(selectedMode)}”作为本轮组织方式，不会启动协作或触发外部动作。</span>
            <button type="button" aria-describedby={!visibleReceipt ? "work-cockpit-impact-canvas-title" : undefined} disabled={saving || selectedDisabled || alreadyRecorded || !selectedOption?.impact_preview} onClick={onConfirm}>
              {saving ? "正在记录" : alreadyRecorded ? "本次方式已记录" : previewingOverride ? `记录为${routeLabel(selectedMode)}` : "记录本轮方式"}<IconArrowRight aria-hidden="true" />
            </button>
          </footer>
        )}

        {visibleReceipt && <RouteSelectionReceiptView receipt={visibleReceipt} historyCount={item.selection_receipts?.length ?? 1} />}

        <fieldset className="work-cockpit-route-options">
        <legend>执行方式</legend>
        <p className="work-cockpit-field-help">{fixedByAdmission
          ? "这项工作已按规则选择最轻量的方式，本轮不需要你再次确认。"
          : "你可以在服务端允许的范围内改写本次方式。改写不会改变任务内容。"}</p>
        <div className="work-cockpit-route-list">
          {routeOptions(item).map((option) => {
            const RouteIcon = ROUTE_ICONS[option.mode];
            const isSelected = selectedMode === option.mode;
            const isCandidate = option.candidate_only || option.mode === "adaptive_swarm";
            return (
              <label className={`work-cockpit-route-option${isSelected ? " is-selected" : ""}${option.recommended ? " is-recommended" : ""}${!option.available ? " is-disabled" : ""}`} key={option.mode}>
                <input
                  type="radio"
                  name="demo2-route-mode"
                  value={option.mode}
                  checked={isSelected}
                  disabled={!option.available || saving || fixedByAdmission}
                  onChange={() => onDraftMode(option.mode)}
                />
                <span className="work-cockpit-route-icon" aria-hidden="true"><RouteIcon /></span>
                <span className="work-cockpit-route-copy">
                  <strong>{routeLabel(option.mode)}</strong>
                  <small>{option.summary}</small>
                  {option.tradeoff && <em>{option.tradeoff}</em>}
                </span>
                <span className="work-cockpit-route-badges">
                  {option.recommended && <b>推荐</b>}
                  {isCandidate && <b className="is-candidate">候选方式</b>}
                  {!option.available && <b className="is-unavailable">暂不可选</b>}
                </span>
              </label>
            );
          })}
        </div>
        </fieldset>

        {!selectedOption?.impact_preview && (
          <section className="work-cockpit-impact-unavailable" role="status">
            <IconAlertTriangle aria-hidden="true" />
            <div><strong>影响预演暂不可用</strong><span>服务端没有返回这项执行方式的影响事实，当前不能确认。</span></div>
          </section>
        )}
        {!visibleReceipt && <DecisionStatus item={item} selectedMode={selectedMode} />}
        {canStartSwarm && (
          <section className="demo2-start-execution" aria-labelledby="demo2-start-execution-title">
            <div>
              <span>已选择 · 自适应协作群组</span>
              <strong id="demo2-start-execution-title">准备好让本次协作发生了吗？</strong>
              <p>点击后会创建受控业务工作包，并通过服务端事件展示进展。不会发送邮件、写入 CRM 或调用外部系统。</p>
            </div>
            <button type="button" onClick={() => onStartExecution?.(item.work_item_id)} disabled={saving}>
              {saving ? "正在启动" : "启动本次协作"}<IconArrowRight aria-hidden="true" />
            </button>
          </section>
        )}
        {selectedMode === "adaptive_swarm" && executionPending && !canStartSwarm && !execution && (
          <p className="work-cockpit-boundary"><IconUsersGroup aria-hidden="true" />选择 Adaptive Swarm 后，需要明确点击“启动本次协作”；系统不会自动创建工作单元。</p>
        )}
        {execution && execution.status !== "not_started" && <p className="work-cockpit-recorded"><IconCheck aria-hidden="true" />本次协作状态：{EXECUTION_STATUS_LABELS[execution.status]} · 进展来自服务端事件</p>}
        {error && (
          <div className="work-cockpit-error" role="alert">
            <IconAlertTriangle aria-hidden="true" />
            <div><strong>{execution ? "协作进展需要重新连接" : "执行方式尚未确认"}</strong><span>{error}</span></div>
            <button type="button" onClick={onRefresh} disabled={saving}><IconRefresh aria-hidden="true" />重新读取</button>
          </div>
        )}
      </div>
    </section>
  );
}

function QueueItem({ item, selected, onSelect }: { item: Demo2WorkItem; selected: boolean; onSelect: () => void }) {
  return (
    <li>
      <button type="button" className={`work-cockpit-queue-item${selected ? " is-selected" : ""}`} aria-pressed={selected} onClick={onSelect}>
        <span className="work-cockpit-queue-status" aria-hidden="true" />
        <span className="work-cockpit-queue-copy">
          <strong>{item.title}</strong>
          <small>{statusLabel(item)}</small>
          <span>{item.objective}</span>
        </span>
        <IconArrowRight aria-hidden="true" />
      </button>
    </li>
  );
}

const BAND_LABELS = {
  low: "低",
  medium: "中",
  high: "高",
  tight: "紧",
  approved: "已预留",
  ample: "充足",
} as const;

function WorkItemOverview({ item, previewMode }: { item: Demo2WorkItem; previewMode: Demo2RouteMode | null }) {
  const activeMode = item.selected_mode ?? item.recommendation.mode;
  const impactMode = previewMode && item.allowed_modes.includes(previewMode) ? previewMode : activeMode;
  const impactOption = routeOption(item, impactMode);
  const isServerSelected = item.admission_status === "route_selected" && item.selected_mode === impactMode;
  const previewingOverride = item.selected_mode !== null && item.selected_mode !== impactMode;
  const visibleReceipt = isServerSelected && item.selection_receipt?.selected_mode === impactMode
    ? item.selection_receipt
    : null;
  return (
    <article className="work-cockpit-overview" aria-labelledby="work-cockpit-overview-title">
      <header>
        <div>
          <span className="work-cockpit-eyebrow">当前工作</span>
          <h2 id="work-cockpit-overview-title">{item.title}</h2>
          <p>{item.objective}</p>
        </div>
        <span className="work-cockpit-status">{previewingOverride ? "新选择尚未提交" : statusLabel(item)}</span>
      </header>

      <section className="work-cockpit-source-summary" aria-labelledby="work-cockpit-source-title">
        <div>
          <span>资料范围</span>
          <strong id="work-cockpit-source-title">{item.facts.source_labels.length} 类演示数据</strong>
        </div>
        <ul>
          {item.facts.source_labels.map((source) => <li key={source}>演示数据 · {source}</li>)}
        </ul>
      </section>

      <Demo2AgentCallTrace item={item} />

      {item.execution && item.execution.status !== "not_started" && (
        <Demo2ExecutionBoard execution={item.execution} />
      )}

      {!item.execution && impactOption && (
        <RouteImpactCanvas
          option={impactOption}
          receipt={visibleReceipt}
          isServerSelected={isServerSelected}
          previewingOverride={previewingOverride}
        />
      )}

      <details className="work-cockpit-supporting-details">
        <summary><span>推荐依据与方式比较</span><strong>需要更多细节时展开</strong></summary>
        <section className="work-cockpit-admission-facts" aria-labelledby="work-cockpit-admission-facts-title">
          <div className="work-cockpit-section-heading">
            <span>为什么这样建议</span>
            <strong id="work-cockpit-admission-facts-title">当前工作条件</strong>
          </div>
          <dl>
            <div><dt>业务价值</dt><dd>{BAND_LABELS[item.facts.value_band]}</dd></div>
            <div><dt>资料广度</dt><dd>{item.facts.breadth} 类</dd></div>
            <div><dt>可并行工作包</dt><dd>{item.facts.parallelism} 个</dd></div>
            <div><dt>截止压力</dt><dd>{BAND_LABELS[item.facts.deadline_pressure]}</dd></div>
            <div><dt>业务风险</dt><dd>{BAND_LABELS[item.facts.risk_band]}</dd></div>
            <div><dt>资源边界</dt><dd>{BAND_LABELS[item.facts.budget_band]}</dd></div>
          </dl>
        </section>

        <section className="work-cockpit-route-overview" aria-labelledby="work-cockpit-route-overview-title">
          <div className="work-cockpit-section-heading">
            <span>执行方式比较</span>
            <strong id="work-cockpit-route-overview-title">推荐与可选代价</strong>
          </div>
          <div className="work-cockpit-route-overview-list">
            {item.route_profiles.map((profile) => {
              const recommended = profile.mode === item.recommendation.mode;
              const selected = profile.mode === item.selected_mode;
              const RouteIcon = ROUTE_ICONS[profile.mode];
              return (
                <article className={`${recommended ? "is-recommended" : ""}${selected ? " is-selected" : ""}`} key={profile.mode}>
                  <div className="work-cockpit-route-overview-heading">
                    <span><RouteIcon aria-hidden="true" /></span>
                    <div><strong>{routeLabel(profile.mode)}</strong><small>{profile.summary}</small></div>
                    <div className="work-cockpit-route-badges">{recommended && <b>推荐</b>}{selected && <b className="is-selected">本次已选</b>}</div>
                  </div>
                  <dl>
                    <div><dt>预计</dt><dd>{formatRuntime(profile.forecast.estimated_runtime_seconds)}</dd></div>
                    <div><dt>工具上限</dt><dd>{profile.forecast.estimated_tool_calls} 次</dd></div>
                    <div><dt>并行单元</dt><dd>{profile.forecast.max_workers} 个</dd></div>
                  </dl>
                  <p>{profile.tradeoff}</p>
                </article>
              );
            })}
          </div>
        </section>
      </details>

      <footer className="work-cockpit-overview-status">
        <IconShieldCheck aria-hidden="true" />
        <div>
          <strong>{previewingOverride
            ? `服务端仍为${routeLabel(activeMode)}；${routeLabel(impactMode)}尚未提交`
            : item.admission_status === "route_selected"
              ? `已确定为${routeLabel(activeMode)}`
              : `建议使用${routeLabel(activeMode)}`}</strong>
          <span>当前执行状态：尚未启动。实际协作和外部动作都没有被创建。</span>
        </div>
      </footer>
    </article>
  );
}

function resolveSelectedItem(snapshot: Demo2CockpitSnapshot, selectedId: string | null) {
  if (selectedId) return snapshot.items.find((item) => item.work_item_id === selectedId) ?? null;
  return snapshot.items[0] ?? null;
}

export function WorkCockpit({
  snapshot,
  loading,
  saving,
  selectedId,
  draftMode,
  onSelect,
  onRefresh,
}: WorkCockpitProps) {
  if (loading && !snapshot) {
    return (
      <section className="work-cockpit work-cockpit-loading" aria-live="polite">
        <IconRefresh aria-hidden="true" />
        <span>正在读取工作项</span>
        <h1>智能工作驾驶舱</h1>
        <p>正在确认哪些工作需要你决定执行方式。</p>
      </section>
    );
  }

  if (!snapshot || snapshot.items.length === 0) {
    return (
      <section className="work-cockpit work-cockpit-empty" aria-live="polite">
        <IconSparkles aria-hidden="true" />
        <h1>智能工作驾驶舱</h1>
        <p>当前没有可供路由的工作项。重新读取服务端状态后再试。</p>
        <button type="button" onClick={onRefresh} disabled={loading}><IconRefresh aria-hidden="true" />重新读取</button>
      </section>
    );
  }

  const selectedItem = resolveSelectedItem(snapshot, selectedId);
  const decisionsNeeded = snapshot.items.filter((item) => item.admission_status === "recommended").length;
  return (
    <section className="work-cockpit" aria-labelledby="work-cockpit-title">
      <header className="work-cockpit-page-header">
        <div>
          <span className="work-cockpit-eyebrow">今日工作队列</span>
          <h2 id="work-cockpit-title">{snapshot.items.length} 项工作，{decisionsNeeded} 项需要你确定执行方式</h2>
          <p>其他工作已按规则选择更轻量的方式；复杂工作在确认前不会启动。</p>
        </div>
        <button type="button" className="work-cockpit-refresh" onClick={onRefresh} disabled={loading || saving} title="重新读取服务端状态" aria-label="重新读取服务端状态"><IconRefresh aria-hidden="true" /></button>
      </header>
      <div className="work-cockpit-layout">
        <aside className="work-cockpit-queue" aria-labelledby="work-cockpit-queue-title">
          <div className="work-cockpit-section-heading"><span>待处理工作</span><strong id="work-cockpit-queue-title">需要确定执行方式</strong></div>
          <ul>
            {snapshot.items.map((item) => <QueueItem key={item.work_item_id} item={item} selected={item.work_item_id === selectedItem?.work_item_id} onSelect={() => onSelect(item.work_item_id)} />)}
          </ul>
        </aside>
        <main className="work-cockpit-main">
          {selectedItem && <WorkItemOverview item={selectedItem} previewMode={draftMode} />}
        </main>
      </div>
    </section>
  );
}
