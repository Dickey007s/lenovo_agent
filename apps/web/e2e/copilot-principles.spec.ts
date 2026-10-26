import { expect, test, type Page } from "@playwright/test";
import { guardRealRecording } from "./recording-support";

async function enter(page: Page) {
  await page.goto("/");
  if ((page.viewportSize()?.width ?? 1280) <= 1000) await page.getByRole("button", { name: "展开工作区导航" }).click();
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "Demo 3 · 人机共驾", exact: true }).click();
  if (await page.getByRole("button", { name: "收起工作区导航" }).isVisible()) await page.getByRole("button", { name: "收起工作区导航" }).click();
  return page.getByRole("region", { name: "单步事项" });
}

test("R12: remember, reload, revoke and keep message confirmation independent", async ({ page }) => {
  await guardRealRecording(page, true);
  await page.setViewportSize({ width: 1440, height: 1000 });
  let section = await enter(page);
  await section.locator(".office-format-preference > summary").click();
  await section.getByLabel("整理方式", { exact: true }).selectOption("compact");
  const writes: string[] = [];
  page.on("request", request => { if (request.method() === "POST") writes.push(request.url()); });
  await section.getByLabel("记住个人文本整理方式", { exact: true }).check();
  expect(writes).toHaveLength(0);
  await section.getByLabel("事项内容", { exact: true }).fill("  第一项 \n\n 第二项  ");
  const started = page.waitForResponse(r => r.url().endsWith("/v1/harness/runs") && r.request().method() === "POST");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  const action = (await (await started).json()).run.office_action;
  expect(action.preview).toBe("第一项\n第二项");
  expect(action.model_called).toBe(false);
  await page.reload();
  section = await enter(page);
  await section.locator(".office-format-preference > summary").click();
  await expect(section.getByLabel("整理方式", { exact: true })).toHaveValue("compact");
  await expect(section.getByLabel("记住个人文本整理方式", { exact: true })).toBeChecked();
  await section.screenshot({ path: "../../outputs/principles-20261020/preference.png" });
  await section.getByLabel("事项类型").selectOption("send_message");
  await section.getByLabel("办理对象").selectOption("client-review");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await expect(section.getByRole("button", { name: "确认登记测试发件" })).toBeDisabled();
  await expect(section.getByRole("checkbox", { name: "已核对完整收件对象" })).not.toBeChecked();
  await section.getByRole("button", { name: "稍后处理", exact: true }).click();
  await section.getByRole("button", { name: "办理另一件事项" }).click();
  await section.locator(".office-format-preference > summary").click();
  await section.getByRole("button", { name: "清除整理偏好" }).click();
  await expect(section.getByLabel("整理方式", { exact: true })).toHaveValue("compact");
  await expect(section.getByLabel("记住个人文本整理方式", { exact: true })).not.toBeChecked();
  section = await enter(page);
  await expect(section.getByLabel("整理方式", { exact: true })).toHaveValue("spaced");
  const stored = await page.evaluate(() => Object.keys(localStorage).filter(k => k.startsWith("office-format-style-v1:")));
  expect(stored).toEqual([]);
});

test("R14: preview old draft without a write, abandon, then save a new revision", async ({ page }) => {
  await guardRealRecording(page, true);
  const section = await enter(page);
  await section.getByLabel("事项类型").selectOption("extract_excerpt");
  await section.getByLabel("事项内容", { exact: true }).fill("最初的材料内容\n第二行依据");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await section.getByRole("button", { name: "编辑这份草稿" }).click();
  await section.getByLabel("编辑摘录草稿").fill("这是一份新的人工修订");
  await section.getByRole("button", { name: "保存草稿修改" }).click();
  await expect(section.locator(".office-control-context")).toContainText("第 2 版");
  await section.locator(".office-action-history > summary").click();
  const writes: string[] = [];
  page.on("request", request => { if (request.method() === "POST") writes.push(request.url()); });
  await section.getByRole("button", { name: "取回第 1 版内容" }).click();
  await expect(section.getByLabel("编辑摘录草稿")).toHaveValue("最初的材料内容\n第二行依据");
  await expect(section).toContainText("尚未恢复");
  expect(writes).toHaveLength(0);
  await section.getByRole("button", { name: "放弃草稿修改" }).click();
  await expect(section.locator(".office-action-preview")).toContainText("这是一份新的人工修订");
  await section.getByRole("button", { name: "取回第 1 版内容" }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await section.getByLabel("编辑摘录草稿").scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../../outputs/principles-20261020/restore-mobile.png" });
  const saved = page.waitForResponse(r => r.url().endsWith("/action-controls") && r.request().method() === "POST");
  await section.getByRole("button", { name: "保存为新的草稿版本" }).click();
  const action = (await (await saved).json()).run.office_action;
  expect(action.revision).toBe(3);
  expect(action.history.map((h: { content_snapshot: string }) => h.content_snapshot)).toEqual(["最初的材料内容\n第二行依据", "这是一份新的人工修订", "最初的材料内容\n第二行依据"]);
  await page.reload();
  await expect(section.locator(".office-control-context")).toContainText("第 3 版");
  await expect(section.locator(".office-action-preview")).toContainText("最初的材料内容");
});

test("R10: pending filter finds deferred work but never executes it", async ({ page }) => {
  await guardRealRecording(page, true);
  const section = await enter(page);
  await section.getByLabel("事项类型").selectOption("compare_materials");
  await section.getByLabel("事项标题").fill("待负责人核对日期");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await section.getByRole("button", { name: "暂时无法判断，稍后处理" }).click();
  await section.getByRole("button", { name: "办理另一件事项" }).click();
  await section.getByLabel("事项标题").fill("已经完成的整理");
  await section.getByRole("button", { name: "开始办理", exact: true }).click();
  await section.locator(".office-recent > summary").click();
  const recent = section.locator(".office-recent");
  await expect(recent.getByRole("button", { name: /已经完成的整理/ })).toBeVisible();
  const writes: string[] = [];
  page.on("request", request => { if (request.method() === "POST") writes.push(request.url()); });
  await recent.getByLabel("最近事项筛选").selectOption("pending");
  await expect(recent.getByRole("button", { name: /已经完成的整理/ })).toHaveCount(0);
  await expect(recent.getByRole("button", { name: /待负责人核对日期/ })).toBeVisible();
  await recent.screenshot({ path: "../../outputs/principles-20261020/pending-filter.png" });
  await recent.getByRole("button", { name: /待负责人核对日期/ }).click();
  await expect(section.locator(".office-control-context")).toContainText("已暂缓");
  await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
  expect(writes).toHaveLength(0);
});

test("R12: unavailable storage leaves preference unsaved and local input usable", async ({ page }) => {
  await guardRealRecording(page, true);
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem;
    Storage.prototype.setItem = function(key, value) {
      if (key.startsWith("office-format-style-v1:")) throw new DOMException("blocked", "SecurityError");
      return original.call(this, key, value);
    };
  });
  const section = await enter(page);
  await section.locator(".office-format-preference > summary").click();
  await section.getByLabel("整理方式", { exact: true }).selectOption("compact");
  await section.getByLabel("记住个人文本整理方式", { exact: true }).click();
  await expect(section.getByRole("alert")).toContainText("浏览器未能保存偏好");
  await expect(section.getByLabel("记住个人文本整理方式", { exact: true })).not.toBeChecked();
  await expect(section.getByLabel("整理方式", { exact: true })).toHaveValue("compact");
});
