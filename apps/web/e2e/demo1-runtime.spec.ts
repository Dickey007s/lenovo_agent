import { expect, test, type APIRequestContext, type Page, type TestInfo } from "@playwright/test";

const API_URL = "http://localhost:8011";
const PENDING_MUTATION_KEY = "office-agent.pending-task-mutation.v1";

type TaskSnapshot = {
  task_id: string;
  status: string;
  phase: string;
  version: number;
  branches: { branch_id: string; status: string }[];
  artifact_versions: { artifact_version_id: string }[];
  controls: { kind: string; status: string; idempotency_key: string }[];
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

async function expectRuntimeStack(page: Page, panelMaxHeight: number) {
  const rectangles = await page.evaluate(() => {
    const selectors = [
      ".chat-pane",
      ".chat-identity",
      ".active-task-strip",
      ".task-runtime-panel",
      ".conversation",
      ".chat-footer",
    ];
    return Object.fromEntries(selectors.map((selector) => {
      const element = document.querySelector(selector);
      if (!element) throw new Error(`Missing layout element: ${selector}`);
      const rect = element.getBoundingClientRect();
      return [selector, {
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        left: rect.left,
        width: rect.width,
        height: rect.height,
      }];
    }));
  });

  const pane = rectangles[".chat-pane"];
  const stack = [
    rectangles[".chat-identity"],
    rectangles[".active-task-strip"],
    rectangles[".task-runtime-panel"],
    rectangles[".conversation"],
    rectangles[".chat-footer"],
  ];
  for (const item of stack) {
    expect(item.left).toBeGreaterThanOrEqual(pane.left - 1);
    expect(item.right).toBeLessThanOrEqual(pane.right + 1);
  }
  for (let index = 0; index < stack.length - 1; index += 1) {
    expect(stack[index].bottom).toBeLessThanOrEqual(stack[index + 1].top + 1);
  }
  expect(rectangles[".task-runtime-panel"].height).toBeLessThanOrEqual(panelMaxHeight + 1);
  expect(rectangles[".conversation"].height).toBeGreaterThanOrEqual(180);
}

async function expectConflictBeforeBranches(page: Page) {
  const orderedSections = await page
    .locator(".task-runtime-panel > .task-conflicts, .task-runtime-panel > .task-branches")
    .evaluateAll((elements) => elements.map((element) => element.className));
  expect(orderedSections).toHaveLength(2);
  expect(orderedSections[0]).toContain("task-conflicts");
  expect(orderedSections[1]).toContain("task-branches");

  const firstTabStop = await page.locator(".task-runtime-panel").evaluate((panel) => {
    const controls = Array.from(panel.querySelectorAll<HTMLElement>("button, input, summary"));
    return controls.find((control) => control.tabIndex >= 0 && !control.hasAttribute("disabled"))?.textContent?.trim();
  });
  expect(firstTabStop).toContain("采用正式收入来源");
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

  const undersizedTargets = await page.locator(".task-view-shell button, .task-view-shell summary").evaluateAll((elements) => (
    elements.flatMap((element) => {
      const rect = element.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return [];
      return rect.height < 44 ? [{ text: element.textContent?.trim(), height: rect.height }] : [];
    })
  ));
  expect(undersizedTargets, "visible artifact actions should be at least 44px tall").toEqual([]);
}

test("Demo 1 uses server facts from creation through the three-branch commit", async ({ page, request }, testInfo) => {
  const owner = "e2e_demo1_main";
  await routeBrowserApiAs(page, owner);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/");

  const createButton = page.getByRole("button", { name: /创建任务/ });
  await expect(createButton).toBeEnabled();
  await createButton.click();
  await expect(page.getByText("ACTIVE TASK", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "启动任务" }).click();
  await expect(page.getByRole("heading", { name: "待处理的证据冲突" })).toBeVisible();
  await expect(page.locator(".task-branch-status.is-waiting_evidence")).toHaveCount(1);
  await expect(page.locator(".task-branch-status.is-committed")).toHaveCount(2);
  await expectConflictBeforeBranches(page);
  await expectRuntimeStack(page, 270);
  await attachScreenshot(page, testInfo, "demo1-open-conflict-desktop");

  const openAnalysis = page.getByRole("button", { name: "查看经营分析" });
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
  await expectRuntimeStack(page, 220);
  await expectMobileArtifactWorkspace(page);
  const conflictAction = page.getByRole("button", { name: "采用正式收入来源" });
  const steerInput = page.getByLabel("方向指令");
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
  await page.getByRole("button", { name: "记录指令" }).click();
  await expect(page.getByText(/方向指令已记录.*应用/)).toBeVisible();

  await conflictAction.scrollIntoViewIfNeeded();
  await conflictAction.click();
  await expect(page.getByText("RECENT TASK", { exact: true })).toBeVisible();
  await expect(page.getByText("已验证并提交", { exact: true })).toBeVisible();
  await expect(page.locator(".task-branch-status.is-committed")).toHaveCount(3);
  await expect(page.locator(".task-conflicts")).toHaveCount(0);
  await attachScreenshot(page, testInfo, "demo1-committed-desktop");

  const openReply = page.getByRole("button", { name: "查看客户回复草稿" });
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
  const replayButton = page.getByRole("button", { name: "再次演示" });
  await expect(replayButton).toBeEnabled();

  const repeatKeys: string[] = [];
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
  await expect(page.getByText("RECENT TASK", { exact: true })).toBeVisible();
  await expect(page.getByText("已连接当前工作区", { exact: true })).toBeVisible();
  await expect(page.getByText("服务连接中断，正在恢复", { exact: true })).toHaveCount(0);
  await expect(replayButton).toBeEnabled();
  expect(await listTasks(request, owner)).toHaveLength(1);

  await replayButton.click();
  await expect(page.getByText("ACTIVE TASK", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "启动任务" })).toBeEnabled();
  expect(repeatKeys).toHaveLength(2);
  expect(repeatKeys[0]).not.toBe("");
  expect(repeatKeys[1]).toBe(repeatKeys[0]);

  const repeatedTasks = await listTasks(request, owner);
  expect(repeatedTasks).toHaveLength(2);
  expect(repeatedTasks[0].task_id).not.toBe(completedTaskId);
  expect(repeatedTasks[0].status).toBe("ready");
  expect(repeatedTasks[1].task_id).toBe(completedTaskId);
  expect(repeatedTasks[1].status).toBe("committed");
});

test("an aborted start keeps one idempotency key across reload and reconciles without duplicates", async ({ page, request }, testInfo) => {
  const owner = "e2e_demo1_recovery";
  await routeBrowserApiAs(page, owner);
  await page.goto("/");

  const createButton = page.getByRole("button", { name: /创建任务/ });
  await expect(createButton).toBeEnabled();
  await createButton.click();
  await expect(page.getByText("ACTIVE TASK", { exact: true })).toBeVisible();

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

  await page.getByRole("button", { name: "启动任务" }).click();
  await expect(page.getByText(/启动结果待确认/)).toBeVisible();
  await expect(page.getByRole("button", { name: "立即对账" })).toBeVisible();
  await expect(page.getByText("已连接当前工作区", { exact: true })).toBeVisible();
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
  await expect(page.getByRole("button", { name: "立即对账" })).toBeVisible();
  await expect(page.getByText("已连接当前工作区", { exact: true })).toBeVisible();
  const savedAfterReload = await page.evaluate((key) => window.sessionStorage.getItem(key), PENDING_MUTATION_KEY);
  expect(savedAfterReload).toBe(savedBeforeReload);

  await page.getByRole("button", { name: "立即对账" }).click();
  await expect(page.getByRole("heading", { name: "待处理的证据冲突" })).toBeVisible();
  await expect.poll(() => page.evaluate((key) => window.sessionStorage.getItem(key), PENDING_MUTATION_KEY)).toBeNull();

  const afterRetry = await listTasks(request, owner);
  expect(afterRetry).toHaveLength(1);
  expect(afterRetry[0].version).toBe(2);
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
  expect(replayed.artifact_versions).toHaveLength(5);
  const afterReplay = await listTasks(request, owner);
  expect(afterReplay).toHaveLength(1);
  expect(afterReplay[0].version).toBe(2);
  expect(afterReplay[0].artifact_versions).toHaveLength(5);
  await attachScreenshot(page, testInfo, "demo1-start-reconciled");
});
