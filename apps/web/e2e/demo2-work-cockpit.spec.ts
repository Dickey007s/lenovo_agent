import { expect, test, type Page, type TestInfo } from "@playwright/test";
import type {
  Demo2CockpitSnapshot,
  Demo2ExecutionSnapshot,
  Demo2RouteImpactPreview,
  Demo2RouteMode,
  Demo2RouteProfile,
  Demo2RouteSelectionReceipt,
} from "../app/demo2-types";

const forecast = (estimated_tool_calls: number, estimated_runtime_seconds: number, max_workers: number) => ({
  source_type: "fixture_policy_forecast" as const,
  estimated_tool_calls,
  estimated_runtime_seconds,
  max_workers,
});

async function attachScreenshot(page: Page, testInfo: TestInfo, name: string) {
  await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: "image/png" });
}

async function openLegacyCockpit(page: Page) {
  await page.getByRole("button", { name: "任务", exact: true }).click();
}

const impactPreview = (mode: Demo2RouteMode): Demo2RouteImpactPreview => ({
  summary: "选择前先查看工作如何组织、在哪里等待，以及哪些动作不会发生。",
  changes: [
    { change_kind: "change", aspect: "work_allocation", label: "任务怎么分配", before: "本次工作组织方式尚未确定", after: mode === "adaptive_swarm" ? "三个受限工作包可并行准备，最终仍需统一汇总核对。" : mode === "fixed_workflow" ? "一个固定步骤序列处理资料、核对和汇总。" : "一个 Agent 串行处理全部资料和草稿。", detail: null },
    { change_kind: "change", aspect: "coordination", label: "并行与等待", before: "尚未记录本次协调方式", after: mode === "adaptive_swarm" ? "允许受限并行与工作包协调，不创建实际协作单元。" : "按顺序处理，不创建协作单元。", detail: null },
    { change_kind: "change", aspect: "human_control", label: "什么时候需要你", before: "确认节点尚未记录", after: mode === "adaptive_swarm" ? "关键节点需要用户确认，最终结果仍需复核。" : "在结果形成后由用户统一确认。", detail: null },
    { change_kind: "change", aspect: "policy_forecast", label: "演示策略预测", before: "尚未绑定本次执行方式", after: "由固定策略提供耗时、工具调用与并行上限。", detail: "不是实测结果。" },
    { change_kind: "preserve", aspect: "execution_boundary", label: "执行状态", before: "尚未启动", after: "选择后仍未启动，只记录本次路由。", detail: null },
    { change_kind: "no_external_action", aspect: "external_action", label: "不会发生", before: "未触发外部动作", after: "不会发送邮件、写入 CRM，也不会创建实际协作单元或访问真实业务系统。", detail: null },
  ],
  execution_status_before: "not_started",
  execution_status_after: "not_started",
  external_side_effect: "none",
});

const selectionReceipt = (mode: "single_agent" | "fixed_workflow" | "adaptive_swarm"): Demo2RouteSelectionReceipt => ({
  receipt_id: `route-receipt-${mode}`,
  from_cockpit_version: 1,
  to_cockpit_version: 2,
  from_item_version: 1,
  to_item_version: 2,
  selected_mode: mode,
  selection_source: mode === "adaptive_swarm" ? "admission" : "user_override",
  override_scope: mode === "adaptive_swarm" ? null : "this_run",
  forecast: forecast(mode === "adaptive_swarm" ? 30 : 15, mode === "adaptive_swarm" ? 900 : 720, mode === "adaptive_swarm" ? 3 : 1),
  changes: [
    { change_kind: "change", aspect: "route_decision", label: "本次执行方式", before: "等待选择", after: `已记录为${mode === "fixed_workflow" ? "固定流程" : mode === "single_agent" ? "单 Agent" : "自适应协作群组"}`, detail: "这里只记录路由决定，不代表执行已经开始。" },
    ...impactPreview(mode).changes,
  ],
  execution_status_before: "not_started",
  execution_status_after: "not_started",
  external_side_effect: "none",
  processing: { path: "policy_engine", model_called: false, elapsed_ms: 3 },
  summary: "服务端已记录本次执行方式；执行仍未启动，也未创建实际协作单元或触发外部动作。",
});

function cockpitFixture(): Demo2CockpitSnapshot {
  const profiles: Demo2RouteProfile[] = [
    { mode: "tool_call", label: "工具调用", summary: "只读取必要证据，不扩大执行范围。", forecast: forecast(2, 60, 1), tradeoff: "只能处理当前的单一核查点。", candidate_only: false, impact_preview: impactPreview("tool_call") },
    { mode: "single_agent", label: "单 Agent", summary: "由一个 Agent 串行完成工作。", forecast: forecast(12, 360, 1), tradeoff: "资源更少，但多个来源会串行处理。", candidate_only: false, impact_preview: impactPreview("single_agent") },
    { mode: "fixed_workflow", label: "固定流程", summary: "按预设步骤稳定推进。", forecast: forecast(18, 480, 1), tradeoff: "更容易审计，但不会根据新问题动态拆分。", candidate_only: false, impact_preview: impactPreview("fixed_workflow") },
    { mode: "adaptive_swarm", label: "自适应协作群组", summary: "按工作包受限并行评估。", forecast: forecast(30, 900, 3), tradeoff: "并行度更高，但协调成本和人工确认节点更多。", candidate_only: true, impact_preview: impactPreview("adaptive_swarm") },
  ];
  return {
    owner_id: "demo_user",
    backend: "memory",
    version: 1,
    last_event_sequence: 4,
    items: [{
      work_item_id: "customer_a_operating_review",
      owner_id: "demo_user",
      title: "客户 A 经营汇报",
      objective: "汇总经营事实、项目风险并形成可核对的汇报包。",
      business_status: "attention",
      priority: 94,
      facts: { value_band: "high", breadth: 4, parallelism: 3, deadline_pressure: "high", risk_band: "medium", budget_band: "approved", source_labels: ["邮件", "CRM", "项目周报", "日历"] },
      allowed_modes: ["single_agent", "fixed_workflow", "adaptive_swarm"],
      route_profiles: profiles,
      admission_status: "recommended",
      recommendation: {
        mode: "adaptive_swarm",
        summary: "高价值、多来源且可并行，建议进入受限协作评估。",
        reasons: [
          { factor: "breadth", label: "资料广度", detail: "需要汇总四类资料。" },
          { factor: "parallelism", label: "并行空间", detail: "三个工作包可以独立准备。" },
          { factor: "deadline", label: "截止压力", detail: "今日截止，串行等待成本较高。" },
        ],
        forecast: forecast(30, 900, 3),
        policy_version: "demo2-routing-v1",
      },
      selected_mode: null,
      selection_source: null,
      override_scope: null,
      execution_status: "not_started",
      selection_receipt: null,
      selection_receipts: [],
      version: 1,
      last_event_sequence: 1,
      last_event_type: "ADMISSION_EVALUATED",
    }],
  };
}

test.describe("Demo 2 work cockpit", () => {
  test("loads the server-backed queue and explains the recommended route without internal identifiers", async ({ page }, testInfo) => {
    await page.goto("/");
    await openLegacyCockpit(page);

    await expect(page.getByRole("heading", { name: "今天的工作，应该怎么处理" })).toBeVisible();
    const demoNav = page.getByRole("navigation", { name: "三个演示能力" });
    await expect(demoNav.getByRole("button", { name: /Demo 1.*持续任务/ })).toBeVisible();
    await expect(demoNav.getByRole("button", { name: /Demo 2.*智能调度/ })).toHaveAttribute("aria-current", "page");
    await expect(demoNav.getByRole("button", { name: /Demo 3.*受控执行/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /客户 A 经营汇报/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /供应商邮件回复/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /周报格式统一/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /报销异常核查/ })).toBeVisible();
    const decision = page.locator(".work-cockpit-decision-pane");
    await expect(decision.getByRole("heading", { name: "自适应协作群组", exact: true })).toBeVisible();
    await expect(decision.getByText("候选方式")).toBeVisible();
    const impactCanvas = page.locator(".work-cockpit-impact-canvas");
    await expect(impactCanvas.getByRole("heading", { name: "如果选择自适应协作群组，工作会怎样展开" })).toBeVisible();
    await expect(impactCanvas.getByText("三个受限工作包可并行准备，最终仍需统一汇总核对。")).toBeVisible();
    await expect(impactCanvas.getByText("选择后仍未启动，只记录本次路由。")).toBeVisible();
    await expect(impactCanvas.getByText("不会发送邮件、写入 CRM，也不会创建实际协作单元或访问真实业务系统。")).toBeVisible();
    await expect(decision.getByText("确认后只记录执行方式，任务尚未启动。")).toBeVisible();
    await expect(decision.getByText("规则路由，不调用大模型。", { exact: false })).toBeVisible();
    const callTrace = page.locator(".work-cockpit-overview .agent-call-trace");
    await expect(callTrace.getByText("本次用了什么", { exact: true })).toBeVisible();
    await callTrace.locator("summary").click();
    await expect(callTrace.getByText("任务条件评估", { exact: true })).toBeVisible();
    await expect(callTrace.getByText("受控协作运行时", { exact: true })).toBeVisible();
    await expect(callTrace.getByText("大模型 0", { exact: true })).toBeVisible();
    await expect(callTrace.getByText("外部工具 0", { exact: true })).toBeVisible();
    const confirmButton = decision.getByRole("button", { name: "记录本轮方式" });
    await expect(confirmButton).toBeVisible();
    const confirmButtonInViewport = await confirmButton.evaluate((button) => {
      const rect = button.getBoundingClientRect();
      return { top: rect.top, bottom: rect.bottom, innerHeight: window.innerHeight };
    });
    expect(confirmButtonInViewport.top).toBeGreaterThanOrEqual(0);
    expect(confirmButtonInViewport.bottom).toBeLessThanOrEqual(confirmButtonInViewport.innerHeight);
    expect(await confirmButton.evaluate((button) => {
      const rect = button.getBoundingClientRect();
      const hit = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
      return hit === button || button.contains(hit);
    })).toBe(true);
    await expect(page.getByText("演示数据 · CRM")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("customer_a_operating_review");
    await expect(page.locator("body")).not.toContainText("fixture:");
    await expect(page.locator("body")).not.toContainText("worker");
    await attachScreenshot(page, testInfo, "demo2-route-impact-preview-desktop");

    await demoNav.getByRole("button", { name: /Demo 1.*持续任务/ }).click();
    await expect(page.getByRole("heading", { name: "跨期间财务证据任务" }).first()).toBeVisible();
    const harnessNav = page.getByRole("navigation", { name: "演示场景" });
    await harnessNav.getByRole("button", { name: /Demo 3.*受控执行/ }).click();
    await expect(page.getByRole("heading", { name: "受约束的运营流程设计任务" }).first()).toBeVisible();
    await harnessNav.getByRole("button", { name: /Demo 2.*动态协作/ }).click();
    await expect(page.getByRole("heading", { name: "版本上线合规协作任务" }).first()).toBeVisible();
  });

  test("shows fixed lightweight routes as server decisions instead of fake user choices", async ({ page }) => {
    await page.goto("/");
    await openLegacyCockpit(page);
    await page.getByRole("button", { name: /供应商邮件回复/ }).click();

    const decision = page.locator(".work-cockpit-decision-pane");
    await expect(decision.getByRole("radio", { name: /单 Agent/ })).toBeChecked();
    await expect(decision.getByRole("radio", { name: /单 Agent/ })).toBeDisabled();
    await expect(decision.getByText("这项工作已按规则选择最轻量的方式，本轮不需要你再次确认。")).toBeVisible();
    await expect(decision.getByRole("button", { name: /记录本轮方式/ })).toHaveCount(0);
  });

  test("allows a bounded fixed-workflow override and records it before execution", async ({ page }, testInfo) => {
    let currentCockpit = cockpitFixture();
    await page.route("**/v1/demo2/cockpit", async (route) => {
      await route.fulfill({ json: currentCockpit });
    });
    let submitted: Record<string, unknown> = {};
    await page.route("**/v1/demo2/work-items/*/route", async (route) => {
      submitted = JSON.parse(route.request().postData() ?? "{}");
      const current = currentCockpit.items[0];
      const receipt = selectionReceipt("fixed_workflow");
      const selected = { ...current, admission_status: "route_selected" as const, selected_mode: "fixed_workflow" as const, selection_source: "user_override" as const, override_scope: "this_run" as const, selection_receipt: receipt, selection_receipts: [receipt], version: 2, last_event_sequence: 2, last_event_type: "ROUTE_SELECTED" as const };
      currentCockpit = { ...currentCockpit, version: 2, last_event_sequence: 5, items: [selected] };
      await route.fulfill({ json: { cockpit_version: 2, cockpit_last_event_sequence: 5, item: selected } });
    });
    await page.goto("/");
    await openLegacyCockpit(page);
    await page.getByRole("radio", { name: /固定流程/ }).check();
    const impactCanvas = page.locator(".work-cockpit-impact-canvas");
    await expect(impactCanvas.getByRole("heading", { name: "如果选择固定流程，工作会怎样展开" })).toBeVisible();
    await expect(impactCanvas.getByText("一个固定步骤序列处理资料、核对和汇总。")).toBeVisible();
    await page.getByRole("button", { name: /记录本轮方式/ }).click();
    await expect(page.getByRole("heading", { name: "本次工作方式已记录" })).toBeVisible();
    await expect(page.getByText("本次覆盖服务端推荐")).toBeVisible();
    await expect(page.getByText("仅本次运行")).toBeVisible();
    await expect(page.getByText("尚未执行")).toBeVisible();
    await expect(page.locator(".work-cockpit-impact-canvas.is-recorded").getByText("这里只记录路由决定，不代表执行已经开始。")).toBeVisible();
    const callTrace = page.locator(".work-cockpit-overview .agent-call-trace");
    await callTrace.locator("summary").click();
    await expect(callTrace.getByText("工作方式决策规则", { exact: true })).toBeVisible();
    await expect(callTrace.getByText("3 ms", { exact: false })).toBeVisible();
    await attachScreenshot(page, testInfo, "demo2-route-selection-receipt-desktop");
    expect(submitted.mode).toBe("fixed_workflow");
    expect(submitted.scope).toBe("this_run");
    expect(submitted.expected_version).toBe(1);
    expect(typeof submitted.idempotency_key).toBe("string");

    await page.reload();
    await openLegacyCockpit(page);
    await expect(page.getByRole("heading", { name: "本次工作方式已记录" })).toBeVisible();
    await expect(impactCanvas.getByRole("heading", { name: "本次已选择固定流程" })).toBeVisible();
    await expect(page.getByText("尚未执行").first()).toBeVisible();

    await page.getByRole("radio", { name: /单 Agent/ }).check();
    await expect(page.getByText("新选择尚未提交").first()).toBeVisible();
    await expect(impactCanvas.getByRole("heading", { name: "如果改为单 Agent，工作会怎样展开" })).toBeVisible();
    await expect(page.getByText("服务端当前为“固定流程”；改为“单 Agent”尚未提交。")).toBeVisible();
    await expect(page.getByRole("button", { name: "记录为单 Agent" })).toBeVisible();
  });

  test("keeps the local route choice visible when the server reports a version conflict", async ({ page }) => {
    let cockpitReads = 0;
    await page.route("**/v1/demo2/cockpit", async (route) => {
      cockpitReads += 1;
      const fixture = cockpitFixture();
      if (cockpitReads > 1) {
        fixture.version = 2;
        fixture.last_event_sequence = 5;
        fixture.items[0].version = 2;
        fixture.items[0].last_event_sequence = 2;
      }
      await route.fulfill({ json: fixture });
    });
    await page.route("**/v1/demo2/work-items/*/route", async (route) => {
      await route.fulfill({ status: 409, json: { detail: "工作项版本冲突" } });
    });

    await page.goto("/");
    await openLegacyCockpit(page);
    await page.getByRole("radio", { name: /固定流程/ }).check();
    await page.getByRole("button", { name: /记录本轮方式/ }).click();

    const decision = page.locator(".work-cockpit-decision-pane");
    await expect(decision.getByRole("radio", { name: /固定流程/ })).toBeChecked();
    await expect(decision.getByRole("alert")).toContainText("你的本次选择仍保留");
    await expect(decision.getByRole("button", { name: /重新读取/ })).toBeVisible();
  });

  test("keeps the cockpit usable at mobile width", async ({ page }, testInfo) => {
    await page.route("**/v1/demo2/cockpit", async (route) => {
      await route.fulfill({ json: cockpitFixture() });
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await openLegacyCockpit(page);
    await expect(page.getByRole("heading", { name: "今天的工作，应该怎么处理" })).toBeVisible();
    const callTrace = page.locator(".work-cockpit-overview .agent-call-trace");
    await callTrace.locator("summary").click();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
    const undersized = await page.locator(".demo-experience-nav button, .agent-call-trace summary, .work-cockpit button, .work-cockpit label, .work-cockpit-decision-pane button, .work-cockpit-decision-pane label").evaluateAll((elements) => elements.filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.height > 0 && rect.height < 44;
    }).length);
    expect(undersized).toBe(0);
    await attachScreenshot(page, testInfo, "demo2-route-impact-preview-mobile");
  });

  test("starts the selected adaptive swarm and renders server SSE work-package convergence", async ({ page }) => {
    const initial = cockpitFixture();
    const base = initial.items[0];
    const selectedReceipt = selectionReceipt("adaptive_swarm");
    const selected = {
      ...base,
      admission_status: "route_selected" as const,
      selected_mode: "adaptive_swarm" as const,
      selection_source: "admission" as const,
      override_scope: null,
      selection_receipt: selectedReceipt,
      selection_receipts: [selectedReceipt],
      version: 2,
      last_event_sequence: 2,
      last_event_type: "ROUTE_SELECTED" as const,
    };
    const runningExecution: Demo2ExecutionSnapshot = {
      execution_id: "demo2-execution-fake",
      owner_id: "demo_user",
      work_item_id: "customer_a_operating_review",
      mode: "adaptive_swarm" as const,
      version: 1,
      status: "running" as const,
      source_document_ids: ["crm-customer-a", "forecast-customer-a", "project-customer-a", "mail-customer-a"],
      worker_runs: [
        { worker_run_id: "facts", label: "经营事实核对", role: "revenue_analyst", objective: "核对 CRM 与预测中的经营口径。", status: "running", source_document_ids: ["crm-customer-a", "forecast-customer-a"], trigger: "initial_plan", artifact_version_id: null, depends_on: [], processing: null },
        { worker_run_id: "risk", label: "项目风险提取", role: "project_risk_analyst", objective: "从项目周报提取延期和风险。", status: "queued", source_document_ids: ["project-customer-a"], trigger: "initial_plan", artifact_version_id: null, depends_on: [], processing: null },
        { worker_run_id: "dependencies", label: "汇报依赖整理", role: "request_context_analyst", objective: "整理日历截止时间和汇报依赖。", status: "queued", source_document_ids: ["mail-customer-a"], trigger: "initial_plan", artifact_version_id: null, depends_on: [], processing: null },
      ],
      artifacts: [],
      events: [{ execution_id: "demo2-execution-fake", sequence: 1, event_type: "DYNAMIC_REPLAN", status: "running", worker_run_id: "facts", artifact_version_id: null, message: "已派发三个业务工作包", details: { reason: "recognized_revenue_vs_forecast_revenue" } }],
      receipt: null,
      last_event_sequence: 1,
      budget_max_workers: 3,
      budget_max_worker_runs: 4,
    };
    const processing = [
      { path: "language_model", kind: "language_model", label: "模型 Worker", model_called: true, model: "deepseek-v4-pro", elapsed_ms: 812, output_used: "model", fallback_reason: null },
      { path: "deterministic", kind: "deterministic", label: "确定性演示 Worker", model_called: false, model: null, elapsed_ms: 34, output_used: "deterministic", fallback_reason: null },
      { path: "language_model", kind: "language_model", label: "模型调用后使用安全回退", model_called: true, model: "deepseek-v4-pro", elapsed_ms: 901, output_used: "template_fallback", fallback_reason: "ValidationError" },
    ] as const;
    const workerArtifacts = runningExecution.worker_runs.map((unit, index) => ({
      artifact_version_id: `${unit.worker_run_id}-artifact`,
      artifact_id: `${unit.worker_run_id}-finding`,
      version: 1,
      title: `${unit.label}结果`,
      kind: "worker_finding" as const,
      status: "validated" as const,
      source_document_ids: unit.source_document_ids,
      content: { summary: `${unit.label}已完成。` },
      created_at: "2026-08-21T00:00:00Z",
      processing: processing[index],
    }));
    const completedExecution: Demo2ExecutionSnapshot = {
      ...runningExecution,
      version: 8,
      status: "completed",
      worker_runs: runningExecution.worker_runs.map((unit, index) => ({ ...unit, status: "completed", artifact_version_id: `${unit.worker_run_id}-artifact`, processing: processing[index] })),
      artifacts: [...workerArtifacts, { artifact_version_id: "report-artifact", artifact_id: "shared-fake", version: 2, title: "客户 A 经营汇报包", kind: "verified_report_bundle", status: "validated", source_document_ids: runningExecution.source_document_ids ?? [], content: { summary: "三个工作包均已完成来源校验。" }, created_at: "2026-08-21T00:00:00Z" }],
      events: [...runningExecution.events, { execution_id: "demo2-execution-fake", sequence: 8, event_type: "EXECUTION_COMPLETED", status: "completed", worker_run_id: null, artifact_version_id: "report-artifact", message: "共享工件已验证", details: {} }],
      receipt: { receipt_id: "receipt-fake", execution_id: "demo2-execution-fake", work_item_id: "customer_a_operating_review", worker_run_ids: ["facts", "risk", "dependencies"], artifact_version_ids: ["facts-artifact"], final_artifact_version_id: "facts-artifact", status: "completed" as const, summary: "内部工作包已汇总；没有发生外部系统写入。", external_side_effect: "none" as const, started_at: "2026-08-21T00:00:00Z", completed_at: "2026-08-21T00:00:01Z" },
      last_event_sequence: 8,
    };
    const staleExecution: Demo2ExecutionSnapshot = { ...runningExecution, version: 2, last_event_sequence: 2 };
    let releaseSse: (() => void) | undefined;
    const sseGate = new Promise<void>((resolve) => { releaseSse = resolve; });
    let releaseStaleGet: (() => void) | undefined;
    const staleGetGate = new Promise<void>((resolve) => { releaseStaleGet = resolve; });
    let executionReads = 0;
    let cockpit = { ...initial, version: 2, last_event_sequence: 6, items: [selected, ...initial.items.slice(1)] };
    await page.route("**/v1/demo2/cockpit", async (route) => route.fulfill({ json: cockpit }));
    await page.route("**/v1/demo2/work-items/*/execution", async (route) => {
      if (route.request().method() === "GET") {
        executionReads += 1;
        if (executionReads === 1) {
          await staleGetGate;
          await route.fulfill({ json: staleExecution });
          return;
        }
        await route.fulfill({ json: completedExecution });
        releaseStaleGet?.();
        return;
      }
      const item = { ...selected, execution_id: runningExecution.execution_id, execution_status: "running" as const, execution: runningExecution };
      cockpit = { ...cockpit, version: 3, last_event_sequence: 7, items: [item, ...cockpit.items.slice(1)] };
      await route.fulfill({ json: { cockpit_version: 3, cockpit_last_event_sequence: 7, item, execution: runningExecution } });
    });
    await page.route("**/v1/demo2/work-items/*/execution/events**", async (route) => {
      await sseGate;
      const item = { ...selected, execution_status: "completed" as const, execution: completedExecution };
      cockpit = { ...cockpit, version: 4, last_event_sequence: 8, items: [item, ...cockpit.items.slice(1)] };
      const started = JSON.stringify({ execution_id: "demo2-execution-fake", sequence: 2, event_type: "WORKER_STARTED", status: "running", message: "经营事实核对已开始", details: {} });
      const completed = JSON.stringify({ execution_id: "demo2-execution-fake", sequence: 8, event_type: "EXECUTION_COMPLETED", status: "completed", message: "共享工件已验证", details: {} });
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream", "cache-control": "no-cache" },
        body: `id: 2\nevent: WORKER_STARTED\ndata: ${started}\n\nid: 2\ndata: ${started}\n\nid: 8\nevent: EXECUTION_COMPLETED\ndata: ${completed}\n\nid: 8\ndata: ${completed}\n\n`,
      });
    });

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await openLegacyCockpit(page);
    await expect(page.getByRole("button", { name: /启动本次协作/ })).toBeVisible();
    await page.getByRole("button", { name: /启动本次协作/ }).click();
    await expect(page.getByRole("heading", { name: "业务工作包正在收敛" })).toBeVisible();
    releaseSse?.();
    await expect(page.getByRole("heading", { name: "业务工作包已收敛" })).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid").getByText("经营事实核对", { exact: true })).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid").getByText("允许来源", { exact: true }).first()).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid").getByText("销售预测", { exact: true })).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid").getByText("模型已调用 · deepseek-v4-pro", { exact: true })).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid").getByText("确定性处理", { exact: true })).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid").getByText("模板回退", { exact: true })).toBeVisible();
    await expect(page.locator(".demo2-work-unit-grid")).not.toContainText("等待人");
    await expect(page.locator(".demo2-work-unit-grid")).not.toContainText("验证中");
    const callTrace = page.locator(".work-cockpit-overview .agent-call-trace");
    await expect(callTrace.getByText("模型采用 1", { exact: true })).toBeVisible();
    await expect(callTrace.getByText("模型回退 1", { exact: true })).toBeVisible();
    await expect(callTrace.getByText("确定性 1", { exact: true })).toBeVisible();
    await page.locator(".demo2-replan-log summary").click();
    await expect(page.getByText("已派发三个业务工作包", { exact: true })).toBeVisible();
    await expect(page.getByText("正式收入与预测收入存在口径冲突，需要增加专项核验。", { exact: true })).toBeVisible();
    await expect(page.getByText("本次协作已完成", { exact: true })).toBeVisible();
    await expect(page.getByText("不会发送邮件、写入 CRM 或调用外部业务系统", { exact: true })).toBeVisible();
    await expect(page.locator("body")).not.toContainText("demo2-execution-fake");
    await expect(page.locator("body")).not.toContainText("shared-fake");
    await expect(page.locator("body")).not.toContainText("recognized_revenue_vs_forecast_revenue");
    expect(executionReads).toBe(2);
    expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1)).toBe(false);
  });

  test("reconnects the execution event stream after reloading an existing run", async ({ page }) => {
    const fixture = cockpitFixture();
    const receipt = selectionReceipt("adaptive_swarm");
    const running: Demo2ExecutionSnapshot = {
      execution_id: "existing-execution",
      owner_id: "demo_user",
      work_item_id: "customer_a_operating_review",
      mode: "adaptive_swarm",
      version: 4,
      status: "running",
      last_event_sequence: 4,
      source_document_ids: ["crm-customer-a"],
      worker_runs: [{ worker_run_id: "facts", label: "经营事实核对", objective: "核对经营口径。", role: "revenue_analyst", depends_on: [], source_document_ids: ["crm-customer-a"], trigger: "initial_plan", status: "running", artifact_version_id: null, processing: null }],
      artifacts: [],
      events: [],
      receipt: null,
      budget_max_workers: 3,
      budget_max_worker_runs: 4,
    };
    const selected = { ...fixture.items[0], admission_status: "route_selected" as const, selected_mode: "adaptive_swarm" as const, selection_source: "admission" as const, selection_receipt: receipt, selection_receipts: [receipt], execution_id: running.execution_id, execution_status: "running" as const };
    const cockpit = { ...fixture, version: 4, items: [selected] };
    let streamConnections = 0;
    await page.route("**/v1/demo2/cockpit", async (route) => route.fulfill({ json: cockpit }));
    await page.route("**/v1/demo2/work-items/*/execution", async (route) => route.fulfill({ json: running }));
    await page.route("**/v1/demo2/work-items/*/execution/events**", async (route) => {
      streamConnections += 1;
      await route.fulfill({ status: 200, headers: { "content-type": "text/event-stream" }, body: ": heartbeat\n\n" });
    });

    await page.goto("/");
    await openLegacyCockpit(page);
    await expect(page.getByRole("heading", { name: "业务工作包正在收敛" })).toBeVisible();
    await expect.poll(() => streamConnections).toBeGreaterThanOrEqual(1);
    const beforeReload = streamConnections;
    await page.reload();
    await openLegacyCockpit(page);
    await expect(page.getByRole("heading", { name: "业务工作包正在收敛" })).toBeVisible();
    await expect.poll(() => streamConnections).toBeGreaterThan(beforeReload);
  });

  test("refreshes intermediate worker failure events and offers a truthful reconnect", async ({ page }) => {
    const fixture = cockpitFixture();
    const receipt = selectionReceipt("adaptive_swarm");
    const running: Demo2ExecutionSnapshot = {
      execution_id: "failure-execution",
      owner_id: "demo_user",
      work_item_id: "customer_a_operating_review",
      mode: "adaptive_swarm",
      version: 4,
      status: "running",
      last_event_sequence: 4,
      source_document_ids: ["crm-customer-a", "project-customer-a"],
      worker_runs: [
        { worker_run_id: "facts", label: "经营事实核对", objective: "核对经营口径。", role: "revenue_analyst", depends_on: [], source_document_ids: ["crm-customer-a"], trigger: "initial_plan", status: "running", artifact_version_id: null, processing: null },
        { worker_run_id: "risk", label: "项目风险提取", objective: "提取项目风险。", role: "project_risk_analyst", depends_on: [], source_document_ids: ["project-customer-a"], trigger: "initial_plan", status: "queued", artifact_version_id: null, processing: null },
      ],
      artifacts: [],
      events: [],
      receipt: null,
      budget_max_workers: 3,
      budget_max_worker_runs: 4,
    };
    const interrupted: Demo2ExecutionSnapshot = {
      ...running,
      version: 6,
      last_event_sequence: 6,
      worker_runs: [
        { ...running.worker_runs[0], status: "failed", error_code: "worker_result_invalid" },
        { ...running.worker_runs[1], status: "cancelled", error_code: "peer_failed" },
      ],
      events: [
        { execution_id: running.execution_id, sequence: 5, event_type: "WORKER_FAILED", status: "running", worker_run_id: "facts", artifact_version_id: null, message: "经营事实核对失败", details: { error_code: "worker_result_invalid" } },
        { execution_id: running.execution_id, sequence: 6, event_type: "WORKER_CANCELLED", status: "running", worker_run_id: "risk", artifact_version_id: null, message: "项目风险提取已取消", details: { error_code: "peer_failed" } },
      ],
    };
    const selected = { ...fixture.items[0], admission_status: "route_selected" as const, selected_mode: "adaptive_swarm" as const, selection_source: "admission" as const, selection_receipt: receipt, selection_receipts: [receipt], execution_id: running.execution_id, execution_status: "running" as const };
    const cockpit = { ...fixture, version: 4, items: [selected] };
    let executionReads = 0;
    let streamConnections = 0;
    await page.route("**/v1/demo2/cockpit", async (route) => route.fulfill({ json: cockpit }));
    await page.route("**/v1/demo2/work-items/*/execution", async (route) => {
      executionReads += 1;
      await route.fulfill({ json: executionReads === 1 ? running : interrupted });
    });
    await page.route("**/v1/demo2/work-items/*/execution/events**", async (route) => {
      streamConnections += 1;
      const failed = JSON.stringify(interrupted.events[0]);
      const cancelled = JSON.stringify(interrupted.events[1]);
      await route.fulfill({
        status: 200,
        headers: { "content-type": "text/event-stream" },
        body: `id: 5\nevent: WORKER_FAILED\ndata: ${failed}\n\nid: 5\ndata: ${failed}\n\nid: 6\nevent: WORKER_CANCELLED\ndata: ${cancelled}\n\nid: 6\ndata: ${cancelled}\n\n`,
      });
    });

    await page.goto("/");
    await openLegacyCockpit(page);
    await expect(page.getByRole("article", { name: "经营事实核对 · 失败" })).toBeVisible();
    await expect(page.getByRole("article", { name: "项目风险提取 · 已取消" })).toBeVisible();
    await expect(page.getByRole("article", { name: "经营事实核对 · 失败" }).getByText("处理失败", { exact: true })).toBeVisible();
    const error = page.locator(".work-cockpit-error");
    await expect(error.getByText("协作进展需要重新连接", { exact: true })).toBeVisible();
    await expect(error).toContainText("已保留服务端已返回的状态");
    expect(executionReads).toBe(3);
    expect(streamConnections).toBe(1);

    await error.getByRole("button", { name: "重新读取" }).click();
    await expect.poll(() => streamConnections).toBeGreaterThanOrEqual(2);
    expect(executionReads).toBeGreaterThanOrEqual(4);
  });
});
