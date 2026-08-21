"use client";

import { IconAlertTriangle, IconArrowRight, IconCheck, IconCircleCheck, IconX } from "@tabler/icons-react";

import { AgentCallTrace, type AgentCallStep } from "./agent-call-trace";

export type ActionImpactKind = "will_change" | "will_recheck" | "unchanged" | "no_external_action";

export type ActionImpactItem = {
  item_id: string;
  change_kind: ActionImpactKind;
  label: string;
  before?: string | number | null;
  after?: string | number | null;
};

export type ActionImpactPayload = {
  preview_id?: string;
  receipt_id?: string;
  action_id?: string;
  action_hash?: string;
  policy_version?: string;
  items?: ActionImpactItem[];
  external_side_effect?: "none" | "simulator_only" | "external" | "unknown";
  status?: string;
  observed_at?: string;
  event_sequence?: number;
  simulator?: string;
  generated_at?: string;
  error_code?: string;
  failure_stage?: string;
  retryable?: boolean;
};

export type ActionImpactRun = {
  status: string;
  action: {
    action_id: string;
    capability: string;
    action_type: string;
    target_scope: string;
    recipients: string[];
    resources: string[];
    task_artifact_binding?: { artifact_version: number; task_version: number } | null;
  };
  control_plan: {
    action_hash: string;
    status: string;
    missing_requirements: string[];
    required_approvals: string[];
    reason_codes: string[];
  };
  evidence?: Record<string, { status: string }>;
  approvals?: { approver_role: string; decision: "approved" | "rejected" }[];
  impact_preview?: ActionImpactPayload | null;
  execution_receipt?: ActionImpactPayload | null;
  permit?: { permit_id: string; expires_at: string } | null;
  tool_result?: { status: string; simulator: string; output: Record<string, unknown> } | null;
};

type EvidenceDefinition = { label: string; input_type: string; options: { value: string; label: string }[]; user_action?: string };
type LedgerProps = {
  run: ActionImpactRun;
  evidenceCatalog: Record<string, EvidenceDefinition>;
  evidence: Record<string, string>;
  busy: boolean;
  onEvidence: (key: string, value: string) => void;
  onSubmitEvidence: () => void;
  onDecide: (role: string, decision: "approved" | "rejected") => void;
  onAuthorize: () => void;
  roleLabels: Record<string, string>;
  capabilityLabels: Record<string, string>;
  targetScopeLabels: Record<string, string>;
  riskLabel?: string;
  onDismissReceipt?: () => void;
};

export function deriveGovernedToolState(
  run: Pick<ActionImpactRun, "status" | "tool_result" | "execution_receipt">,
) {
  const receiptStatus = run.execution_receipt?.status;
  const attempted = Boolean(run.tool_result)
    || run.execution_receipt?.failure_stage === "simulator"
    || receiptStatus === "unknown"
    || receiptStatus === "succeeded";
  const outcomeUnknown = attempted && (receiptStatus === "unknown" || (run.status === "FAILED" && !run.tool_result));
  const terminalWithoutTool = ["DENIED", "FAILED"].includes(run.status) && !attempted;
  const status: AgentCallStep["status"] = outcomeUnknown
    ? "unknown"
    : run.tool_result
      ? "complete"
      : terminalWithoutTool
        ? "blocked"
        : "not_called";
  return { attempted, outcomeUnknown, terminalWithoutTool, status };
}

const GROUPS: { kind: ActionImpactKind; label: string; className: string }[] = [
  { kind: "will_change", label: "会改变", className: "is-change" },
  { kind: "will_recheck", label: "会重新核对", className: "is-recheck" },
  { kind: "unchanged", label: "会保持", className: "is-preserve" },
  { kind: "no_external_action", label: "不会发生", className: "is-no-action" },
];

function listFor(payload: ActionImpactPayload | null | undefined, kind: ActionImpactKind): ActionImpactItem[] | undefined {
  if (!payload || !Array.isArray(payload.items)) return undefined;
  return payload.items.filter(item => item.change_kind === kind);
}

function groupsFor(payload: ActionImpactPayload | null | undefined) {
  return GROUPS.reduce<Record<ActionImpactKind, ActionImpactItem[] | undefined>>((groups, group) => {
    groups[group.kind] = listFor(payload, group.kind);
    return groups;
  }, { will_change: undefined, will_recheck: undefined, unchanged: undefined, no_external_action: undefined });
}

function isComplete(
  payload: ActionImpactPayload | null | undefined,
  groups: Record<ActionImpactKind, ActionImpactItem[] | undefined>,
  run: ActionImpactRun,
) {
  if (!payload || payload.action_id !== run.action.action_id || payload.action_hash !== run.control_plan.action_hash) return false;
  const items = GROUPS.flatMap(group => groups[group.kind] ?? []);
  const ids = new Set(items.map(item => item.item_id));
  return items.length === GROUPS.length
    && GROUPS.every(group => groups[group.kind]?.length === 1)
    && ids.size === items.length;
}

function textFor(item: ActionImpactItem) {
  return item.label;
}

function ImpactRows({ payload, receiptStatus }: { payload: ActionImpactPayload | null | undefined; receiptStatus?: string }) {
  const groups = groupsFor(payload);
  const receiptTone = receiptStatus === "succeeded" ? "is-success" : receiptStatus === "denied" ? "is-denied" : receiptStatus ? "is-uncertain" : "";
  return <div className={`action-impact-groups ${receiptStatus ? `is-receipt ${receiptTone}` : ""}`}>
    {GROUPS.map(group => {
      const items = groups[group.kind];
      return <section className={`action-impact-group ${group.className}`} key={group.kind}>
        <header><span>{group.label}</span><small>{items === undefined ? "待服务端提供" : `${items.length} 项`}</small></header>
        {items === undefined ? <p className="action-impact-unavailable">服务端未提供这类影响，暂不作判断。</p> : items.length === 0 ? <p className="action-impact-unavailable">服务端未提供这类影响，暂不作判断。</p> : <ul>{items.map(item => <li key={item.item_id}>
          <span className="action-impact-item-mark">{receiptStatus === "succeeded" ? <IconCheck aria-hidden="true"/> : receiptStatus === "denied" ? <IconX aria-hidden="true"/> : receiptStatus ? <IconAlertTriangle aria-hidden="true"/> : <IconArrowRight aria-hidden="true"/>}</span>
          <div><strong>{textFor(item)}</strong>{item.before != null || item.after != null ? <small className="action-impact-transition">{String(item.before ?? "当前")} <IconArrowRight aria-hidden="true"/> {String(item.after ?? "执行后")}</small> : null}</div>
        </li>)}</ul>}
      </section>;
    })}
  </div>;
}

export function ActionGovernanceTrace({ run, defaultOpen = false }: { run: ActionImpactRun; defaultOpen?: boolean }) {
  const denied = run.status === "DENIED";
  const failed = run.status === "FAILED";
  const {
    attempted: simulatorAttempted,
    outcomeUnknown: simulatorOutcomeUnknown,
    terminalWithoutTool,
    status: toolStatus,
  } = deriveGovernedToolState(run);
  const requiredEvidence = Object.values(run.evidence ?? {});
  const satisfiedEvidence = requiredEvidence.filter((item) => item.status === "satisfied").length;
  const approvedRoles = new Set((run.approvals ?? []).filter((item) => item.decision === "approved").map((item) => item.approver_role));
  const approvalRequired = run.control_plan.required_approvals.length > 0;
  const approvalsComplete = approvalRequired && run.control_plan.required_approvals.every((role) => approvedRoles.has(role));
  const evidenceStatus: AgentCallStep["status"] = run.control_plan.status === "WAITING_EVIDENCE"
    ? "waiting"
    : terminalWithoutTool && run.control_plan.missing_requirements.length > 0
      ? "blocked"
      : "complete";
  const approvalStatus: AgentCallStep["status"] = !approvalRequired
    ? "not_called"
    : approvalsComplete
    ? "complete"
    : run.control_plan.status === "WAITING_APPROVAL"
      ? "waiting"
      : terminalWithoutTool
        ? "blocked"
        : "not_called";
  const permitStatus: AgentCallStep["status"] = run.permit
    ? "complete"
    : run.control_plan.status === "READY_TO_AUTHORIZE"
      ? "waiting"
      : terminalWithoutTool
        ? "blocked"
        : "not_called";
  const simulator = run.tool_result?.simulator === "email_simulator" ? "邮件演示工具" : run.tool_result ? "办公演示工具" : "受控演示工具";
  const controlPlanStatusLabel = ({
    WAITING_EVIDENCE: "等待可信依据",
    WAITING_APPROVAL: "等待人工确认",
    READY_TO_AUTHORIZE: "等待签发执行许可",
    AUTHORIZED: "执行许可已签发",
    DENIED: "已停止",
  } as Record<string, string>)[run.control_plan.status] ?? "治理状态已更新";
  const steps: AgentCallStep[] = [
    {
      id: "action",
      label: "建立动作候选",
      component: "动作准备器",
      kind: "runtime",
      status: "complete",
      detail: "服务端已把当前意图规范化为受控动作；候选本身没有执行权限。",
      meta: "Action Runtime · 动作内容、目标与成果版本在后续每一关都会重新核对",
    },
    {
      id: "risk-policy",
      label: "判断风险与策略",
      component: "风险与权限规则",
      kind: "rule",
      status: denied ? "blocked" : "complete",
      detail: denied
        ? "确定性规则已停止该动作，治理链不会继续执行。"
        : `确定性规则已生成风险等级和控制计划，当前为“${controlPlanStatusLabel}”。`,
      meta: "Risk Engine + Policy Engine · 风险、权限和审批要求不由大模型决定",
    },
    {
      id: "evidence",
      label: "核对可信依据",
      component: "可信依据核对",
      kind: "rule",
      status: evidenceStatus,
      detail: run.control_plan.missing_requirements.length > 0
        ? `仍缺 ${run.control_plan.missing_requirements.length} 项服务端要求的依据，不能越过。`
        : requiredEvidence.length > 0
          ? `${satisfiedEvidence} / ${requiredEvidence.length} 项依据已由服务端核对。`
          : "当前动作没有额外待补依据，服务端仍保留策略核对结果。",
      meta: "Evidence Resolver · 只接受服务端可核验依据",
    },
    {
      id: "human",
      label: "记录人工决定",
      component: "人工确认",
      kind: "human",
      status: approvalStatus,
      detail: run.control_plan.required_approvals.length === 0
        ? "当前控制计划不要求人工批准。"
        : approvalsComplete
          ? "所需人工批准已被服务端记录；批准本身仍不等于执行。"
          : `等待 ${run.control_plan.required_approvals.length} 个角色完成本次确认。`,
      meta: "Human Gate · 人工确认不会自动变成执行回执",
    },
    {
      id: "permit",
      label: "签发一次性执行许可",
      component: "执行许可服务",
      kind: "permit",
      status: permitStatus,
      detail: run.permit
        ? "服务端已为当前动作哈希、目标和参数签发一次性许可。"
        : run.control_plan.status === "READY_TO_AUTHORIZE"
          ? "全部门槛已满足，仍需用户明确点击执行后才会签发。"
          : "在证据与人工确认完成前，不会签发执行许可。",
      meta: "Permit Service · 许可内容、标识和签名默认隐藏",
    },
    {
      id: "tool",
      label: "调用受控演示工具",
      component: "受控演示工具",
      kind: "tool",
      status: toolStatus,
      detail: simulatorOutcomeUnknown
        ? `${simulator}已经进入调用，但服务端无法确认最终结果；必须按未知结果处理并人工核对。`
        : run.tool_result
        ? `执行网关已校验许可并调用${simulator}，服务端已返回“${run.tool_result.status === "succeeded" ? "模拟成功" : "结果未完成"}”。`
        : terminalWithoutTool
          ? "治理链已停止，执行网关和演示工具没有被调用。"
          : "尚未调用；人工批准或执行许可都不能替代真实执行回执。",
      meta: simulatorAttempted
        ? "Tool Gateway → Simulator · 当前只连接演示工具，不代表真实邮件或外部系统已写入"
        : "Tool Gateway → Simulator · 尚未进入",
      statusLabel: simulatorOutcomeUnknown ? "结果待核对" : run.tool_result ? "工具已调用" : undefined,
    },
  ];

  return <AgentCallTrace
    demo="Demo 3"
    summary="动作按风险规则、证据、人工确认、一次性许可和受控工具逐关推进；每一关都能明确看到已运行、未调用或结果待核对。"
    metrics={[
      { label: "治理规则已调用", tone: "rule" },
      { label: !approvalRequired ? "无需人工确认" : approvalsComplete ? "人工确认已记录" : "人工确认待定", tone: approvalsComplete ? "safe" : approvalRequired ? "warning" : "neutral" },
      { label: run.permit ? "执行许可已签发" : "执行许可未签发", tone: run.permit ? "safe" : "neutral" },
      { label: simulatorOutcomeUnknown ? "工具结果待核对" : simulatorAttempted ? "演示工具已调用" : "演示工具未调用", tone: simulatorOutcomeUnknown ? "warning" : simulatorAttempted ? "safe" : "neutral" },
    ]}
    steps={steps}
    boundary="这里只展示服务端动作记录与治理事实。执行许可内容、动作原始参数、Prompt、思维链和审计 payload 默认隐藏。"
    defaultOpen={defaultOpen}
  />;
}

export function ActionImpactLedger({ run, evidenceCatalog, evidence, busy, onEvidence, onSubmitEvidence, onDecide, onAuthorize, roleLabels, capabilityLabels, targetScopeLabels, riskLabel, onDismissReceipt }: LedgerProps) {
  const terminal = ["EXECUTED", "DENIED", "FAILED"].includes(run.status);
  const previewGroups = groupsFor(run.impact_preview);
  const previewComplete = isComplete(run.impact_preview, previewGroups, run);
  const receiptGroups = groupsFor(run.execution_receipt);
  const receiptComplete = isComplete(run.execution_receipt, receiptGroups, run);
  const receiptSucceeded = run.status === "EXECUTED" && run.execution_receipt?.status === "succeeded" && receiptComplete;
  const receiptDenied = run.status === "DENIED" || run.execution_receipt?.status === "denied";
  const receiptUnknown = run.execution_receipt?.status === "unknown" || run.execution_receipt?.failure_stage === "simulator";
  const status = run.control_plan.status;
  const binding = run.action.task_artifact_binding;
  const title = capabilityLabels[run.action.capability] ?? "受控办公动作";
  const target = run.action.recipients.join(", ") || run.action.resources.join(", ") || "当前工作区";
  const simulatorLabel = run.tool_result?.simulator === "email_simulator" ? "演示邮件工具" : run.tool_result ? "演示办公工具" : null;

  return <div className={`approval-overlay action-impact-overlay ${terminal ? "is-terminal" : ""}`}>
    <section className={`approval-modal action-impact-ledger ${terminal ? "is-terminal" : ""} ${run.status === "DENIED" || run.status === "FAILED" ? "is-failed" : ""}`} role="dialog" aria-modal="false" aria-label="动作影响账本">
      <header className="action-impact-header"><div><span>动作影响账本</span><h2>{title}</h2></div><div className="action-impact-stage"><b className={terminal ? receiptSucceeded ? "is-done" : "is-failed" : previewComplete ? "is-ready" : "is-blocked"}>{terminal ? receiptSucceeded ? "实际回执" : receiptUnknown ? "结果待核对" : "未执行" : previewComplete ? "预演已生成" : "影响待核对"}</b>{terminal && onDismissReceipt && <button type="button" className="action-impact-dismiss" aria-label="收起动作回执" title="收起动作回执" onClick={onDismissReceipt}><IconX aria-hidden="true"/></button>}</div></header>
      <div className="action-impact-steps" aria-label="动作阶段"><span className={!terminal ? "is-current" : "is-done"}><i>1</i>预演</span><span className={status === "WAITING_APPROVAL" || status === "READY_TO_AUTHORIZE" ? "is-current" : terminal ? "is-done" : ""}><i>2</i>你的确认</span><span className={terminal ? "is-current" : ""}><i>3</i>实际回执</span></div>
      <ActionGovernanceTrace run={run} />
      {binding && <div className="approval-task-binding"><strong>基于已核对成果</strong><span>客户回复草稿 v{binding.artifact_version} · 本轮汇报 v{binding.task_version}</span><small>动作只绑定这一版成果；成果变化后必须重新准备。</small></div>}
      <div className="action-impact-action-facts"><span><small>动作</small><strong>{title}</strong></span><span><small>影响范围</small><strong>{targetScopeLabels[run.action.target_scope] ?? "服务端范围待确认"}</strong></span><span><small>目标</small><strong>{target}</strong></span></div>
      {!terminal && <><p className="approval-summary">批准前先看清哪些内容会改变、哪些内容会保持不变。系统不会把确认按钮当作执行回执。</p><ImpactRows payload={run.impact_preview}/>{!previewComplete && <div className="action-impact-fail-closed" role="alert"><IconAlertTriangle aria-hidden="true"/><span>服务端尚未提供完整影响预演。为避免误操作，批准和执行暂不可用。</span></div>}</>}
      {terminal && <><div className={`action-impact-receipt-heading ${receiptSucceeded ? "is-success" : "is-failed"}`}>{receiptSucceeded ? <IconCircleCheck aria-hidden="true"/> : receiptDenied ? <IconX aria-hidden="true"/> : <IconAlertTriangle aria-hidden="true"/>}<div><strong>{receiptSucceeded ? "服务端已返回实际回执" : receiptDenied && receiptComplete ? "服务端确认本次未执行" : receiptUnknown ? "受控工具已进入，结果仍待核对" : "服务端回执未完整返回"}</strong><small>{receiptSucceeded ? "以下内容只来自结构化回执，不依赖 Agent 说明。" : receiptDenied && receiptComplete ? "已完成的任务成果不会因此被撤销。" : receiptUnknown ? "不能把未知结果表述为成功或未执行；请按恢复流程核对。" : "暂不显示未被服务端确认的具体变化。"}</small></div></div><ImpactRows payload={run.execution_receipt} receiptStatus={run.execution_receipt?.status}/>{(!receiptComplete || receiptUnknown) && <div className="action-impact-fail-closed" role="alert"><IconAlertTriangle aria-hidden="true"/><span>{receiptUnknown ? "演示工具已进入，但最终结果未知；在核对回执前不得重复执行或宣称成功。" : "动作已结束，但结构化影响回执尚未完整返回；暂不显示未确认的具体变化。"}</span></div>}{run.tool_result && <details className="approval-details action-impact-tool-result"><summary>查看执行边界 <b>⌄</b></summary><p>执行工具：{simulatorLabel} · {run.tool_result.status === "succeeded" ? "已返回模拟结果" : "结果未完成"}</p><p>当前动作只代表演示环境中的受控执行，不代表真实外部系统已写入。</p></details>}</>}
      {!terminal && status === "WAITING_EVIDENCE" && <div className="approval-gate"><strong>需要补充可信依据</strong>{run.control_plan.missing_requirements.map(requirement => { const item = evidenceCatalog[requirement]; return <label key={requirement}><span>{item?.label ?? requirement}</span>{item?.input_type === "select" ? <select value={evidence[requirement] ?? ""} onChange={event => onEvidence(requirement, event.target.value)}><option value="">请选择</option>{item.options.map(option => <option value={option.value} key={option.value}>{option.label}</option>)}</select> : <small>✓ {item?.user_action ?? "系统自动校验"}</small>}</label>; })}<button className="primary-button" disabled={busy} onClick={onSubmitEvidence}>提交依据</button></div>}
      {!terminal && status === "WAITING_APPROVAL" && <div className="approval-gate"><strong>请确认这次影响</strong>{run.control_plan.required_approvals.map(role => <div className="approval-role" key={role}><span><b>{roleLabels[role] ?? "指定审批人"}</b><small>批准后仍需执行确认</small></span><div><button disabled={busy || !previewComplete} onClick={() => onDecide(role, "rejected")}><IconX aria-hidden="true"/>不执行</button><button className="primary-button" disabled={busy || !previewComplete} onClick={() => onDecide(role, "approved")}><IconCheck aria-hidden="true"/>批准这次影响</button></div></div>)}</div>}
      {!terminal && status === "READY_TO_AUTHORIZE" && <footer className="approval-final action-impact-final"><div><strong>你的批准已记录</strong><small>执行前会再次核对动作绑定和成果版本。</small></div><button className="primary-button" disabled={busy || !previewComplete} onClick={onAuthorize}>执行这次已批准的动作</button></footer>}
      {!terminal && status !== "WAITING_EVIDENCE" && status !== "WAITING_APPROVAL" && status !== "READY_TO_AUTHORIZE" && <div className="action-impact-status-note">{riskLabel ? `需要确认：${riskLabel}` : "等待服务端更新动作状态"}</div>}
    </section>
  </div>;
}
