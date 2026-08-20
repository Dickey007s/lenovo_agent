import { expect, test, type Page, type TestInfo } from "@playwright/test";
import type {
  Demo2CockpitSnapshot,
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
    await expect(callTrace.getByText("协作单元", { exact: true })).toBeVisible();
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
    await expect(page.getByRole("heading", { name: "准备客户 A 的经营汇报" })).toBeVisible();
    await demoNav.getByRole("button", { name: /Demo 3.*受控执行/ }).click();
    await expect(page.getByRole("heading", { name: "受控动作与调用记录" })).toBeVisible();
    await demoNav.getByRole("button", { name: /Demo 2.*智能调度/ }).click();
    await expect(page.getByRole("heading", { name: "今天的工作，应该怎么处理" })).toBeVisible();
  });

  test("shows fixed lightweight routes as server decisions instead of fake user choices", async ({ page }) => {
    await page.goto("/");
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
});
