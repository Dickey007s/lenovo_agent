import { expect, test } from "@playwright/test";

const forecast = (estimated_tool_calls: number, estimated_runtime_seconds: number, max_workers: number) => ({
  source_type: "fixture_policy_forecast" as const,
  estimated_tool_calls,
  estimated_runtime_seconds,
  max_workers,
});

function cockpitFixture() {
  const profiles = [
    { mode: "tool_call", label: "工具调用", summary: "只读取必要证据，不扩大执行范围。", forecast: forecast(2, 60, 1), tradeoff: "只能处理当前的单一核查点。", candidate_only: false },
    { mode: "single_agent", label: "单 Agent", summary: "由一个 Agent 串行完成工作。", forecast: forecast(12, 360, 1), tradeoff: "资源更少，但多个来源会串行处理。", candidate_only: false },
    { mode: "fixed_workflow", label: "固定流程", summary: "按预设步骤稳定推进。", forecast: forecast(18, 480, 1), tradeoff: "更容易审计，但不会根据新问题动态拆分。", candidate_only: false },
    { mode: "adaptive_swarm", label: "自适应协作群组", summary: "按工作包受限并行评估。", forecast: forecast(30, 900, 3), tradeoff: "并行度更高，但协调成本和人工确认节点更多。", candidate_only: true },
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
      version: 1,
      last_event_sequence: 1,
      last_event_type: "ADMISSION_EVALUATED",
    }],
  };
}

test.describe("Demo 2 work cockpit", () => {
  test("loads the server-backed queue and explains the recommended route without internal identifiers", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "今天的工作，应该怎么处理" })).toBeVisible();
    await expect(page.getByRole("button", { name: /客户 A 经营汇报/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /供应商邮件回复/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /周报格式统一/ })).toBeVisible();
    await expect(page.getByRole("button", { name: /报销异常核查/ })).toBeVisible();
    const decision = page.locator(".work-cockpit-decision-pane");
    await expect(decision.getByRole("heading", { name: "自适应协作群组" })).toBeVisible();
    await expect(decision.getByText("候选方式")).toBeVisible();
    await expect(decision.getByText("确认后只记录执行方式，任务尚未启动。")).toBeVisible();
    await expect(page.getByText("演示数据 · CRM")).toBeVisible();
    await expect(page.locator("body")).not.toContainText("customer_a_operating_review");
    await expect(page.locator("body")).not.toContainText("fixture:");
    await expect(page.locator("body")).not.toContainText("worker");
  });

  test("shows fixed lightweight routes as server decisions instead of fake user choices", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /供应商邮件回复/ }).click();

    const decision = page.locator(".work-cockpit-decision-pane");
    await expect(decision.getByRole("radio", { name: /单 Agent/ })).toBeChecked();
    await expect(decision.getByRole("radio", { name: /单 Agent/ })).toBeDisabled();
    await expect(decision.getByText("这项工作已按规则选择最轻量的方式，本轮不需要你再次确认。")).toBeVisible();
    await expect(decision.getByRole("button", { name: /确认执行方式/ })).toHaveCount(0);
  });

  test("allows a bounded fixed-workflow override and records it before execution", async ({ page }) => {
    await page.route("**/v1/demo2/cockpit", async (route) => {
      await route.fulfill({ json: cockpitFixture() });
    });
    let submitted: Record<string, unknown> = {};
    await page.route("**/v1/demo2/work-items/*/route", async (route) => {
      submitted = JSON.parse(route.request().postData() ?? "{}");
      const current = cockpitFixture().items[0];
      await route.fulfill({ json: { cockpit_version: 2, cockpit_last_event_sequence: 5, item: { ...current, admission_status: "route_selected", selected_mode: "fixed_workflow", selection_source: "user_override", override_scope: "this_run", version: 2, last_event_sequence: 2, last_event_type: "ROUTE_SELECTED" } } });
    });
    await page.goto("/");
    await page.getByRole("radio", { name: /固定流程/ }).check();
    await expect(page.getByText("本次改为“固定流程”的影响")).toBeVisible();
    await page.getByRole("button", { name: /确认执行方式/ }).click();
    await expect(page.getByText("已记录为“固定流程” · 尚未启动本次任务")).toBeVisible();
    expect(submitted.mode).toBe("fixed_workflow");
    expect(submitted.scope).toBe("this_run");
    expect(submitted.expected_version).toBe(1);
    expect(typeof submitted.idempotency_key).toBe("string");
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
    await page.getByRole("button", { name: /确认执行方式/ }).click();

    const decision = page.locator(".work-cockpit-decision-pane");
    await expect(decision.getByRole("radio", { name: /固定流程/ })).toBeChecked();
    await expect(decision.getByRole("alert")).toContainText("你的本次选择仍保留");
    await expect(decision.getByRole("button", { name: /重新读取/ })).toBeVisible();
  });

  test("keeps the cockpit usable at mobile width", async ({ page }) => {
    await page.route("**/v1/demo2/cockpit", async (route) => {
      await route.fulfill({ json: cockpitFixture() });
    });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "今天的工作，应该怎么处理" })).toBeVisible();
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    expect(overflow).toBe(false);
    const undersized = await page.locator(".work-cockpit button, .work-cockpit label, .work-cockpit-decision-pane button, .work-cockpit-decision-pane label").evaluateAll((elements) => elements.filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.height > 0 && rect.height < 44;
    }).length);
    expect(undersized).toBe(0);
  });
});
