import { expect, test, type Page } from "@playwright/test";
import path from "node:path";

const phase = process.env.COPILOT_CAPTURE_PHASE === "before" ? "before" : "after";
const output = path.resolve(__dirname, "../../../docs/reports/copilot-cases-20261010/assets");

async function capture(page: Page, filename: string) {
  const style = await page.addStyleTag({ content: ".workspace-shell, .workspace-main, .workspace-content, .workspace-center, .workspace-layout, .workspace-body { height: auto !important; max-height: none !important; overflow: visible !important; }" });
  const originals = await page.getByRole("region", { name: "单步事项" }).evaluate(node => {
    const records: { element: HTMLElement; style: string | null }[] = [];
    let current = node.parentElement;
    while (current) {
      records.push({ element: current, style: current.getAttribute("style") });
      current.style.setProperty("height", "auto", "important");
      current.style.setProperty("max-height", "none", "important");
      current.style.setProperty("overflow", "visible", "important");
      current = current.parentElement;
    }
    (window as unknown as { captureStyles: typeof records }).captureStyles = records;
    return records.length;
  });
  expect(originals).toBeGreaterThan(0);
  try { await page.screenshot({ path: path.join(output, filename), fullPage: true }); }
  finally {
    await page.evaluate(() => {
      const state = window as unknown as { captureStyles?: { element: HTMLElement; style: string | null }[] };
      state.captureStyles?.forEach(({ element, style }) => style === null ? element.removeAttribute("style") : element.setAttribute("style", style));
      delete state.captureStyles;
    });
    await style.evaluate(node => node.parentNode?.removeChild(node));
  }
}

async function enter(page: Page) {
  await page.setViewportSize({ width: 1600, height: 1400 });
  await page.goto("/");
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  return page.getByRole("region", { name: "单步事项" });
}

test("C02: inspect and edit an excerpt without losing the source", async ({ page }) => {
  const section = await enter(page);
  await section.getByLabel("事项类型").selectOption("extract_excerpt");
  await section.getByLabel("事项标题").fill("客户评审会前摘录");
  await section.getByLabel("事项内容", { exact: true }).fill("项目周报：接口说明已整理；交付日期仍需负责人核准。\n对外汇报前须核对日期，不应将准备完成写成批准交付。");
  await section.getByRole("button", { name: "开始办理" }).click();
  await expect(section.getByRole("heading", { name: "摘录草稿" })).toBeVisible();
  if (phase === "after") await expect(section.locator(".office-source-review")).toHaveAttribute("open", "");
  await capture(page, `c02-${phase}.png`);
  await section.getByRole("button", { name: "编辑这份草稿" }).click();
  await section.getByLabel("编辑摘录草稿").fill("接口说明已整理；交付日期待负责人核准。本次只准备内部材料。");
  const saved = page.waitForResponse(r => r.url().endsWith("/action-controls") && r.request().method() === "POST");
  await section.getByRole("button", { name: "保存草稿修改" }).click();
  const action = (await (await saved).json()).run.office_action;
  expect(action.source_excerpt).toContain("对外汇报前须核对日期");
  expect(action.revision).toBe(2);
  expect(action.model_called).toBe(false);
  expect(action.external_action).toBe("none");
  if (phase === "after") {
    await expect(section.getByRole("heading", { name: "人工修订草稿" })).toBeVisible();
    await capture(page, "c02-edited.png");
  }
});

test("C08: revised message invalidates checks and exposes the change", async ({ page }) => {
  const section = await enter(page);
  await section.getByLabel("事项类型").selectOption("send_message");
  await section.getByLabel("办理对象").selectOption("client-review");
  await section.getByLabel("事项内容", { exact: true }).fill("评审材料预计周三提交，最终日期待负责人核准。");
  await section.getByRole("button", { name: "开始办理" }).click();
  for (const box of await section.getByRole("checkbox").all()) await box.check();
  await section.getByRole("button", { name: "修改内容", exact: true }).click();
  await section.getByLabel("事项内容", { exact: true }).fill("评审材料改为周五提交，仍需负责人核准。本次仅登记测试发件。");
  await section.getByRole("button", { name: "更新内容并重新核对" }).click();
  await expect(section.getByRole("button", { name: "确认登记测试发件" })).toBeDisabled();
  for (const box of await section.getByRole("checkbox").all()) await expect(box).not.toBeChecked();
  if (phase === "after") {
    await expect(section.locator(".office-recheck-notice")).toContainText("正文");
    await expect(section.locator(".office-version-changes")).toHaveAttribute("open", "");
  }
  await capture(page, `c08-${phase}.png`);
  await section.getByRole("button", { name: "稍后处理", exact: true }).click();
  await page.reload();
  await expect(section.getByRole("button", { name: "确认登记测试发件" })).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await expect(section.locator(".office-action-preview")).toContainText("review@example.invalid");
  if (phase === "after") await capture(page, "c08-mobile.png");
});

test("C11: explicit judgment records a choice, never dispatches downstream work", async ({ page }) => {
  const section = await enter(page);
  await section.getByLabel("事项类型").selectOption("compare_materials");
  await section.getByLabel("事项标题").fill("评审材料究竟周三还是周五提交？");
  await section.getByRole("button", { name: "开始办理" }).click();
  for (const option of await section.getByRole("radio").all()) await expect(option).not.toBeChecked();
  await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
  if (phase === "after") await expect(section.locator(".office-decision")).toContainText("不会自动继续其他任务");
  await capture(page, `c11-${phase}.png`);
  const writes: string[] = [];
  page.on("request", request => { if (request.method() === "POST") writes.push(request.url()); });
  await section.getByRole("radio", { name: "采用材料 B" }).check();
  await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
  await section.getByLabel("判断理由").fill("作为本次核对口径保留会议记录；仍需负责人确认是否替代原邮件。");
  const saved = page.waitForResponse(r => r.url().endsWith("/action-controls") && r.request().method() === "POST");
  await section.getByRole("button", { name: "记录这次判断" }).click();
  const action = (await (await saved).json()).run.office_action;
  expect(action.receipt.kind).toBe("decision_note");
  expect(action.external_action).toBe("none");
  expect(action.input.content).toContain("周三");
  expect(action.input.alternative_content).toContain("周五");
  expect(writes).toHaveLength(1);
  if (phase === "after") {
    await expect(section.locator(".office-decision-result")).toContainText("不会自动继续其他任务");
    await capture(page, "c11-recorded.png");
  }
});
