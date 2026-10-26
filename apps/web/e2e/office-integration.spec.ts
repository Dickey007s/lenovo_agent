import { expect, test, type Page } from "@playwright/test";

const api = "http://localhost:8011";

async function newAction(page: Page, path = "/") {
  await page.goto(path);
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  return page.getByRole("region", { name: "单步事项" });
}

async function captureWorkbench(page: Page, path: string) {
  await page.evaluate(() => {
    for (const element of document.querySelectorAll<HTMLElement>("*")) {
      if (element.scrollTop) element.scrollTop = 0;
      if (element.scrollLeft) element.scrollLeft = 0;
    }
    window.scrollTo(0, 0);
  });
  await page.screenshot({ path, fullPage: true });
}

async function delayAction(page: Page, status = 200) {
  let release!: () => void;
  let ready!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const accepted = new Promise<void>(resolve => { ready = resolve; });
  let snapshot: { run: { run_id: string } };
  await page.route("**/v1/harness/runs", async route => {
    if (route.request().method() !== "POST" || !route.request().postDataJSON().action) return route.continue();
    const response = await route.fetch();
    snapshot = await response.json();
    ready();
    await gate;
    await route.fulfill(status === 200 ? { response } : { status, json: { detail: "旧事项响应失败" } });
  });
  return {
    accepted,
    snapshot: () => snapshot,
    deliver: async () => {
      const finished = page.waitForEvent("requestfinished", request => request.method() === "POST" && request.url().endsWith("/runs"));
      release();
      await finished;
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    },
  };
}

for (const status of [200, 409, 500]) {
  test(`late action ${status} cannot replace or refresh a newer draft`, async ({ page }) => {
    const section = await newAction(page);
    const delayed = await delayAction(page, status);
    await section.getByRole("button", { name: "开始办理", exact: true }).click();
    await delayed.accepted;
    await page.getByRole("button", { name: "新建任务", exact: true }).click();
    const draft = page.getByRole("textbox", { name: "任务指令" });
    await draft.fill("保留当前新任务，不接受旧事项回执");
    const oldReads: string[] = [];
    page.on("request", request => {
      if (request.method() === "GET" && request.url().includes(delayed.snapshot().run.run_id)) oldReads.push(request.url());
    });
    await delayed.deliver();
    await expect(draft).toBeVisible();
    await expect(draft).toHaveValue("保留当前新任务，不接受旧事项回执");
    await expect(page.locator(".office-action-error")).toHaveCount(0);
    expect(oldReads).toEqual([]);
    await page.getByRole("button", { name: "办理事项", exact: true }).click();
    await expect(section.getByRole("button", { name: "开始办理", exact: true })).toBeEnabled();
    await expect(section.locator(".office-action-state")).toHaveCount(0);
    const persisted = await page.request.get(`${api}/v1/harness/runs/${delayed.snapshot().run.run_id}`, { headers: { "X-User-Id": "demo_user" } });
    expect(persisted.ok()).toBeTruthy();
  });
}

test("late action success leaves an explicitly opened historical task selected", async ({ page }) => {
  const section = await newAction(page);
  await section.getByLabel("事项标题").fill("历史事项保持选中");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await expect(section.locator(".office-action-receipt")).toBeVisible();
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  await section.getByLabel("事项标题").fill("迟到的新事项");
  const delayed = await delayAction(page);
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await delayed.accepted;
  await page.getByRole("button", { name: /^任务会话/ }).click();
  await page.getByTestId("task-session").filter({ hasText: "历史事项保持选中" }).getByRole("button", { name: /打开记录/ }).click();
  await expect(section.getByRole("heading", { name: "历史事项保持选中" })).toBeVisible();
  await delayed.deliver();
  await expect(section.getByRole("heading", { name: "历史事项保持选中" })).toBeVisible();
  await expect(section.getByRole("heading", { name: "迟到的新事项" })).toHaveCount(0);
});

test("both task entries expose the same action workbench without invented Loop controls", async ({ page }) => {
  const section = await newAction(page, "/agent-capabilities");
await expect(page.getByRole("button", { name: /^执行进展/ })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^成果与建议/ })).toHaveCount(0);
  await section.getByLabel("事项标题").fill("共用入口事项");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await expect(section.locator(".office-action-receipt")).toBeVisible();
  await page.reload();
  await expect(section.getByRole("heading", { name: "共用入口事项" })).toBeVisible();
  await expect(page.getByRole("button", { name: "暂停运行", exact: true })).toHaveCount(0);
  await expect(page.getByRole("button", { name: /^执行进展/ })).toHaveCount(0);
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await expect(page.getByRole("textbox", { name: "任务指令" })).toBeVisible();
  await expect(page.getByRole("group", { name: "任务方式" })).toBeVisible();
});

test("switching task mode isolates an in-flight action without deleting its record", async ({ page }) => {
  const section = await newAction(page);
  const delayed = await delayAction(page);
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await delayed.accepted;
  await page.getByRole("button", { name: "分析资料", exact: true }).click();
  const draft = page.getByRole("textbox", { name: "任务指令" });
  await draft.fill("模式切换后的分析任务");
  await delayed.deliver();
  await expect(draft).toBeVisible();
  await expect(draft).toHaveValue("模式切换后的分析任务");
  await expect(page.getByRole("button", { name: "分析资料", exact: true })).toHaveAttribute("aria-pressed", "true");
});

for (const viewport of [{ width: 1920, height: 1080 }, { width: 390, height: 844 }]) {
  test(`integrated workbench ${viewport.width}px layout and screenshots`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.goto("/");
    await page.getByRole("button", { name: "新建任务", exact: true }).click();
    const folder = process.env.CAPABILITY_SCREENSHOT_DIR ?? "../../outputs/ui-focus-20261008/screenshots";
    await captureWorkbench(page, `${folder}/analysis-${viewport.width}.png`);
    await page.getByRole("button", { name: "办理事项", exact: true }).click();
    const section = page.getByRole("region", { name: "单步事项" });
    await expect(section.getByLabel("事项类型")).toBeVisible();
    await captureWorkbench(page, `${folder}/action-${viewport.width}.png`);
    await section.getByLabel("事项类型").selectOption("compare_materials");
    await section.getByRole("button", { name: "开始办理", exact: true }).click();
    await expect(section.getByRole("group", { name: "材料对照" })).toBeVisible();
    await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await captureWorkbench(page, `${folder}/judgment-${viewport.width}.png`);
  });
}
