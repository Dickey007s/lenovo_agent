import { expect, test, type Page, type Route } from "@playwright/test";

const API_URL = process.env.HARNESS_E2E_API_URL ?? "http://localhost:8011";
type DemoId = "demo1" | "demo2" | "demo3";

const scenarioData: Record<DemoId, { scenario_id: string; title: string; goal: string; display: string; summary: string }> = {
  demo1: { scenario_id: "Finance-018", title: "核对跨年度往来账款", goal: "识别未收款与长期不变账款。", display: "2025 年往来明细", summary: "Excel 表格，共 1 个工作表；明细（A1:F18，列：客户、日期、金额）" },
  demo2: { scenario_id: "pm-014", title: "核对产品上线条件", goal: "并行核对配置、功能和兼容性测试。", display: "功能测试报告", summary: "Excel 表格，共 1 个工作表；功能测试（A1:J59，列：模块、用例、结果）" },
  demo3: { scenario_id: "Operations-008", title: "审核外呼流程边界", goal: "在准备动作前核对时间和人工升级规则。", display: "外呼流程说明", summary: "Markdown 业务说明，包含 6 个标题" },
};

function publicFiles(demo: DemoId, withRefs = false) {
  const item = scenarioData[demo];
  return [{
    ...(withRefs ? { file_ref: "file-01" } : {}),
    display_label: item.display,
    display_group: demo === "demo1" ? "财务往来" : demo === "demo2" ? "版本上线资料" : "运营合规资料",
    display_summary: item.summary,
  }];
}

function scenario(demo: DemoId) {
  const item = scenarioData[demo];
  return {
    ...item,
    demo_id: demo,
    dataset_label: "公开办公基准数据",
    dataset_version: "FORTE · pinned",
    deliverables: [demo === "demo2" ? "上线核对结论" : "可复核业务结论"],
    data_boundary: "仅限本轮公开基准输入文件",
    human_gate_summary: demo === "demo3" ? "产生外部影响前需要人工确认" : "形成结论后由用户确认是否进入后续动作",
    allowed_capabilities: demo === "demo3" ? ["读取规则", "核对动作边界", "生成流程工件"] : ["读取表格", "核对业务事实", "生成分析工件"],
    files: publicFiles(demo),
  };
}

function planFor(demo: DemoId, suffix = "本轮") {
  return {
    summary: `${suffix}动态计划`,
    units: [
      { unit_id: `read-${suffix}`, title: `${suffix}读取资料`, objective: "读取服务端允许的本轮输入。", input_file_refs: ["file-01"], depends_on: [], tool: "file.read", requires_human_gate: false, side_effect: "none", artifact_name: null, artifact_type: null },
      { unit_id: `review-${suffix}`, title: `${suffix}形成结论`, objective: "形成计划产出并等待后续执行。", input_file_refs: ["file-01"], depends_on: [`read-${suffix}`], tool: demo === "demo3" ? "action.preview" : "artifact.write", requires_human_gate: demo === "demo3", side_effect: demo === "demo3" ? "external_action" : "run_workspace_write", artifact_name: demo === "demo3" ? null : `${demo}-business-summary`, artifact_type: demo === "demo3" ? null : "summary" },
    ],
  };
}

function snapshot(demo: DemoId, options: { sequence?: number; version?: number; outputUsed?: boolean; failed?: boolean; suffix?: string } = {}) {
  const item = scenarioData[demo];
  const sequence = options.sequence ?? 4;
  const failed = Boolean(options.failed);
  const eventName = failed ? "harness_failed" : "ready_to_execute";
  return {
    run_id: `harness:${item.scenario_id}`,
    owner_id: "demo_user",
    scenario_id: item.scenario_id,
    status: failed ? "failed" : "ready_to_execute",
    version: options.version ?? 5,
    created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    last_event_sequence: sequence,
    source_documents: publicFiles(demo, true),
    plan: failed ? null : planFor(demo, options.suffix),
    model_receipt: { called: true, model: "deepseek-v4-pro", elapsed_ms: 1280, output_used: options.outputUsed ?? true },
    validation_errors: failed ? ["测试错误"] : [],
    events: sequence > 0 ? [{ sequence, event_name: eventName, occurred_at: new Date().toISOString(), status: failed ? "failed" : "ready_to_execute", message: failed ? "计划未通过安全校验，执行未启动。" : "计划通过服务端校验，执行未启动。", details: {} }] : [],
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) { await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) }); }

async function mockHarness(page: Page, options: { outputUsed?: boolean; failed?: boolean; disconnect?: boolean; failFirstStart?: boolean; delayedFinanceDetail?: boolean; outOfOrderGet?: boolean } = {}) {
  let activeDemo: DemoId = "demo1";
  let startCalls = 0;
  let getCalls = 0;
  let streamCalls = 0;
  const startKeys: string[] = [];
  const streamUrls: string[] = [];
  await page.route(`${API_URL}/v1/**`, async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (path === "/v1/threads" && route.request().method() === "POST") return fulfillJson(route, { thread_id: "thread-harness" });
    if (path === "/v1/evidence/requirements" || path === "/v1/workspace" || path === "/v1/tasks") return fulfillJson(route, []);
    if (path === "/v1/demo2/cockpit") return fulfillJson(route, { items: [] });
    if (path === "/v1/harness/scenarios") return fulfillJson(route, { scenarios: (["demo1", "demo2", "demo3"] as DemoId[]).map(scenario) });
    const detailDemo = (["demo1", "demo2", "demo3"] as DemoId[]).find((demo) => path === `/v1/harness/scenarios/${scenarioData[demo].scenario_id}`);
    if (detailDemo) {
      if (detailDemo === "demo1" && options.delayedFinanceDetail) await new Promise((resolve) => setTimeout(resolve, 500));
      return fulfillJson(route, scenario(detailDemo));
    }
    if (path === "/v1/harness/runs" && route.request().method() === "POST") {
      startCalls += 1;
      const body = route.request().postDataJSON() as { scenario_id: string; idempotency_key: string };
      startKeys.push(body.idempotency_key);
      activeDemo = (["demo1", "demo2", "demo3"] as DemoId[]).find((demo) => scenarioData[demo].scenario_id === body.scenario_id) ?? "demo1";
      if (options.failFirstStart && startCalls === 1) return fulfillJson(route, { detail: "unknown" }, 503);
      const queued = { ...snapshot(activeDemo, { sequence: 0, version: 1, outputUsed: options.outputUsed, failed: options.failed }), status: "queued", plan: null, model_receipt: null, events: [] };
      return fulfillJson(route, { run: queued, replayed: startCalls > 1 }, 202);
    }
    if (path.startsWith("/v1/harness/runs/") && path.endsWith("/events")) {
      streamCalls += 1; streamUrls.push(url.toString());
      const after = Number(url.searchParams.get("after") ?? "0");
      const names = options.disconnect && streamCalls === 1 ? ["workspace_index"] : ["planning_started", "planning_completed", "plan_validation", options.failed ? "harness_failed" : "ready_to_execute"];
      const body = names.map((name, index) => {
        const sequence = after + index + 1;
        const event = { sequence, event_name: name, occurred_at: new Date().toISOString(), status: options.failed ? "failed" : name === "ready_to_execute" ? "ready_to_execute" : name === "plan_validation" ? "validating" : "planning", message: name === "planning_started" ? "正在根据文件生成计划。" : name === "planning_completed" ? "模型计划已返回。" : name === "harness_failed" ? "计划未通过安全校验。" : name === "ready_to_execute" ? "计划已就绪，执行未启动。" : "服务端状态已更新。", details: {} };
        return `id: ${sequence}\nevent: ${name}\ndata: ${JSON.stringify(event)}\n\n`;
      }).join("");
      return route.fulfill({ status: 200, contentType: "text/event-stream", body });
    }
    if (path.startsWith("/v1/harness/runs/")) {
      getCalls += 1;
      if (options.disconnect && streamCalls === 1) {
        const indexed = snapshot(activeDemo, { sequence: 1, version: 2, outputUsed: options.outputUsed });
        return fulfillJson(route, {
          ...indexed,
          status: "indexing",
          plan: null,
          model_receipt: null,
          events: [{ sequence: 1, event_name: "workspace_index", occurred_at: new Date().toISOString(), status: "indexing", message: "已读取本轮文件范围。", details: {} }],
        });
      }
      if (options.outOfOrderGet && getCalls === 1) { await new Promise((resolve) => setTimeout(resolve, 350)); return fulfillJson(route, snapshot(activeDemo, { sequence: 1, version: 2, suffix: "迟到旧版" })); }
      return fulfillJson(route, snapshot(activeDemo, { sequence: Math.max(4, getCalls), version: 5, outputUsed: options.outputUsed, failed: options.failed, suffix: "最新" }));
    }
    return fulfillJson(route, {});
  });
  return { startKeys, streamUrls, getStartCalls: () => startCalls, getStreamCalls: () => streamCalls };
}

test("opens the unified work site by default and leaves it from any workspace rail item", async ({ page }) => {
  await mockHarness(page);
  await page.goto("/");
  await expect(page.getByText("工作现场", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: "核对跨年度往来账款" }).first()).toBeVisible();
  await expect(page.locator(".harness-workbench")).toBeVisible();
  await page.getByRole("button", { name: "邮件", exact: true }).click();
  await expect(page.locator(".harness-workbench")).toHaveCount(0);
});

test("projects all three real scenarios and rejects a late previous-scenario detail", async ({ page }) => {
  await mockHarness(page, { delayedFinanceDetail: true });
  await page.goto("/");
  await page.getByRole("button", { name: /Demo 2/ }).click();
  await expect(page.getByRole("heading", { name: "核对产品上线条件" }).first()).toBeVisible();
  await page.waitForTimeout(600);
  await expect(page.getByRole("heading", { name: "核对产品上线条件" }).first()).toBeVisible();
  await page.getByRole("button", { name: /Demo 3/ }).click();
  await expect(page.getByRole("heading", { name: "审核外呼流程边界" }).first()).toBeVisible();
  await expect(page.getByText("产生外部影响前需要人工确认")).toBeVisible();
  await page.getByRole("treeitem", { name: "外呼流程说明" }).click();
  await expect(page.getByText("Markdown 业务说明，包含 6 个标题")).toBeVisible();
});

test("renders the final server plan in the left workspace and receipts in the persistent right Agent pane", async ({ page }) => {
  const state = await mockHarness(page, { outOfOrderGet: true });
  await page.goto("/");
  await page.getByRole("button", { name: "开始本轮" }).click();
  await expect(page.getByText("最新读取资料")).toBeVisible();
  await page.waitForTimeout(450);
  await expect(page.getByText("迟到旧版读取资料")).toHaveCount(0);
  await expect(page.locator(".chat-pane").getByText("模型计划已采纳")).toBeVisible();
  await expect(page.locator(".chat-pane").getByText("计划已通过校验，任务尚未执行")).toBeVisible();
  await expect(page.getByText("2025 年往来明细").last()).toBeVisible();
  await expect(page.getByText("task.md")).toHaveCount(0);
  await expect(page.getByText(/Finance-018\/input/)).toHaveCount(0);
  await expect(page.getByText("file-01", { exact: true })).toHaveCount(0);
  await page.waitForTimeout(1_200);
  expect(state.getStreamCalls()).toBe(1);
});

test("shows rejected model output and reuses the same idempotency key after an unknown start result", async ({ page }) => {
  const state = await mockHarness(page, { outputUsed: false, failFirstStart: true });
  await page.goto("/");
  await page.getByRole("button", { name: "开始本轮" }).click();
  await expect(page.getByRole("button", { name: "重试启动" })).toBeVisible();
  await page.getByRole("button", { name: "重试启动" }).click();
  await expect(page.locator(".chat-pane").getByText("模型计划未采纳")).toBeVisible();
  expect(state.getStartCalls()).toBe(2);
  expect(state.startKeys[0]).toBe(state.startKeys[1]);
});

test("keeps a failed plan unexecuted and creates a fresh command only for a new round", async ({ page }) => {
  const state = await mockHarness(page, { failed: true });
  await page.goto("/");
  await page.getByRole("button", { name: "开始本轮" }).click();
  await expect(page.getByText("计划未通过服务端校验").first()).toBeVisible();
  await expect(page.getByText("计划已通过服务端校验，尚未执行任务")).toHaveCount(0);
  await page.getByRole("button", { name: "开始新一轮" }).click();
  await expect.poll(() => state.getStartCalls()).toBe(2);
  expect(state.startKeys[0]).not.toBe(state.startKeys[1]);
});

test("reconnects a closed named SSE from the last sequence", async ({ page }) => {
  const state = await mockHarness(page, { disconnect: true });
  await page.goto("/");
  await page.getByRole("button", { name: "开始本轮" }).click();
  await expect.poll(() => state.streamUrls.length).toBeGreaterThan(1);
  expect(state.streamUrls.some((url) => /after=[1-9]/.test(url))).toBeTruthy();
  const terminalConnections = state.getStreamCalls();
  await page.waitForTimeout(1_200);
  expect(state.getStreamCalls()).toBe(terminalConnections);
});

test("keeps the 390px work site private, touchable and free from horizontal overflow", async ({ page }) => {
  await mockHarness(page);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.locator(".harness-workbench")).toBeVisible();
  const privateText = await page.locator("body").innerText();
  expect(privateText).not.toMatch(/task\.md|rubric|prompt|sha256|Finance-018\/input|file-01|harness:|\b[0-9a-f]{40}\b|\b[0-9a-f]{64}\b/i);
  const overflow = await page.locator(".harness-workbench").evaluate((element) => ({ clientWidth: element.clientWidth, scrollWidth: element.scrollWidth }));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth + 1);
  const small = await page.locator(".harness-workbench button").evaluateAll((elements) => elements.flatMap((element) => { const rect = element.getBoundingClientRect(); return rect.width && rect.height < 44 ? [{ text: element.textContent, height: rect.height }] : []; }));
  expect(small).toEqual([]);
});
