import { expect, test, type Page, type Route } from "@playwright/test";

const API_URL = process.env.HARNESS_E2E_API_URL ?? "http://localhost:8011";
type ScenarioId = "Finance-018" | "pm-014" | "Operations-008";

const files = {
  finance2025: { file_ref: "forte-a0bccc1df48cc6a1", display_label: "2025 年上半年往来明细", display_group: "财务往来", display_summary: "Excel 表格，共 1 个工作表；sheet1（A1:J76）" },
  finance2026: { file_ref: "forte-32eda8bd1465bd22", display_label: "2026 年往来明细", display_group: "财务往来", display_summary: "Excel 表格，共 1 个工作表；sheet1（A1:J59）" },
  releaseConfig: { file_ref: "forte-8190a8f0f714c421", display_label: "上线配置清单", display_group: "版本上线资料", display_summary: "Excel 表格，共 1 个工作表；配置清单" },
  releaseTest: { file_ref: "forte-8c3dc9b1239e42d1", display_label: "功能测试报告", display_group: "版本上线资料", display_summary: "Excel 表格，共 1 个工作表；功能测试" },
  operations: { file_ref: "forte-b43bfccfe810c0aa", display_label: "外呼合规规则说明", display_group: "运营合规资料", display_summary: "Markdown 业务说明，包含 6 个标题" },
};

const scenarios = [
  { scenario_id: "Finance-018", demo_id: "demo1", title: "核对跨年度往来账款", goal: "识别未收款与长期不变账款。", dataset_label: "公开办公基准数据 · FORTE", dataset_version: "FORTE 公开版本 · 345c1ec", data_boundary: "仅限所选 FORTE 文件", human_gate_summary: "任何外部动作不在本轮范围内", files: [files.finance2025, files.finance2026] },
  { scenario_id: "pm-014", demo_id: "demo2", title: "核对产品上线条件", goal: "并行核对配置、功能和兼容性测试。", dataset_label: "公开办公基准数据 · FORTE", dataset_version: "FORTE 公开版本 · 345c1ec", data_boundary: "仅限所选 FORTE 文件", human_gate_summary: "任何外部动作不在本轮范围内", files: [files.releaseConfig, files.releaseTest] },
  { scenario_id: "Operations-008", demo_id: "demo3", title: "审核外呼流程边界", goal: "核对时间和人工升级规则。", dataset_label: "公开办公基准数据 · FORTE", dataset_version: "FORTE 公开版本 · 345c1ec", data_boundary: "仅限所选 FORTE 文件", human_gate_summary: "任何外部动作不在本轮范围内", files: [files.operations] },
] as const;

function tablePreview(file = files.finance2025) {
  return { scenario_id: "Finance-018", ...file, kind: "table", sheet_name: "sheet1", columns: ["科目名称", "客商名称", "方向", "期末余额"], rows: [{ row_number: 2, values: ["其他应收款", "黄杉文化传播有限公司", "借", "1500000"] }, { row_number: 3, values: ["应付账款", "魔典引擎", "贷", "305630.12"] }], total_rows: 75, text: null, truncated: false };
}

function previewFor(path: string) {
  if (path.endsWith(files.operations.file_ref)) return { scenario_id: "Operations-008", ...files.operations, kind: "markdown", sheet_name: null, columns: [], rows: [], total_rows: null, text: "# 外呼合规规则\n\n工作日 9:00 前禁止外呼。无法确认身份时必须转人工。", truncated: false };
  if (path.endsWith(files.releaseConfig.file_ref)) return { ...tablePreview(files.releaseConfig), scenario_id: "pm-014", columns: ["配置项", "期望值", "当前值"], rows: [{ row_number: 2, values: ["灰度比例", "10%", "10%"] }], total_rows: 1 };
  if (path.endsWith(files.releaseTest.file_ref)) return { ...tablePreview(files.releaseTest), scenario_id: "pm-014", columns: ["模块", "用例", "结果"], rows: [{ row_number: 2, values: ["登录", "正常登录", "通过"] }], total_rows: 1 };
  return tablePreview(path.endsWith(files.finance2026.file_ref) ? files.finance2026 : files.finance2025);
}

function plan(selectedRefs: string[]) {
  return { summary: "先读取所选资料，再核对关键事实并形成引用结论。", units: [
    { unit_id: "read", title: "读取所选资料", objective: "读取并检查用户选择的公开文件。", input_file_refs: selectedRefs, depends_on: [], tool: "table.inspect", requires_human_gate: false, side_effect: "none", artifact_name: null, artifact_type: null },
    { unit_id: "analyze", title: "形成核对结论", objective: "回答用户问题并标注文件依据。", input_file_refs: selectedRefs, depends_on: ["read"], tool: "artifact.write", requires_human_gate: false, side_effect: "run_workspace_write", artifact_name: "read-only-result", artifact_type: "analysis" },
  ] };
}

function snapshot(body: { scenario_id: ScenarioId; instruction: string; selected_file_refs: string[] }, status: "queued" | "completed" | "failed" = "completed", sequence = 8) {
  const scenario = scenarios.find((item) => item.scenario_id === body.scenario_id)!;
  const selected = scenario.files.filter((file) => body.selected_file_refs.includes(file.file_ref));
  const failed = status === "failed";
  return {
    run_id: `harness:${body.scenario_id}`, owner_id: "demo_user", scenario_id: body.scenario_id,
    status, version: status === "queued" ? 1 : 9, created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    last_event_sequence: status === "queued" ? 0 : sequence, instruction: body.instruction, instruction_source: "user",
    source_documents: status === "queued" ? [] : selected, selection_reason: `用户选择了 ${selected.length} 份公开文件`,
    plan: status === "queued" || failed ? null : plan(body.selected_file_refs),
    model_receipt: status === "queued" ? null : { called: true, model: "deepseek-v4-pro", elapsed_ms: 1350, output_used: !failed },
    analysis_receipt: status === "completed" ? { called: true, model: "deepseek-v4-pro", elapsed_ms: 2180, output_used: true } : null,
    result: status === "completed" ? { summary: "核对完成：发现多项跨期余额需要人工关注。", findings: [
      { title: "余额连续未变", detail: "黄杉文化传播有限公司的其他应收款期末余额保持不变。", file_refs: body.selected_file_refs },
      { title: "保证金长期挂账", detail: "一项租赁保证金在所选期间没有发生额。", file_refs: body.selected_file_refs },
      { title: "应付款需要复核", detail: "一项应付款在所选期间保持不变。", file_refs: body.selected_file_refs },
      { title: "第四项默认收起", detail: "详细发现默认收起，避免结果首屏文字过载。", file_refs: body.selected_file_refs },
    ], follow_ups: ["请财务人员确认该余额是否仍应保留"], review_required: true } : null,
    validation_errors: failed ? ["模型引用了未选择的文件"] : [],
    events: status === "queued" ? [] : [{ sequence, event_name: failed ? "harness_failed" : "task_completed", occurred_at: new Date().toISOString(), status, message: failed ? "本轮未通过服务端校验，已停止且未发生外部动作。" : "本轮只读分析已完成，结果等待用户复核。", details: {} }],
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) { await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) }); }

async function mockHarness(page: Page, options: { failFirstStart?: boolean; disconnect?: boolean; failed?: boolean; catalogFailures?: number } = {}) {
  let catalogCalls = 0; let startCalls = 0; let streamCalls = 0;
  let currentBody = { scenario_id: "Finance-018" as ScenarioId, instruction: "", selected_file_refs: [files.finance2025.file_ref, files.finance2026.file_ref] };
  const starts: { scenario_id: ScenarioId; instruction: string; selected_file_refs: string[]; idempotency_key: string }[] = [];
  const streams: string[] = [];
  await page.route(`${API_URL}/v1/**`, async (route) => {
    const url = new URL(route.request().url()); const path = url.pathname;
    if (path === "/v1/health") return fulfillJson(route, { status: "ok" });
    if (path === "/v1/harness/scenarios") {
      catalogCalls += 1;
      if (catalogCalls <= (options.catalogFailures ?? 0)) return fulfillJson(route, { detail: "temporary" }, 503);
      return fulfillJson(route, { scenarios });
    }
    if (path.includes("/files/")) return fulfillJson(route, previewFor(path));
    if (path === "/v1/harness/runs" && route.request().method() === "POST") {
      startCalls += 1; const body = route.request().postDataJSON() as typeof currentBody & { idempotency_key: string };
      currentBody = body; starts.push(body);
      if (options.failFirstStart && startCalls === 1) return fulfillJson(route, { detail: "unknown" }, 503);
      return fulfillJson(route, { run: snapshot(body, "queued"), replayed: startCalls > 1 }, 202);
    }
    if (path.endsWith("/events")) {
      streamCalls += 1; streams.push(url.toString()); const after = Number(url.searchParams.get("after") ?? "0");
      const allEventNames = ["workspace_index", "planning_started", "planning_completed", "plan_validation", "analysis_started", "analysis_completed", "result_validation", options.failed ? "harness_failed" : "task_completed"];
      const eventNames = options.disconnect && streamCalls === 1 ? ["workspace_index"] : allEventNames.slice(after);
      const body = eventNames.map((eventName, index) => { const sequence = after + index + 1; const message = eventName === "workspace_index" ? "已读取并冻结场景文件索引。" : eventName === "planning_started" ? "正在根据文件索引生成工作计划。" : eventName === "planning_completed" ? "模型计划已返回，等待服务端校验。" : eventName === "plan_validation" ? "计划通过路径、工具、依赖与人工确认校验。" : eventName === "analysis_started" ? "正在读取所选公开文件并执行只读分析。" : eventName === "analysis_completed" ? "只读分析结果已返回，等待服务端核对文件引用。" : eventName === "result_validation" ? "结果已通过所选文件引用与只读边界校验。" : eventName === "task_completed" ? "本轮只读分析已完成，结果等待用户复核。" : "本轮未通过服务端校验。"; return `id: ${sequence}\nevent: ${eventName}\ndata: ${JSON.stringify({ sequence, event_name: eventName, occurred_at: new Date().toISOString(), status: eventName === "task_completed" ? "completed" : eventName === "harness_failed" ? "failed" : "running", message, details: {} })}\n\n`; }).join("");
      return route.fulfill({ status: 200, contentType: "text/event-stream", body });
    }
    if (path.startsWith("/v1/harness/runs/")) {
      if (options.disconnect && streamCalls === 1) return fulfillJson(route, { ...snapshot(currentBody, "queued"), status: "indexing", last_event_sequence: 1, version: 2 });
      return fulfillJson(route, snapshot(currentBody, options.failed ? "failed" : "completed"));
    }
    return fulfillJson(route, { detail: "not found" }, 404);
  });
  return { starts, streams, get startCalls() { return startCalls; }, get streamCalls() { return streamCalls; } };
}

test("opens real FORTE data, accepts a custom task, and shows a verifiable trajectory", async ({ page }) => {
  const state = await mockHarness(page);
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "FORTE 数据工作台" })).toBeVisible();
  await expect(page.getByText("黄杉文化传播有限公司")).toBeVisible();
  await expect(page.locator("body")).not.toContainText(/Demo\s*[123]/);

  const instruction = "只检查余额连续不变的客商，并告诉我依据来自哪些文件。";
  await page.getByRole("textbox", { name: "你想从这些数据里知道什么？" }).fill(instruction);
  await page.getByRole("button", { name: "运行任务" }).click();
  await expect.poll(() => state.starts.length).toBe(1);
  expect(state.starts[0].instruction).toBe(instruction);
  expect(state.starts[0].selected_file_refs).toEqual([files.finance2025.file_ref, files.finance2026.file_ref]);
  await expect(page.getByRole("heading", { name: /核对完成/ })).toBeVisible();
  await expect(page.getByText("余额连续未变", { exact: true })).toBeVisible();
  await expect(page.getByText("第四项默认收起", { exact: true })).toBeHidden();
  await page.getByRole("button", { name: "查看其余 1 条发现" }).click();
  await expect(page.getByText("第四项默认收起", { exact: true })).toBeVisible();
  await expect(page.getByText("仍需你判断 · 1 项")).toBeVisible();
  await expect(page.getByText("规划调用")).toBeVisible();
  await expect(page.getByText("分析调用")).toBeVisible();
  await expect(page.getByText("初步结果已形成")).toBeVisible();
  const body = await page.locator("body").innerText();
  expect(body).not.toMatch(/Finance-018\/input|sha256|task_instruction|思维链/);
});

test("freely browses all three collections and previews markdown content", async ({ page }) => {
  await mockHarness(page); await page.goto("/");
  await page.getByRole("button", { name: /运营规则/ }).click();
  await page.getByRole("button", { name: files.operations.display_label }).click();
  await expect(page.getByText("工作日 9:00 前禁止外呼")).toBeVisible();
  await expect(page.getByText("1 份文件已选")).toBeVisible();
  await expect(page.getByRole("textbox", { name: "你想从这些数据里知道什么？" })).toHaveValue(/必须转人工/);
});

test("file selection is explicit and scoped to the active collection", async ({ page }) => {
  const state = await mockHarness(page); await page.goto("/");
  const checkboxes = page.locator(".dataset-tree section.is-active input[type=checkbox]");
  await expect(checkboxes).toHaveCount(2); await checkboxes.nth(1).uncheck();
  await expect(page.getByText("1 份文件已选")).toBeVisible();
  await page.getByRole("button", { name: "运行任务" }).click();
  await expect.poll(() => state.starts.length).toBe(1);
  expect(state.starts[0].selected_file_refs).toEqual([files.finance2025.file_ref]);
});

test("reuses the same idempotency key when a start response is unknown", async ({ page }) => {
  const state = await mockHarness(page, { failFirstStart: true }); await page.goto("/");
  await page.getByRole("button", { name: "运行任务" }).click();
  await expect(page.getByText(/任务启动结果未知/)).toBeVisible();
  await page.getByRole("button", { name: "运行任务" }).click();
  await expect.poll(() => state.starts.length).toBe(2);
  expect(state.starts[0].idempotency_key).toBe(state.starts[1].idempotency_key);
  await expect(page.getByRole("heading", { name: /核对完成/ })).toBeVisible();
});

test("reconnects the named event stream from the last observed sequence", async ({ page }) => {
  const state = await mockHarness(page, { disconnect: true }); await page.goto("/");
  await page.getByRole("button", { name: "运行任务" }).click();
  await expect(page.getByRole("heading", { name: /核对完成/ })).toBeVisible();
  await expect.poll(() => state.streamCalls).toBeGreaterThanOrEqual(2);
  expect(state.streams.some((url) => new URL(url).searchParams.get("after") === "1")).toBeTruthy();
});

test("keeps a catalog outage understandable and recovers automatically", async ({ page }) => {
  await mockHarness(page, { catalogFailures: 2 }); await page.goto("/");
  await expect(page.getByRole("heading", { name: "FORTE 数据工作台" })).toBeVisible({ timeout: 12_000 });
  await expect(page.getByText("黄杉文化传播有限公司")).toBeVisible();
});

test("fails closed without fabricating a result", async ({ page }) => {
  await mockHarness(page, { failed: true }); await page.goto("/");
  await page.getByRole("button", { name: "运行任务" }).click();
  await expect(page.getByText("本轮已安全停止")).toBeVisible();
  await expect(page.getByText("模型引用了未选择的文件")).toBeVisible();
  await expect(page.getByRole("button", { name: "分析结果" })).toBeDisabled();
});

test("mobile keeps the dataset, composer, preview, and trajectory usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await mockHarness(page); await page.goto("/");
  await expect(page.getByRole("heading", { name: "FORTE 数据工作台" })).toBeVisible();
  const metrics = await page.evaluate(() => ({ viewport: document.documentElement.clientWidth, scroll: document.documentElement.scrollWidth }));
  expect(metrics.scroll).toBeLessThanOrEqual(metrics.viewport);
  const shortControls = await page.locator("button:visible, summary:visible").evaluateAll((nodes) => nodes.filter((node) => (node as HTMLElement).getBoundingClientRect().height < 44).map((node) => ({ text: node.textContent, height: (node as HTMLElement).getBoundingClientRect().height })));
  expect(shortControls).toEqual([]);
  await expect(page.getByRole("textbox", { name: "你想从这些数据里知道什么？" })).toBeVisible();
  await expect(page.locator(".table-preview")).toBeVisible();
});
