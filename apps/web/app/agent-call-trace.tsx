"use client";

import { useState } from "react";
import {
  IconAlertTriangle,
  IconBolt,
  IconCheck,
  IconChevronRight,
  IconClock,
  IconMinus,
  IconRobot,
  IconShieldCheck,
  IconSparkles,
  IconTool,
  IconUserCheck,
} from "@tabler/icons-react";

export type DemoExperienceId = "demo1" | "demo2" | "demo3";
export type AgentCallKind = "runtime" | "model" | "rule" | "human" | "permit" | "tool";
export type AgentCallStatus = "complete" | "active" | "waiting" | "not_called" | "blocked" | "unknown";

export type AgentCallStep = {
  id: string;
  label: string;
  component: string;
  kind: AgentCallKind;
  status: AgentCallStatus;
  statusLabel?: string;
  detail: string;
  meta?: string;
};

export type AgentCallMetric = {
  label: string;
  tone?: "neutral" | "model" | "rule" | "safe" | "warning";
};

export type DemoExperienceItem = {
  id: DemoExperienceId;
  label: string;
  title: string;
  status: string;
};

const STATUS_LABELS: Record<AgentCallStatus, string> = {
  complete: "已运行",
  active: "运行中",
  waiting: "等待",
  not_called: "未调用",
  blocked: "已停止",
  unknown: "结果未知",
};

const KIND_ICONS = {
  runtime: IconBolt,
  model: IconSparkles,
  rule: IconShieldCheck,
  human: IconUserCheck,
  permit: IconCheck,
  tool: IconTool,
} as const;

export function DemoExperienceNav({
  active,
  items,
  onSelect,
}: {
  active: DemoExperienceId;
  items: DemoExperienceItem[];
  onSelect: (id: DemoExperienceId) => void;
}) {
  return (
    <nav className="demo-experience-nav" aria-label="三个演示能力">
      <div className="demo-experience-nav-heading">
        <IconRobot aria-hidden="true" />
        <span><b>Agent 能力演示</b><small>选择一个 Demo，查看它实际调用了什么</small></span>
      </div>
      <div className="demo-experience-nav-items">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            className={active === item.id ? "is-active" : ""}
            aria-current={active === item.id ? "page" : undefined}
            onClick={() => onSelect(item.id)}
          >
            <span>{item.label}</span>
            <strong>{item.title}</strong>
            <small>{item.status}</small>
            <IconChevronRight aria-hidden="true" />
          </button>
        ))}
      </div>
    </nav>
  );
}

export function AgentCallTrace({
  demo,
  summary,
  steps,
  metrics,
  boundary,
  defaultOpen = false,
}: {
  demo: string;
  summary: string;
  steps: AgentCallStep[];
  metrics: AgentCallMetric[];
  boundary: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <details className="agent-call-trace" open={open} onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>
        <span className="agent-call-trace-icon"><IconBolt aria-hidden="true" /></span>
        <span className="agent-call-trace-copy">
          <small>{demo} · 调用证据</small>
          <strong>本次用了什么</strong>
          <em>{summary}</em>
        </span>
        <span className="agent-call-trace-metrics" aria-label="调用摘要">
          {metrics.map((metric) => <b className={`is-${metric.tone ?? "neutral"}`} key={metric.label}>{metric.label}</b>)}
        </span>
        <IconChevronRight className="agent-call-trace-chevron" aria-hidden="true" />
      </summary>
      <ol>
        {steps.map((step) => {
          const StepIcon = KIND_ICONS[step.kind];
          return (
            <li className={`is-${step.status} is-${step.kind}`} key={step.id}>
              <span className="agent-call-step-icon"><StepIcon aria-hidden="true" /></span>
              <div>
                <span><strong>{step.label}</strong><b>{step.component}</b></span>
                <p>{step.detail}</p>
                {step.meta && <small>{step.meta}</small>}
              </div>
              <em>{step.status === "blocked" || step.status === "unknown" ? <IconAlertTriangle aria-hidden="true" /> : step.status === "waiting" || step.status === "active" ? <IconClock aria-hidden="true" /> : step.status === "not_called" ? <IconMinus aria-hidden="true" /> : <IconCheck aria-hidden="true" />}{step.statusLabel ?? STATUS_LABELS[step.status]}</em>
            </li>
          );
        })}
      </ol>
      <footer><IconShieldCheck aria-hidden="true" /><span>{boundary}</span></footer>
    </details>
  );
}
