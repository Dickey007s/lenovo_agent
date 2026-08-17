import {
  IconAlertTriangle,
  IconArrowRight,
  IconBolt,
  IconCheck,
  IconClock,
  IconRefresh,
  IconRobot,
  IconShieldCheck,
  IconSparkles,
  IconTool,
  IconUsersGroup,
} from "@tabler/icons-react";

import type {
  Demo2CockpitSnapshot,
  Demo2RouteMode,
  Demo2RouteProfile,
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
  return item.admission_status === "route_selected"
    ? "执行方式已记录"
    : BUSINESS_STATUS_LABELS[item.business_status];
}

function optionFacts(option: Demo2RouteProfile) {
  return (
    <dl className="work-cockpit-option-facts">
      <div>
        <dt><IconClock aria-hidden="true" />预计耗时</dt>
        <dd>{formatRuntime(option.forecast.estimated_runtime_seconds)}<small>规则预测</small></dd>
      </div>
      <div>
        <dt><IconTool aria-hidden="true" />工具调用上限</dt>
        <dd>{option.forecast.estimated_tool_calls} 次工具调用<small>规则预测</small></dd>
      </div>
      <div>
        <dt><IconUsersGroup aria-hidden="true" />并行程度</dt>
        <dd>最多 {option.forecast.max_workers} 个并行单元</dd>
      </div>
      <div>
        <dt><IconShieldCheck aria-hidden="true" />人工确认</dt>
        <dd>{option.mode === "adaptive_swarm" ? "关键节点确认" : "结果确认"}</dd>
      </div>
    </dl>
  );
}

function DecisionStatus({ item, selectedMode }: { item: Demo2WorkItem; selectedMode: Demo2RouteMode }) {
  const recorded = item.admission_status === "route_selected" && item.selected_mode !== null;
  if (!recorded) {
    return (
      <p className="work-cockpit-not-started" role="status">
        <IconShieldCheck aria-hidden="true" />
        确认后只记录执行方式，任务尚未启动。
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
  const recommendedOption = routeOption(item, item.recommendation.mode);
  const selectedIsRecommended = selectedMode === item.recommendation.mode;
  const selectedDisabled = !selectedOption || !selectedOption.available;
  const executionPending = item.execution_status === "not_started";
  const fixedByAdmission = item.admission_status === "route_selected" && item.allowed_modes.length === 1;

  return (
    <section className="work-cockpit-decision-pane" aria-labelledby="work-cockpit-decision-title">
      <header className="work-cockpit-decision-header">
        <div>
          <span className="work-cockpit-eyebrow">执行方式建议</span>
          <h2 id="work-cockpit-decision-title">怎么完成这项工作</h2>
          <p>{item.objective}</p>
        </div>
        <span className="work-cockpit-status">{statusLabel(item)}</span>
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
        {recommendedOption && optionFacts(recommendedOption)}
      </section>

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

      {selectedOption && !selectedIsRecommended && (
        <section className="work-cockpit-tradeoff" aria-label="改写代价">
          <strong>本次改为“{routeLabel(selectedMode)}”的影响</strong>
          <p>{selectedOption.tradeoff || "服务端未提供改写代价，当前不能确认该方式。"}</p>
        </section>
      )}

      {selectedOption && !selectedIsRecommended && optionFacts(selectedOption)}
      <DecisionStatus item={item} selectedMode={selectedMode} />
      {selectedMode === "adaptive_swarm" && executionPending && (
        <p className="work-cockpit-boundary"><IconUsersGroup aria-hidden="true" />当前仅记录为候选执行方式，不会自动创建或启动实际协作。</p>
      )}
      {error && (
        <div className="work-cockpit-error" role="alert">
          <IconAlertTriangle aria-hidden="true" />
          <div><strong>执行方式尚未确认</strong><span>{error}</span></div>
          <button type="button" onClick={onRefresh} disabled={saving}><IconRefresh aria-hidden="true" />重新读取</button>
        </div>
      )}
      {!fixedByAdmission && (
        <footer className="work-cockpit-confirm-bar">
          <span>确认只会记录路由选择，不会发送邮件、写入 CRM 或启动外部动作。</span>
          <button type="button" disabled={saving || selectedDisabled} onClick={onConfirm}>
            {saving ? "正在确认" : "确认执行方式"}<IconArrowRight aria-hidden="true" />
          </button>
        </footer>
      )}
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

function WorkItemOverview({ item }: { item: Demo2WorkItem }) {
  const activeMode = item.selected_mode ?? item.recommendation.mode;
  return (
    <article className="work-cockpit-overview" aria-labelledby="work-cockpit-overview-title">
      <header>
        <div>
          <span className="work-cockpit-eyebrow">当前工作</span>
          <h2 id="work-cockpit-overview-title">{item.title}</h2>
          <p>{item.objective}</p>
        </div>
        <span className="work-cockpit-status">{statusLabel(item)}</span>
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

      <footer className="work-cockpit-overview-status">
        <IconShieldCheck aria-hidden="true" />
        <div>
          <strong>{item.admission_status === "route_selected" ? `已确定为${routeLabel(activeMode)}` : `建议使用${routeLabel(activeMode)}`}</strong>
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
          {selectedItem && <WorkItemOverview item={selectedItem} />}
        </main>
      </div>
    </section>
  );
}
