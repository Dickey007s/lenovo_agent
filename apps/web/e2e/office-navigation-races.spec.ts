import { expect, test, type Page } from "@playwright/test";

const api = "http://localhost:8011";
const headers = { "X-User-Id": "demo_user" };
const activeRunKey = "office-agent:forte-public-office:active-run";

async function delayNextGet(page: Page, path: string) {
  let release!: () => void;
  let ready!: () => void;
  let held = false;
  const gate = new Promise<void>(resolve => { release = resolve; });
  const accepted = new Promise<void>(resolve => { ready = resolve; });
  await page.route(url => url.pathname === path, async route => {
    if (route.request().method() !== "GET" || held) return route.continue();
    held = true;
    const response = await route.fetch();
    ready();
    await gate;
    await route.fulfill({ response });
  });
  return {
    accepted,
    deliver: async () => {
      const finished = page.waitForEvent("requestfinished", request => request.method() === "GET" && new URL(request.url()).pathname === path);
      release();
      await finished;
      await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve()))));
    },
  };
}

test("an initial restore cannot replace a newer completed action", async ({ page }) => {
  const old = await page.request.post(`${api}/v1/harness/runs`, {
    headers,
    data: {
      instruction: "办理事项：启动前保存的旧事项 A",
      idempotency_key: `restore-race-${Date.now()}`,
      action: { operation: "format_text", title: "启动前保存的旧事项 A", content: "仅整理旧记录。", target: "", due_date: null, source_ref: null },
    },
  });
  expect(old.ok()).toBeTruthy();
  const oldRun = (await old.json()).run;
  await page.addInitScript(({ key, runId }) => sessionStorage.setItem(key, runId), { key: activeRunKey, runId: oldRun.run_id });
  const delayed = await delayNextGet(page, `/v1/harness/tasks/${encodeURIComponent(oldRun.task_id)}`);
  await page.goto("/");
  await delayed.accepted;
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  const section = page.getByRole("region", { name: "单步事项" });
  await section.getByLabel("事项标题").fill("用户新建并已完成的事项 B");
  const response = page.waitForResponse(value => value.request().method() === "POST" && value.url().endsWith("/runs"));
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  const newRun = (await (await response).json()).run;
  await expect(section.getByRole("heading", { name: "用户新建并已完成的事项 B", exact: true })).toBeVisible();
  await expect(section.locator(".office-action-receipt")).toBeVisible();
  await delayed.deliver();
  await expect(section.getByRole("heading", { name: "用户新建并已完成的事项 B", exact: true })).toBeVisible();
  await expect(section.getByRole("heading", { name: "启动前保存的旧事项 A", exact: true })).toHaveCount(0);
  expect(await page.evaluate(key => sessionStorage.getItem(key), activeRunKey)).toBe(newRun.run_id);
});

test("a delayed action refresh cannot close a newer local action draft", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  const section = page.getByRole("region", { name: "单步事项" });
  await section.getByLabel("事项标题").fill("核对中的旧事项 A");
  const response = page.waitForResponse(value => value.request().method() === "POST" && value.url().endsWith("/runs"));
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  const run = (await (await response).json()).run;
  await expect(section.locator(".office-action-receipt")).toBeVisible();
  await expect(section.getByRole("button", { name: "办理另一件事项", exact: true })).toBeEnabled();
  const delayed = await delayNextGet(page, `/v1/harness/runs/${encodeURIComponent(run.run_id)}`);
  await section.getByRole("button", { name: "核对最新状态", exact: true }).click();
  await delayed.accepted;
  await section.getByRole("button", { name: "办理另一件事项", exact: true }).click();
  const title = section.getByLabel("事项标题");
  const content = section.getByLabel("事项内容", { exact: true });
  await title.fill("尚未提交的另一事项 B");
  await content.fill("新草稿内容必须保留，不得被旧事项核对结果隐藏。");
  await delayed.deliver();
  await expect(title).toBeVisible();
  await expect(title).toHaveValue("尚未提交的另一事项 B");
  await expect(content).toHaveValue("新草稿内容必须保留，不得被旧事项核对结果隐藏。");
  await expect(section.getByRole("button", { name: "开始办理", exact: true })).toBeEnabled();
});
