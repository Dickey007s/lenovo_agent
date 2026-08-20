import { expect, test, type APIRequestContext, type Page, type TestInfo } from "@playwright/test";

const API_URL = "http://localhost:8011";
const PENDING_MUTATION_KEY = "office-agent.pending-task-mutation.v1";

type TaskSnapshot = {
  task_id: string;
  status: string;
  phase: string;
  version: number;
  last_event_sequence: number;
  contract: {
    title: string;
    objective: string;
    deliverables: { title: string }[];
  };
  branches: { branch_id: string; status: string }[];
  artifact_versions: { artifact_version_id: string }[];
  controls: { kind: string; status: string; idempotency_key: string }[];
  last_commit: { artifact_version_ids: string[] } | null;
};

type PendingMutation = {
  taskId: string;
  kind: string;
  idempotencyKey: string;
  expectedVersion: number;
};

function ownerHeaders(owner: string) {
  return {
    "X-User-Id": owner,
    "X-User-Roles": "current_user,sales_manager",
  };
}

async function routeBrowserApiAs(page: Page, owner: string) {
  await page.route(`${API_URL}/**`, async (route) => {
    if (route.request().method() === "OPTIONS") {
      await route.continue();
      return;
    }
    await route.continue({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
  });
}

async function listTasks(request: APIRequestContext, owner: string) {
  const response = await request.get(`${API_URL}/v1/tasks`, { headers: ownerHeaders(owner) });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as TaskSnapshot[];
}

async function attachScreenshot(page: Page, testInfo: TestInfo, name: string) {
  await page.addStyleTag({ content: "nextjs-portal { display: none !important; }" });
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path, fullPage: true });
  await testInfo.attach(name, { path, contentType: "image/png" });
}

async function expectMobileArtifactWorkspace(page: Page) {
  const overflow = await page.evaluate(() => {
    const selectors = ["html", ".workspace-viewport", ".task-view-shell", ".task-artifact-workspace"];
    return selectors.map((selector) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing responsive element: ${selector}`);
      return { selector, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
    });
  });
  for (const item of overflow) {
    expect(item.scrollWidth, `${item.selector} should not scroll horizontally`).toBeLessThanOrEqual(item.clientWidth + 1);
  }

  const undersizedTargets = await page.locator(".task-artifact-workspace button, .task-artifact-workspace summary").evaluateAll((elements) => (
    elements.flatMap((element) => {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return [];
      return rect.height < 44 ? [{ text: element.textContent?.trim(), height: rect.height }] : [];
    })
  ));
  expect(undersizedTargets, "visible artifact actions should be at least 44px tall").toEqual([]);
}

async function expectMobileTaskDirector(page: Page) {
  const overflow = await page.evaluate(() => {
    const selectors = ["html", "body", ".app-shell", ".task-view-shell", ".task-director-canvas", ".task-director-side-pane"];
    return selectors.map((selector) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing responsive element: ${selector}`);
      return { selector, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
    });
  });
  for (const item of overflow) {
    expect(item.scrollWidth, `${item.selector} should not scroll horizontally`).toBeLessThanOrEqual(item.clientWidth + 1);
  }

  const undersizedTargets = await page.locator([
    ".task-view-shell button",
    ".task-view-shell summary",
    ".task-director-side-pane button",
    ".task-director-side-pane summary",
  ].join(", ")).evaluateAll((elements) => elements.flatMap((element) => {
    const rect = element.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return [];
    return rect.height < 44 ? [{ text: element.textContent?.trim(), height: rect.height }] : [];
  }));
  expect(undersizedTargets, "visible Task Director actions should be at least 44px tall").toEqual([]);
}

async function expectPrimarySurfaceToHideRuntimeJargon(page: Page) {
  const surface = page.locator(".app-shell.is-task-director");
  await expect(surface).toBeVisible();
  const visibleText = await surface.innerText();
  expect(visibleText).not.toMatch(/Demo 1|Snapshot|ORCHESTRATION BOARD|DECISION INBOX/i);
}

async function openLongTask(page: Page) {
  const tab = page.getByRole("tab", { name: "长任务", exact: true });
  await expect(tab).toBeVisible();
  await tab.click();
}

test("the first task path exposes the customer A purpose, decision facts, and confirmed outcomes", async ({ page, request }, testInfo) => {
  const owner = "e2e_customer_report_comprehension";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 1181, height: 900 });
  await page.goto("/");
  await openLongTask(page);

  await expect(page.getByRole("heading", { name: "准备客户 A 的经营汇报" })).toBeVisible();
  await expect(page.getByRole("button", { name: "开始准备汇报", exact: true })).toHaveCount(1);
  const promisedDeliverables = await page.locator(".task-director-empty li").allTextContents();
  await expectPrimarySurfaceToHideRuntimeJargon(page);
  await attachScreenshot(page, testInfo, "usability-first-open-1181");

  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  await expect(page.getByText("为什么需要你", { exact: true })).toBeVisible();
  await expect(page.getByText("确认后会发生什么", { exact: true })).toBeVisible();
  const impactPreview = page.locator(".task-impact-preview");
  await expect(impactPreview.locator("strong").filter({ hasText: "影响预演" })).toBeVisible();
  await expect(impactPreview.getByText("待确认正式口径", { exact: true })).toBeVisible();
  await expect(impactPreview.getByText("CRM 正式收入 2400 万元，并保留预测差异", { exact: true })).toBeVisible();
  await expect(impactPreview.getByText("按 CRM 正式口径重新核对，仍保持草稿", { exact: true })).toBeVisible();
  await expect(impactPreview.getByText("保持已核对状态", { exact: true })).toBeVisible();
  await expect(impactPreview.getByText("仍不发送", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看待确认项", exact: true })).toHaveCount(1);
  await expect(page.getByRole("button", { name: "采用正式口径并继续核对", exact: true })).toHaveCount(1);
  await expectPrimarySurfaceToHideRuntimeJargon(page);
  const overflow = await page.evaluate(() => ["html", "body", ".app-shell", ".workspace-viewport", ".task-view-shell"]
    .map((selector) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing usability surface: ${selector}`);
      return { selector, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
    }));
  for (const item of overflow) {
    expect(item.scrollWidth, `${item.selector} should not hide the main task horizontally at 1181px`)
      .toBeLessThanOrEqual(item.clientWidth + 1);
  }
  await expect(page.locator(".workspace-toast")).toBeHidden({ timeout: 4_000 });
  await attachScreenshot(page, testInfo, "usability-decision-1181");

  const controlRequest = page.waitForRequest(
    (request) => request.url().includes("/control") && request.method() === "POST",
  );
  await page.getByRole("button", { name: "采用正式口径并继续核对", exact: true }).click();
  expect((await controlRequest).postDataJSON()).toMatchObject({
    kind: "resolve_evidence",
    resolution_option_id: "use-official-crm-revenue",
  });
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  const impactReceipt = page.locator(".task-impact-receipt");
  await expect(impactReceipt.getByRole("heading", { name: "你的决定已经落实到材料中" })).toBeVisible();
  await expect(impactReceipt.getByText("采用 CRM 正式收入 2400 万元，并保留预测差异", { exact: true })).toBeVisible();
  await expect(impactReceipt.getByText("已按正式口径重新核对，仍为草稿", { exact: true })).toBeVisible();
  await expect(impactReceipt.getByText("保持已核对状态", { exact: true })).toBeVisible();
  await expect(impactReceipt.getByText("仍不发送", { exact: true })).toBeVisible();
  await expect(impactReceipt.getByText("任务从 v6 更新到 v7，并形成最终提交。", { exact: true })).toBeHidden();
  await expect(page.getByRole("button", { name: "查看经营分析", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看风险页", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "查看客户回复草稿", exact: true })).toBeVisible();
  await expect(page.getByText("客户回复仍是草稿，未发送", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "准备发送客户回复", exact: true })).toBeVisible();
  await expectPrimarySurfaceToHideRuntimeJargon(page);
  await expect(page.locator(".workspace-toast")).toBeHidden({ timeout: 4_000 });
  const completeOverflow = await page.evaluate(() => ["html", "body", ".app-shell", ".workspace-viewport", ".task-view-shell"]
    .map((selector) => {
      const element = document.querySelector<HTMLElement>(selector);
      if (!element) throw new Error(`Missing completed usability surface: ${selector}`);
      return { selector, clientWidth: element.clientWidth, scrollWidth: element.scrollWidth };
    }));
  for (const item of completeOverflow) {
    expect(item.scrollWidth, `${item.selector} should not hide completed task content at 1181px`)
      .toBeLessThanOrEqual(item.clientWidth + 1);
  }
  await attachScreenshot(page, testInfo, "usability-complete-1181");

  await page.reload();
  await openLongTask(page);
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  await expect(page.locator(".task-impact-receipt").getByRole("heading", { name: "你的决定已经落实到材料中" })).toBeVisible();

  const tasks = await listTasks(request, owner);
  expect(tasks).toHaveLength(1);
  expect(tasks[0].status).toBe("committed");
  expect(tasks[0].contract.title).toBe("客户 A 经营汇报");
  expect(promisedDeliverables).toEqual(tasks[0].contract.deliverables.map((deliverable) => deliverable.title));
});

test("a verified reply becomes a version-bound governed simulator action", async ({ page, request }, testInfo) => {
  const owner = "e2e_task_action_bridge";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await openLongTask(page);

  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await page.getByRole("button", { name: "采用正式口径并继续核对", exact: true }).click();
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();

  let prepareCount = 0;
  await page.route(/\/v1\/tasks\/[^/]+\/artifacts\/[^/]+\/actions\/email-send$/, async (route) => {
    prepareCount += 1;
    await route.fallback();
  });
  const prepareResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith("/actions/email-send") && response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "准备发送客户回复", exact: true }).click();
  const prepared = await (await prepareResponsePromise).json() as {
    run_id: string;
    trace_id: string;
    action: { task_artifact_binding: { artifact_version_id: string } | null };
  };

  const gate = page.getByRole("dialog", { name: "动作影响账本" });
  await expect(gate).toBeVisible();
  await expect(gate.getByRole("heading", { name: "发送外部邮件" })).toBeVisible();
  await expect(gate.getByText("预演已生成", { exact: true })).toBeVisible();
  await expect(gate.getByText("会改变", { exact: true })).toBeVisible();
  await expect(gate.getByText("会重新核对", { exact: true })).toBeVisible();
  await expect(gate.getByText("会保持", { exact: true })).toBeVisible();
  await expect(gate.getByText("不会发生", { exact: true })).toBeVisible();
  await expect(gate.getByText("基于已核对成果", { exact: true })).toBeVisible();
  await expect(gate.getByText(/客户回复草稿 v3 · 本轮汇报 v7/)).toBeVisible();
  await expect(gate.getByText("发送外部邮件", { exact: true }).first()).toBeVisible();
  await expect(gate.getByText("企业外客户", { exact: true })).toBeVisible();
  await expect(gate.getByText("customer@example.com", { exact: true })).toBeVisible();
  await expect(gate.getByText(/动作只绑定这一版成果/)).toBeVisible();
  await expect(gate).not.toContainText("email_simulator");
  await expect(gate).not.toContainText("office_action_simulator");
  await expect(gate).not.toContainText("email.send");
  await expect(gate).not.toContainText("Permit");
  const [gateBox, sidePaneBox] = await Promise.all([
    gate.boundingBox(),
    page.locator(".task-director-side-pane").boundingBox(),
  ]);
  const sidePanelColumns = await page.locator(".task-director-side-pane").evaluate(
    (element) => getComputedStyle(element).gridTemplateColumns,
  );
  const conversationPanelBox = await page.locator(".task-conversation-panel.is-task-workspace").boundingBox();
  expect(gateBox).not.toBeNull();
  expect(sidePaneBox).not.toBeNull();
  expect(conversationPanelBox).not.toBeNull();
  expect(sidePanelColumns.trim().split(/\s+/)).toHaveLength(1);
  expect(conversationPanelBox!.height).toBeGreaterThan(sidePaneBox!.height * 0.8);
  expect(gateBox!.width).toBeGreaterThan(sidePaneBox!.width * 0.8);
  expect(gateBox!.height).toBeGreaterThan(300);
  expect(gateBox!.x).toBeGreaterThanOrEqual(sidePaneBox!.x);
  expect(gateBox!.x + gateBox!.width).toBeLessThanOrEqual(sidePaneBox!.x + sidePaneBox!.width + 1);
  expect(prepareCount).toBe(1);
  await expect(page.locator(".workspace-toast")).toHaveCount(0);
  await attachScreenshot(page, testInfo, "demo3-action-impact-preview-1440");

  await gate.getByRole("button", { name: "批准这次影响" }).click();
  await expect(gate.getByText("你的批准已记录", { exact: true })).toBeVisible();
  await gate.getByRole("button", { name: "执行这次已批准的动作" }).click();

  await expect(page.getByText(/交给 Email Simulator 完成了模拟发送/)).toBeVisible();
  await expect(page.getByText(/没有向真实客户发送邮件/)).toBeVisible();
  await expect(gate.getByText("服务端已返回实际回执", { exact: true })).toBeVisible();
  await expect(gate.getByText("实际回执", { exact: true })).toBeVisible();
  await expect(gate.getByRole("heading", { name: "发送外部邮件" })).toBeVisible();
  await attachScreenshot(page, testInfo, "demo3-action-impact-receipt-1440");
  await gate.getByRole("button", { name: "收起动作回执" }).click();
  await expect(gate).toHaveCount(0);

  expect(prepared.action.task_artifact_binding?.artifact_version_id).toBeTruthy();
  const runResponse = await request.get(`${API_URL}/v1/runs/${prepared.run_id}`, {
    headers: ownerHeaders(owner),
  });
  expect(runResponse.ok()).toBeTruthy();
  const completed = await runResponse.json() as {
    status: string;
    tool_result: { simulator: string; output: { simulated: boolean } } | null;
    execution_receipt: { items: { item_id: string; change_kind: string }[] } | null;
  };
  expect(completed.status).toBe("EXECUTED");
  expect(completed.tool_result?.simulator).toBe("email_simulator");
  expect(completed.tool_result?.output.simulated).toBe(true);
  expect(completed.execution_receipt?.items.length).toBeGreaterThan(0);
  const auditResponse = await request.get(`${API_URL}/v1/audit/${prepared.trace_id}`, {
    headers: ownerHeaders(owner),
  });
  const audit = await auditResponse.json() as { event_type: string }[];
  expect(audit.map((event) => event.event_type)).toContain("PERMIT_ISSUED");
  expect(audit.map((event) => event.event_type)).toContain("TOOL_EXECUTED");

  await page.getByRole("button", { name: "审计", exact: true }).click();
  const auditPage = page.locator(".audit-page");
  await expect(auditPage.getByText("受控演示动作已执行", { exact: true })).toBeVisible();
  await expect(auditPage).not.toContainText("email_simulator");
  await expect(auditPage).not.toContainText("email.send");
  await expect(auditPage).not.toContainText("PERMIT_ISSUED");
  await expect(auditPage).not.toContainText("Permit");
  await auditPage.getByText("受控演示动作已执行", { exact: true }).click();
  await expect(auditPage.getByText("受控演示工具已返回结果；真实外部系统未连接。", { exact: true })).toBeVisible();
});

test("rejecting a task-derived action leaves the completed report intact", async ({ page, request }, testInfo) => {
  const owner = "e2e_task_action_reject";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await openLongTask(page);

  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await page.getByRole("button", { name: "采用正式口径并继续核对", exact: true }).click();
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  await page.getByRole("button", { name: "准备发送客户回复", exact: true }).click();

  const gate = page.getByRole("dialog", { name: "动作影响账本" });
  await expect(gate).toBeVisible();
  await gate.getByRole("button", { name: "不执行", exact: true }).click();
  await expect(gate.getByText("服务端确认本次未执行", { exact: true })).toBeVisible();
  await expect(gate.getByRole("heading", { name: "发送外部邮件" })).toBeVisible();
  await attachScreenshot(page, testInfo, "demo3-action-impact-denied-1440");

  const tasks = await listTasks(request, owner);
  expect(tasks).toHaveLength(1);
  expect(tasks[0].status).toBe("committed");
  const commit = tasks[0].last_commit;
  expect(commit).not.toBeNull();
  expect(commit?.artifact_version_ids).toHaveLength(3);
});

test("keeps the action impact ledger readable and bounded on mobile", async ({ page }, testInfo) => {
  const owner = "e2e_task_action_mobile";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await openLongTask(page);
  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await page.getByRole("button", { name: "采用正式口径并继续核对", exact: true }).click();
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  await page.getByRole("button", { name: "准备发送客户回复", exact: true }).click();

  const ledger = page.getByRole("dialog", { name: "动作影响账本" });
  await expect(ledger).toBeVisible();
  await expect(ledger.getByRole("button", { name: "批准这次影响" })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
  expect(overflow).toBe(false);
  const undersized = await ledger.locator("button, select, summary").evaluateAll(elements => elements.flatMap(element => {
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0 && rect.height < 44 ? [element.textContent?.trim()] : [];
  }));
  expect(undersized).toEqual([]);
  const nestedScroll = await ledger.evaluate(element => element.scrollHeight > element.clientHeight + 1);
  expect(nestedScroll).toBe(false);
  await expect(ledger.getByText("会改变", { exact: true })).toBeVisible();
  await expect(ledger.getByText("不会发生", { exact: true })).toBeVisible();
  await attachScreenshot(page, testInfo, "demo3-action-impact-preview-mobile-390");
});

test("fails closed when the server omits the impact preview", async ({ page }) => {
  const owner = "e2e_task_action_no_preview";
  await routeBrowserApiAs(page, owner);
  await page.route(/\/v1\/tasks\/[^/]+\/artifacts\/[^/]+\/actions\/email-send$/, async route => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    const body = await response.json() as Record<string, unknown>;
    delete body.impact_preview;
    const headers: Record<string, string> = { ...response.headers(), "content-type": "application/json" };
    delete headers["content-length"];
    delete headers["content-encoding"];
    await route.fulfill({ status: response.status(), headers, body: JSON.stringify(body) });
  });
  await page.goto("/");
  await openLongTask(page);
  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await page.getByRole("button", { name: "采用正式口径并继续核对", exact: true }).click();
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  await page.getByRole("button", { name: "准备发送客户回复", exact: true }).click();

  const ledger = page.getByRole("dialog", { name: "动作影响账本" });
  await expect(ledger).toBeVisible();
  await expect(ledger.getByText(/服务端尚未提供完整影响预演/)).toBeVisible();
  await expect(ledger.getByRole("button", { name: "批准这次影响" })).toBeDisabled();
  await expect(ledger.getByRole("button", { name: "执行这次已批准的动作" })).toHaveCount(0);
});

test("the initial task lookup cannot expose a duplicate-create action", async ({ page, request }) => {
  const owner = "e2e_task_initial_lookup";
  await routeBrowserApiAs(page, owner);
  const seeded = await request.post(`${API_URL}/v1/demo1/tasks`, {
    headers: {
      "X-User-Id": owner,
      "X-User-Roles": "current_user,sales_manager",
      "Idempotency-Key": "initial-lookup-seed",
    },
  });
  expect(seeded.ok()).toBeTruthy();

  let releaseTasks = () => {};
  const tasksGate = new Promise<void>((resolve) => { releaseTasks = resolve; });
  await page.route(`${API_URL}/v1/tasks`, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    await tasksGate;
    await route.fulfill({ response });
  });

  await page.goto("/");
  await openLongTask(page);
  await expect(page.locator(".task-director-empty").getByRole("heading", { name: "正在读取经营汇报任务" })).toBeVisible();
  await expect(page.getByRole("button", { name: "开始准备汇报", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "邮件", exact: true }).click();
  const loadingBackgroundTask = page.getByLabel("客户经营汇报");
  await expect(loadingBackgroundTask.getByText("正在读取经营汇报任务", { exact: true })).toBeVisible();
  await expect(loadingBackgroundTask.getByText("当前没有进行中的经营汇报", { exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "任务", exact: true }).click();
  releaseTasks();
  await expect(page.getByRole("heading", { name: "准备 3 份经营汇报材料" })).toBeVisible();
  expect(await listTasks(request, owner)).toHaveLength(1);
});

test("a no-task service failure is consistent across the workspace and decision pane", async ({ page }) => {
  const owner = "e2e_task_initial_offline";
  await routeBrowserApiAs(page, owner);
  await page.route(`${API_URL}/v1/tasks`, async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "fixture task service unavailable" }),
    });
  });

  await page.goto("/");
  await openLongTask(page);
  await expect(page.locator(".task-director-empty").getByRole("heading", { name: "经营汇报任务暂时不可用" })).toBeVisible();
  await expect(page.locator("#task-side-panel").getByRole("heading", { name: "经营汇报任务暂时不可用" })).toBeVisible();
  await expect(page.getByText("连接恢复后，这里会显示最近确认的待处理事项。", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "开始准备汇报", exact: true })).toHaveCount(0);
  await page.getByRole("button", { name: "文档", exact: true }).click();
  const offlineBackgroundTask = page.getByLabel("客户经营汇报");
  await expect(offlineBackgroundTask.getByText("经营汇报任务暂时不可用", { exact: true })).toBeVisible();
  await expect(offlineBackgroundTask.getByText("任务服务暂不可用，当前工作区仍可继续使用", { exact: true })).toBeVisible();
});

test("rapid repeated start intent creates and starts only one report task", async ({ page, request }) => {
  const owner = "e2e_task_single_start";
  await routeBrowserApiAs(page, owner);
  let createRequests = 0;
  let startRequests = 0;

  await page.route(`${API_URL}/v1/demo1/tasks`, async (route) => {
    createRequests += 1;
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    await new Promise((resolve) => setTimeout(resolve, 200));
    await route.fulfill({ response });
  });
  await page.route(/\/v1\/tasks\/[^/]+\/start$/, async (route) => {
    startRequests += 1;
    await route.continue({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
  });

  await page.goto("/");
  await openLongTask(page);
  const startButton = page.getByRole("button", { name: "开始准备汇报", exact: true });
  await startButton.evaluate((element) => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
  });

  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  expect(createRequests).toBe(1);
  expect(startRequests).toBe(1);
  expect(await listTasks(request, owner)).toHaveLength(1);
});

test("only the first open conflict in a branch is actionable without a conflict id contract", async ({ page }) => {
  const owner = "e2e_task_conflict_order";
  await routeBrowserApiAs(page, owner);

  let firstConflictResolved = false;
  const projectConflictSequence = (snapshot: Record<string, unknown>) => {
    const conflicts = snapshot.conflicts as Array<Record<string, unknown>> | undefined;
    if (!conflicts?.length) return snapshot;
    const first = conflicts[0];
    const secondId = `${String(first.conflict_id)}-second`;
    const second = {
      ...first,
      conflict_id: secondId,
      subject: "客户 A 收入口径的时间范围",
      summary: "同一份经营分析还有一个后续口径问题。",
      status: "open",
      resolution: null,
      resolved_at: null,
    };
    const branches = snapshot.branches as Array<Record<string, unknown>> | undefined;
    if (!firstConflictResolved && snapshot.status === "waiting_input") {
      snapshot.conflicts = [...conflicts, second];
      snapshot.branches = branches?.map((branch) => branch.branch_id === first.branch_id
        ? { ...branch, issue_ids: [...((branch.issue_ids as string[] | undefined) ?? []), secondId] }
        : branch);
    } else if (firstConflictResolved && snapshot.status === "committed") {
      snapshot.status = "waiting_input";
      snapshot.phase = "verify";
      snapshot.last_commit = null;
      snapshot.conflicts = [...conflicts, second];
      snapshot.branches = branches?.map((branch) => branch.branch_id === first.branch_id
        ? { ...branch, status: "waiting_evidence", issue_ids: [secondId], last_commit_id: null }
        : branch);
    }
    return snapshot;
  };

  await page.route(/\/v1\/tasks\/[^/]+\/start$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    const snapshot = projectConflictSequence(await response.json() as Record<string, unknown>);
    await route.fulfill({ response, json: snapshot });
  });
  await page.route(/\/v1\/tasks\/[^/]+\/advance$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    const snapshot = projectConflictSequence(await response.json() as Record<string, unknown>);
    await route.fulfill({ response, json: snapshot });
  });
  await page.route(/\/v1\/tasks\/[^/]+$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    const snapshot = projectConflictSequence(await response.json() as Record<string, unknown>);
    await route.fulfill({ response, json: snapshot });
  });
  await page.route(/\/v1\/tasks\/[^/]+\/controls$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    firstConflictResolved = true;
    const snapshot = projectConflictSequence(await response.json() as Record<string, unknown>);
    await route.fulfill({ response, json: snapshot });
  });

  await page.goto("/");
  await openLongTask(page);
  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  const cards = page.locator(".task-decision-card");
  await expect(cards).toHaveCount(2);
  const firstDecision = cards.nth(0).getByRole("button", { name: "采用正式口径并继续核对" });
  await expect(firstDecision).toBeEnabled();
  await expect(cards.nth(1).getByRole("button", { name: "采用正式口径并继续核对" })).toBeDisabled();
  await expect(cards.nth(1).getByText("请先处理同一材料中较早的待确认项。", { exact: true })).toBeVisible();
  await expect(cards.nth(0).locator(".task-impact-preview")).toContainText("影响预演");

  await firstDecision.click();
  await expect(cards).toHaveCount(1);
  await expect(page.locator(".task-impact-receipt")).toHaveCount(0);
  await expect(cards.getByRole("heading", { name: "客户 A 收入口径的时间范围" })).toBeVisible();
  await expect(cards.getByRole("button", { name: "采用正式口径并继续核对" })).toBeEnabled();
  await expect(cards.locator(".task-impact-preview")).toContainText("影响预演");
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("a terminal failure takes precedence over stale open conflict cards", async ({ page }) => {
  const owner = "e2e_task_terminal_conflict";
  await routeBrowserApiAs(page, owner);
  const projectFailure = (snapshot: Record<string, unknown>) => {
    if (snapshot.status !== "waiting_input") return snapshot;
    snapshot.status = "failed";
    snapshot.last_error = {
      code: "fixture_failed",
      message: "经营分析需要重新连接数据来源后再试。",
      recoverable: true,
      user_action: "重新连接后刷新任务状态。",
    };
    return snapshot;
  };

  await page.route(/\/v1\/tasks\/[^/]+\/start$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    await route.fulfill({ response, json: projectFailure(await response.json() as Record<string, unknown>) });
  });
  await page.route(/\/v1\/tasks\/[^/]+\/advance$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    await route.fulfill({ response, json: projectFailure(await response.json() as Record<string, unknown>) });
  });
  await page.route(/\/v1\/tasks\/[^/]+$/, async (route) => {
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    await route.fulfill({ response, json: projectFailure(await response.json() as Record<string, unknown>) });
  });

  await page.goto("/");
  await openLongTask(page);
  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await expect(page.getByRole("heading", { name: "任务需要处理后才能继续" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "任务未能继续" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "任务需要恢复" })).toBeVisible();
  await expect(page.getByRole("heading", { name: /请确认 \d+ 件事/ })).toHaveCount(0);
  await expect(page.locator(".task-decision-card")).toHaveCount(0);
  await page.unrouteAll({ behavior: "ignoreErrors" });
});

test("Task Director projects decisions, controls, errors, and versions from server facts", async ({ page, request }, testInfo) => {
  const owner = "e2e_task_director";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 1487, height: 1058 });
  await page.goto("/");
  await openLongTask(page);

  await expect(page.getByRole("heading", { name: "准备客户 A 的经营汇报" })).toBeVisible();
  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();

  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  await expect(page.getByText("2 / 3", { exact: true })).toBeVisible();
  await expect(page.getByText("2 份材料已核对，展开查看", { exact: true })).toBeVisible();
  await expect(page.getByText("已纳入本轮成果", { exact: true })).toHaveCount(0);
  await expect(page.locator(".workspace-toast")).toBeHidden({ timeout: 4_000 });
  await attachScreenshot(page, testInfo, "task-director-conflict-desktop");

  const viewTabs = page.getByRole("tablist", { name: "任务工作区视图" });
  const cockpitTab = viewTabs.getByRole("tab", { name: "今日工作" });
  const directorTab = viewTabs.getByRole("tab", { name: "长任务" });
  await directorTab.focus();
  await directorTab.press("ArrowRight");
  await expect(viewTabs.getByRole("tab", { name: "成果" })).toHaveAttribute("aria-selected", "true");
  await viewTabs.getByRole("tab", { name: "成果" }).press("Home");
  await expect(cockpitTab).toHaveAttribute("aria-selected", "true");
  await directorTab.click();

  await page.getByRole("tab", { name: "Agent 对话" }).click();
  await expect(page.getByRole("heading", { name: "请确认 1 件事" })).toHaveCount(0);
  await page.getByRole("button", { name: "查看待确认项" }).click();
  await expect(page.getByRole("tab", { name: "待我决定" })).toHaveAttribute("aria-selected", "true");
  await expect(page.getByRole("heading", { name: "请确认 1 件事" })).toBeFocused();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "查看待确认项" }).click();
  await expectMobileTaskDirector(page);
  await page.locator("#task-decision-conflicts-title").scrollIntoViewIfNeeded();
  await attachScreenshot(page, testInfo, "task-director-decision-mobile");

  await page.setViewportSize({ width: 1487, height: 1058 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.getByRole("button", { name: "查看相关材料" }).click();
  await expect(page.locator(".task-artifact-status")).toContainText("v1 · 候选版本");
  await expectPrimarySurfaceToHideRuntimeJargon(page);
  await page.getByRole("tab", { name: "长任务" }).click();

  const primaryDecision = page.getByRole("button", { name: "采用正式口径并继续核对" });
  await page.getByText("其他处理方式", { exact: true }).click();
  await page.getByRole("button", { name: "暂停分支" }).click();
  await expect(primaryDecision).toHaveCount(0);
  await expect(page.locator("#task-side-panel").getByRole("heading", { name: "任务已暂停" })).toBeVisible();
  await page.getByRole("button", { name: "恢复分支" }).click();
  await expect(primaryDecision).toBeEnabled();

  let rejectedOnce = false;
  await page.route(/\/v1\/tasks\/[^/]+\/controls$/, async (route) => {
    if (!rejectedOnce && route.request().method() === "POST" && route.request().postDataJSON()?.kind === "resolve_evidence") {
      rejectedOnce = true;
      await route.fulfill({ status: 409, contentType: "application/json", body: JSON.stringify({ detail: "测试冲突：任务版本已更新" }) });
      return;
    }
    await route.fallback();
  });
  await primaryDecision.click();
  await expect(page.getByRole("alert").filter({ hasText: "测试冲突" })).toBeVisible();
  await expect(page.getByText(/已刷新到 v\d+，请复核后重试/)).toBeVisible();

  await primaryDecision.click();
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  await expect(page.getByText("已纳入本轮成果", { exact: true })).toHaveCount(3);
  await expect(page.getByText("材料已准备", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("alert").filter({ hasText: "测试冲突" })).toHaveCount(0);
  await expect(page.locator(".workspace-toast")).toBeHidden({ timeout: 4_000 });
  await attachScreenshot(page, testInfo, "task-director-committed-desktop");

  await page.getByRole("tab", { name: "成果" }).click();
  await expect(page.locator(".task-artifact-status")).toContainText("v2 · 已验证");
  await expect(page.getByText(/正在查看历史版本/)).toHaveCount(0);
  await page.getByRole("button", { name: /^v1 候选版本/ }).click();
  await expect(page.getByText("正在查看历史版本 v1", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "返回当前版本" })).toBeVisible();
  await attachScreenshot(page, testInfo, "task-director-history-desktop");

  const tasks = await listTasks(request, owner);
  expect(tasks).toHaveLength(1);
  expect(tasks[0].status).toBe("committed");
  expect(rejectedOnce).toBeTruthy();
});

test("a late older task GET cannot roll back a newer mutation snapshot", async ({ page, request }) => {
  const owner = "e2e_demo1_snapshot_order";
  await routeBrowserApiAs(page, owner);
  const seeded = await request.post(`${API_URL}/v1/demo1/tasks`, {
    headers: {
      "X-User-Id": owner,
      "X-User-Roles": "current_user,sales_manager",
      "Idempotency-Key": "snapshot-order-seed",
    },
  });
  expect(seeded.ok()).toBeTruthy();

  let releaseStaleGet = () => {};
  let markStaleCaptured = () => {};
  let markStaleDelivered = () => {};
  const staleGetGate = new Promise<void>((resolve) => { releaseStaleGet = resolve; });
  const staleCaptured = new Promise<void>((resolve) => { markStaleCaptured = resolve; });
  const staleDelivered = new Promise<void>((resolve) => { markStaleDelivered = resolve; });
  let delayedSnapshot: TaskSnapshot | null = null;
  let delayedVersion = 0;
  let delayedSequence = 0;

  await page.route(/\/v1\/tasks\/[^/]+$/, async (route) => {
    if (route.request().method() !== "GET" || delayedSnapshot) {
      await route.fallback();
      return;
    }
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    const snapshot = (await response.json()) as TaskSnapshot;
    if (snapshot.status !== "ready") {
      await route.fulfill({ response, body: JSON.stringify(snapshot) });
      return;
    }
    delayedSnapshot = snapshot;
    delayedVersion = snapshot.version;
    delayedSequence = snapshot.last_event_sequence;
    markStaleCaptured();
    await staleGetGate;
    await route.fulfill({ response, body: JSON.stringify(snapshot) });
    markStaleDelivered();
  });

  await page.goto("/");
  await openLongTask(page);
  await staleCaptured;
  expect(delayedVersion).toBe(1);
  expect(delayedSequence).toBe(1);

  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  const syncState = page.getByLabel("任务状态摘要").getByText(/已同步 v\d+/).first();
  const versionBeforeStaleGet = Number((await syncState.innerText()).match(/v(\d+)/)?.[1]);
  expect(versionBeforeStaleGet).toBeGreaterThanOrEqual(6);

  releaseStaleGet();
  await staleDelivered;
  await page.waitForTimeout(250);
  const versionAfterStaleGet = Number((await syncState.innerText()).match(/v(\d+)/)?.[1]);
  expect(versionAfterStaleGet).toBeGreaterThanOrEqual(versionBeforeStaleGet);
  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  await expect(page.getByText("尚未开始", { exact: true })).toHaveCount(0);
});

test("task snapshot ordering uses the received SSE sequence as its floor", async ({ page, request }) => {
  const owner = "e2e_demo1_snapshot_sse_floor";
  await routeBrowserApiAs(page, owner);
  const seeded = await request.post(`${API_URL}/v1/demo1/tasks`, {
    headers: {
      "X-User-Id": owner,
      "X-User-Roles": "current_user,sales_manager",
      "Idempotency-Key": "sse-floor-seed",
    },
  });
  expect(seeded.ok()).toBeTruthy();

  let releaseStaleGet = () => {};
  let markStaleCaptured = () => {};
  let markStaleDelivered = () => {};
  let markReconnected = () => {};
  const staleGetGate = new Promise<void>((resolve) => { releaseStaleGet = resolve; });
  const staleCaptured = new Promise<void>((resolve) => { markStaleCaptured = resolve; });
  const staleDelivered = new Promise<void>((resolve) => { markStaleDelivered = resolve; });
  const reconnected = new Promise<void>((resolve) => { markReconnected = resolve; });
  let delayed = false;
  let syntheticEventSent = false;
  let reconnectAfter = "";

  await page.route(/\/v1\/tasks\/[^/]+$/, async (route) => {
    if (route.request().method() !== "GET" || delayed) {
      await route.fallback();
      return;
    }
    const response = await route.fetch({
      headers: {
        ...route.request().headers(),
        "x-user-id": owner,
        "x-user-roles": "current_user,sales_manager",
      },
    });
    const snapshot = (await response.json()) as TaskSnapshot;
    delayed = true;
    markStaleCaptured();
    await staleGetGate;
    await route.fulfill({
      response,
      body: JSON.stringify({
        ...snapshot,
        status: "failed",
        version: snapshot.version + 1,
        last_event_sequence: snapshot.last_event_sequence + 1,
      }),
    });
    markStaleDelivered();
  });

  await page.route(/\/v1\/tasks\/[^/]+\/events\?after=\d+$/, async (route) => {
    const url = new URL(route.request().url());
    if (syntheticEventSent) {
      reconnectAfter = url.searchParams.get("after") ?? "";
      markReconnected();
      await route.fallback();
      return;
    }
    syntheticEventSent = true;
    const taskId = url.pathname.split("/")[3];
    const event = {
      sequence: 3,
      event_id: "synthetic-sequence-floor",
      task_id: taskId,
      trace_id: "synthetic-sequence-floor",
      task_version: 1,
      branch_id: null,
      artifact_version_id: null,
      control_event_id: null,
      actor_id: owner,
      event_type: "TASK_STATUS_CHANGED",
      idempotency_key: null,
      payload: {},
      occurred_at: new Date().toISOString(),
    };
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: {
        "Access-Control-Allow-Origin": "http://localhost:3011",
        "Cache-Control": "no-cache",
      },
      body: `event: TASK_STATUS_CHANGED\ndata: ${JSON.stringify(event)}\n\n`,
    });
  });

  await page.goto("/");
  await openLongTask(page);
  await staleCaptured;
  await reconnected;
  expect(reconnectAfter).toBe("3");

  releaseStaleGet();
  await staleDelivered;
  await page.waitForTimeout(250);
  await expect(page.getByLabel("任务状态摘要").getByText("尚未开始", { exact: true })).toBeVisible();
  await expect(page.getByText("任务未能继续", { exact: true })).toHaveCount(0);
  await expect(page.getByLabel("任务状态摘要").getByText("正在对账", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "立即对账" }).first().click();
  await expect(page.getByLabel("任务状态摘要").getByText("正在对账", { exact: true })).toBeVisible();
  await expect(page.getByLabel("任务状态摘要").getByText(/^已同步 v/)).toHaveCount(0);
});

test("Demo 1 uses server facts from creation through the three-branch commit", async ({ page, request }, testInfo) => {
  const owner = "e2e_demo1_main";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");
  await openLongTask(page);

  const createButton = page.getByRole("button", { name: "开始准备汇报", exact: true });
  await expect(createButton).toBeEnabled();
  await createButton.click();
  await page.getByRole("button", { name: "邮件", exact: true }).click();
  const backgroundTask = page.getByLabel("当前经营汇报");
  await expect(backgroundTask.getByText("等待你的决定", { exact: true })).toBeVisible();
  await expect(backgroundTask.getByRole("button", { name: "前往处理" })).toBeVisible();
  await expect(page.locator(".task-runtime-panel")).toHaveCount(0);
  await expect(page.locator(".chat-pane")).not.toContainText("fixture:");
  await attachScreenshot(page, testInfo, "demo1-mail-background-task-desktop");
  await backgroundTask.getByRole("button", { name: "前往处理" }).click();
  await expect(page.getByRole("heading", { name: "请确认 1 件事" })).toBeVisible();
  await expect(page.locator("#task-decision-conflicts-title")).toBeFocused();
  const decisionPane = page.locator(".task-director-side-pane");
  const demoSources = decisionPane.getByText("查看演示数据来源", { exact: true });
  await expect(demoSources).toBeVisible();
  await demoSources.click();
  await expect(decisionPane.getByText("演示数据 · CRM 正式收入记录（v3）", { exact: true })).toBeVisible();
  await expect(decisionPane.getByText("演示数据 · 收入预测表（v2）", { exact: true })).toBeVisible();
  await expect(decisionPane).not.toContainText("fixture:");
  await attachScreenshot(page, testInfo, "demo1-open-conflict-desktop");

  const openAnalysis = page.getByRole("button", { name: "查看当前材料：经营分析", exact: true });
  await openAnalysis.scrollIntoViewIfNeeded();
  await openAnalysis.click();
  await expect(page.getByRole("heading", { name: "交付物工作区" })).toBeVisible();
  await expect(page.locator("#task-artifact-detail-title")).toHaveText("经营分析");
  await expect(page.locator(".task-artifact-status")).toContainText("v1 · 候选版本");
  await expect(page.locator(".task-artifact-verification")).toHaveText("存在冲突");
  await expect(page.getByRole("heading", { name: "证据冲突", exact: true })).toBeVisible();
  await expect(page.locator("details.task-artifact-sources[open]")).toHaveCount(0);
  await expect(page.locator("details.task-artifact-checks[open]")).toHaveCount(0);
  await expect(page.locator(".workspace-toast")).toBeHidden({ timeout: 4_000 });
  await attachScreenshot(page, testInfo, "demo1-conflict-artifact-desktop");

  await page.setViewportSize({ width: 390, height: 844 });
  await expectMobileArtifactWorkspace(page);
  const conflictAction = page.getByRole("button", { name: "采用正式口径并继续核对" });
  const steerInput = page.getByRole("textbox", { name: "方向指令" });
  for (const control of [conflictAction, steerInput]) {
    const box = await control.boundingBox();
    expect(box, "mobile control should have a rendered box").not.toBeNull();
    expect(box?.height).toBeGreaterThanOrEqual(44);
  }
  await page.locator("#task-artifact-detail-title").scrollIntoViewIfNeeded();
  await attachScreenshot(page, testInfo, "demo1-conflict-artifact-mobile");

  await page.setViewportSize({ width: 1440, height: 900 });
  await page.evaluate(() => window.scrollTo(0, 0));
  await steerInput.scrollIntoViewIfNeeded();
  await steerInput.fill("保持客户回复为草稿，并突出正式口径与预测差异。");
  await page.getByRole("button", { name: "记录方向指令" }).click();
  await expect(page.getByText(/方向指令已记录.*应用/)).toBeVisible();

  await conflictAction.scrollIntoViewIfNeeded();
  await conflictAction.click();
  await expect(page.getByRole("heading", { name: "本轮成果已准备好" })).toBeVisible();
  await expect(page.locator(".task-artifact-branch-status-committed")).toHaveCount(3);
  await expect(page.locator(".task-decision-card")).toHaveCount(0);
  await attachScreenshot(page, testInfo, "demo1-committed-desktop");

  const openReply = page.getByRole("navigation", { name: "任务分支与交付物" })
    .getByRole("button", { name: "查看客户回复草稿" });
  await openReply.scrollIntoViewIfNeeded();
  await openReply.click();
  await expect(page.locator("#task-artifact-detail-title")).toHaveText("客户回复草稿");
  await expect(page.locator(".task-artifact-status")).toContainText("v3 · 已验证");
  const officialRevenue = page.locator(".task-artifact-content-field").filter({
    has: page.locator("dt", { hasText: "正式收入（万元）" }),
  }).first();
  await expect(officialRevenue.locator("dd")).toContainText("2,400");
  const sendStatus = page.locator(".task-artifact-content-field").filter({
    has: page.locator("dt", { hasText: "发送状态" }),
  }).first();
  await expect(sendStatus.locator("dd")).toHaveText("仅草稿，未发送");
  await expect(page.locator(".task-artifact-commit-heading")).toContainText("最终提交");
  await expect(page.locator(".task-artifact-commit-facts code")).toHaveText(/^sha256:[0-9a-f]{64}$/);

  const replyLineage = page.locator(".task-artifact-lineage-button");
  await replyLineage.first().click();
  await expect(page.locator(".task-artifact-status")).toContainText("v1 · 候选版本");
  await expect(page.getByText("正在查看历史版本 v1", { exact: true })).toBeVisible();
  await expect(replyLineage.first()).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".task-artifact-navigation-button-selected")).toHaveCount(0);
  await openReply.click();
  await expect(page.locator(".task-artifact-status")).toContainText("v3 · 已验证");

  await page.locator(".workspace-viewport").evaluate((element) => { element.scrollTop = 0; });
  await attachScreenshot(page, testInfo, "demo1-committed-reply-artifact-desktop");

  const tasks = await listTasks(request, owner);
  expect(tasks).toHaveLength(1);
  expect(tasks[0].status).toBe("committed");
  expect(tasks[0].phase).toBe("commit");
  expect(tasks[0].branches.map((branch) => branch.status)).toEqual([
    "committed",
    "committed",
    "committed",
  ]);
  expect(tasks[0].controls.some((control) => control.kind === "steer" && control.status === "accepted")).toBeTruthy();
  expect(new Set(tasks[0].artifact_versions.map((artifact) => artifact.artifact_version_id)).size).toBe(7);

  const completedTaskId = tasks[0].task_id;
  await page.reload();
  await openLongTask(page);
  const replayButton = page.getByRole("button", { name: "开始新一轮汇报" });
  await expect(replayButton).toBeEnabled();

  const repeatKeys: string[] = [];
  let repeatStartRequests = 0;
  await page.route(`${API_URL}/v1/tasks/*/start`, async (route) => {
    repeatStartRequests += 1;
    await route.fallback();
  });
  await page.route(`${API_URL}/v1/demo1/tasks`, async (route) => {
    if (route.request().method() !== "POST") {
      await route.fallback();
      return;
    }
    repeatKeys.push(route.request().headers()["idempotency-key"] ?? "");
    if (repeatKeys.length === 1) {
      await route.abort("failed");
      return;
    }
    await route.fallback();
  });

  await replayButton.click();
  await expect.poll(() => repeatKeys.length).toBe(1);
  await expect(page.getByRole("heading", { name: "客户 A 经营汇报已准备完成" })).toBeVisible();
  await expect(page.getByText(/已连接当前工作区/).first()).toBeVisible();
  await expect(page.getByText("服务连接中断，正在恢复", { exact: true })).toHaveCount(0);
  await expect(replayButton).toBeEnabled();
  expect(await listTasks(request, owner)).toHaveLength(1);

  await replayButton.click();
  await expect(page.getByRole("heading", { name: "请确认 1 件事" })).toBeVisible();
  expect(repeatKeys).toHaveLength(2);
  expect(repeatKeys[0]).not.toBe("");
  expect(repeatKeys[1]).toBe(repeatKeys[0]);
  expect(repeatStartRequests).toBe(1);

  const repeatedTasks = await listTasks(request, owner);
  expect(repeatedTasks).toHaveLength(2);
  expect(repeatedTasks[0].task_id).not.toBe(completedTaskId);
  expect(repeatedTasks[0].status).toBe("waiting_input");
  expect(repeatedTasks[1].task_id).toBe(completedTaskId);
  expect(repeatedTasks[1].status).toBe("committed");
  expect(repeatedTasks[1].branches.map((branch) => branch.status)).toEqual([
    "committed",
    "committed",
    "committed",
  ]);
  expect(new Set(repeatedTasks[1].artifact_versions.map((artifact) => artifact.artifact_version_id)).size).toBe(7);
});

test("an aborted start keeps one idempotency key across reload and reconciles without duplicates", async ({ page, request }, testInfo) => {
  const owner = "e2e_demo1_recovery";
  await routeBrowserApiAs(page, owner);
  await page.goto("/");
  await openLongTask(page);

  const createButton = page.getByRole("button", { name: "开始准备汇报", exact: true });
  await expect(createButton).toBeEnabled();

  let aborted = false;
  let attemptedBody: { expected_task_version: number; idempotency_key: string } | undefined;
  await page.route(/\/v1\/tasks\/[^/]+\/start$/, async (route) => {
    if (route.request().method() !== "POST" || aborted) {
      await route.fallback();
      return;
    }
    aborted = true;
    attemptedBody = route.request().postDataJSON() as NonNullable<typeof attemptedBody>;
    await route.abort("failed");
  });

  await createButton.click();
  await expect(page.getByText(/启动结果待确认/)).toBeVisible();
  await expect(page.getByRole("button", { name: "立即对账" }).first()).toBeVisible();
  await expect(page.getByText(/已连接当前工作区/).first()).toBeVisible();
  expect(aborted).toBeTruthy();
  const capturedBody = attemptedBody as { expected_task_version: number; idempotency_key: string };

  const savedBeforeReload = await page.evaluate((key) => window.sessionStorage.getItem(key), PENDING_MUTATION_KEY);
  expect(savedBeforeReload).not.toBeNull();
  const pendingBeforeReload = JSON.parse(savedBeforeReload ?? "{}") as PendingMutation;
  expect(pendingBeforeReload.kind).toBe("start");
  expect(pendingBeforeReload.idempotencyKey).toBe(capturedBody.idempotency_key);
  expect(pendingBeforeReload.expectedVersion).toBe(1);

  const beforeRetry = await listTasks(request, owner);
  expect(beforeRetry).toHaveLength(1);
  expect(beforeRetry[0].version).toBe(1);
  expect(beforeRetry[0].artifact_versions).toHaveLength(0);
  await attachScreenshot(page, testInfo, "demo1-start-result-pending");

  await page.reload();
  await openLongTask(page);
  await expect(page.getByRole("button", { name: "立即对账" }).first()).toBeVisible();
  await expect(page.getByText(/已连接当前工作区/).first()).toBeVisible();
  const savedAfterReload = await page.evaluate((key) => window.sessionStorage.getItem(key), PENDING_MUTATION_KEY);
  expect(savedAfterReload).toBe(savedBeforeReload);

  await page.getByRole("button", { name: "立即对账" }).first().click();
  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  await expect.poll(() => page.evaluate((key) => window.sessionStorage.getItem(key), PENDING_MUTATION_KEY)).toBeNull();

  const afterRetry = await listTasks(request, owner);
  expect(afterRetry).toHaveLength(1);
  expect(afterRetry[0].version).toBe(6);
  expect(afterRetry[0].status).toBe("waiting_input");
  expect(afterRetry[0].artifact_versions).toHaveLength(5);
  expect(new Set(afterRetry[0].artifact_versions.map((artifact) => artifact.artifact_version_id)).size).toBe(5);

  const replay = await request.post(`${API_URL}/v1/tasks/${pendingBeforeReload.taskId}/start`, {
    headers: { ...ownerHeaders(owner), "Content-Type": "application/json" },
    data: {
      expected_task_version: pendingBeforeReload.expectedVersion,
      idempotency_key: pendingBeforeReload.idempotencyKey,
    },
  });
  expect(replay.ok()).toBeTruthy();
  const replayed = (await replay.json()) as TaskSnapshot;
  expect(replayed.version).toBe(2);
  expect(replayed.phase).toBe("observe");
  expect(replayed.status).toBe("running");
  expect(replayed.artifact_versions).toHaveLength(0);
  const afterReplay = await listTasks(request, owner);
  expect(afterReplay).toHaveLength(1);
  expect(afterReplay[0].version).toBe(6);
  expect(afterReplay[0].artifact_versions).toHaveLength(5);
  await attachScreenshot(page, testInfo, "demo1-start-reconciled");
});

test("progressive Task Runtime advances confirmed stages, supports review, disclosure, and reload recovery", async ({ page }, testInfo) => {
  const owner = `e2e_task_progressive_stages_${testInfo.repeatEachIndex}`;
  await routeBrowserApiAs(page, owner);
  let advanceCalls = 0;
  const observedStages: string[] = [];
  const releaseAdvanceGate: Array<() => void> = [];
  const advanceGates = Array.from({ length: 4 }, (_, index) => new Promise<void>((resolve) => {
    releaseAdvanceGate.push(resolve);
    if (index === 0) resolve();
  }));

  await page.route(/\/v1\/tasks\/[^/]+\/advance$/, async (route) => {
    const callIndex = advanceCalls;
    advanceCalls += 1;
    await advanceGates[callIndex];
    const response = await route.fetch({ headers: { ...route.request().headers(), ...ownerHeaders(owner) } });
    const snapshot = await response.json() as TaskSnapshot;
    observedStages.push(`${snapshot.status}:${snapshot.phase}`);
    await route.fulfill({ response, json: snapshot });
  });

  await page.goto("/");
  await openLongTask(page);
  await page.getByRole("button", { name: "开始准备汇报", exact: true }).click();
  await expect(page.locator(".task-director-phases li").nth(0)).toHaveClass(/is-current/);
  await expect(page.getByRole("heading", { name: "读取资料", exact: true })).toBeVisible();
  await expect(page.locator(".task-director-phases li").nth(3).getByRole("button")).toBeDisabled();
  await expect.poll(() => advanceCalls).toBeGreaterThanOrEqual(1);
  await expect(page.locator(".task-director-phases li").nth(1)).toHaveClass(/is-current/);
  await expect(page.getByRole("heading", { name: "拆分任务", exact: true })).toBeVisible();
  await expect(page.getByText(/完成条件：/).first()).toBeVisible();
  releaseAdvanceGate[1]();
  await expect(page.locator(".task-director-phases li").nth(2)).toHaveClass(/is-current/);
  await expect(page.getByRole("heading", { name: "正在生成候选材料" })).toBeVisible();
  releaseAdvanceGate[2]();
  await expect(page.locator(".task-director-phases li").nth(3)).toHaveClass(/is-current/);
  await expect(page.getByRole("heading", { name: "核对事实进行中", exact: true })).toBeVisible();
  releaseAdvanceGate[3]();

  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();
  expect(observedStages).toEqual([
    "running:plan",
    "running:act",
    "verifying:verify",
    "waiting_input:verify",
  ]);
  await expect(page.getByText("2 份材料已核对，展开查看", { exact: true })).toBeVisible();

  await page.locator(".task-director-phases li").nth(2).getByRole("button").click();
  await expect(page.getByText("阶段回看", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "已生成，等待事实核对" })).toBeVisible();
  await expect(page.getByText(/候选版本 v1/)).toHaveCount(3);
  await expect(page.locator(".task-candidate-materials")).not.toContainText("fixture:");
  await page.getByRole("button", { name: "返回当前阶段" }).click();

  await page.reload();
  await openLongTask(page);
  await expect(page.getByRole("heading", { name: "还差 1 个决定，确认后继续核对" })).toBeVisible();

  await page.locator(".task-director-phases li").nth(0).getByRole("button").click();
  await expect(page.getByText("阶段回看", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "返回当前阶段" })).toBeVisible();
  await expect(page.locator(".task-stage-detail")).not.toContainText("fixture:");
  await page.getByRole("button", { name: "返回当前阶段" }).click();

  await page.setViewportSize({ width: 390, height: 844 });
  await expectMobileTaskDirector(page);
});
