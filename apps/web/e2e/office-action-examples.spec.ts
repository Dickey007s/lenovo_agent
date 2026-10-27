import { expect, test, type Page } from "@playwright/test";
import examples from "../app/office-action-examples.json";

// Five headline cases, one per risk level L1 (quiet) -> L5 (strong confirmation / refused),
// each tied to real files in the shared library.
async function enter(page: Page) {
  await page.goto("/");
  if ((page.viewportSize()?.width ?? 1280) <= 1000) await page.getByRole("button", { name: "展开工作区导航" }).click();
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "Demo 3 · 人机共驾", exact: true }).click();
  const close = page.getByRole("button", { name: "收起工作区导航" });
  if (await close.isVisible()) await close.click();
  const section = page.locator(".unified-workbench");
  // The five level cases are the main path: visible straight away, no extra clicks.
  await expect(section.getByRole("group", { name: "选择演示案例" }).getByRole("button")).toHaveCount(5);
  return section;
}

async function pick(page: Page, section: ReturnType<Page["getByRole"]>, example: (typeof examples)[number]) {
  const writes: string[] = [];
  const listener = (req: { method(): string; url(): string }) => { if (req.method() === "POST") writes.push(req.url()); };
  page.on("request", listener);
  await section.getByRole("button", { name: new RegExp(`^${example.level}`) }).click();
  expect(writes).toHaveLength(0); // choosing a case only fills the form, never submits
  page.off("request", listener);
}

test("demo3 shows exactly five L1-L5 cases with level and autonomy labels", async ({ page }) => {
  const section = await enter(page);
  const buttons = section.getByRole("group", { name: "选择演示案例" }).getByRole("button");
  for (const [index, example] of examples.entries()) {
    await expect(buttons.nth(index)).toContainText(example.level);
    await expect(buttons.nth(index)).toContainText(example.levelLabel);
    await expect(buttons.nth(index)).toContainText(example.autonomy);
  }
  await expect(section.locator(".office-legacy-examples")).toHaveCount(1); // older cases stay folded away
});

for (const example of examples) {
  test(`level case ${example.level} ${example.id}: real policy level and human controls`, async ({ page }) => {
    const section = await enter(page);
    await pick(page, section, example);
    await expect(section.getByLabel("事项标题")).toHaveValue(example.input.title);
    await expect(section.locator(".office-example-boundary")).toContainText(example.boundary);
    await expect(section.locator(".office-example-boundary")).toContainText("为什么是这一档");
    for (const source of example.sources) await expect(section.locator(".office-example-boundary")).toContainText(source);

    const response = page.waitForResponse(r => r.url().endsWith("/v1/harness/runs") && r.request().method() === "POST");
    await section.getByRole("button", { name: "启动 Control Loop", exact: true }).click();
    const action = (await (await response).json()).run.office_action;
    // What the UI promised must be what the fixed-rule policy actually decided.
    expect(action.risk_level).toBe(example.level);
    expect(action.autonomy_level).toBe(example.autonomy);
    expect(action.status).toBe(example.expected_status);
    expect(action.external_action).toBe("none");
    expect(action.model_called).toBe(false);
    await expect(section.locator(".office-action-state")).toContainText(example.level);

    if (example.level === "L1") {
      await section.getByRole("button", { name: "撤销此次整理" }).click();
      await expect(section.locator(".office-action-preview pre")).toHaveText(example.input.content);
    } else if (example.level === "L2") {
      // Bound to the real library file: the excerpt comes from the document, not from typed text.
      expect(action.input.source_ref).toMatch(/^forte-[0-9a-f]{16}$/);
      expect(action.source_label).toBe("文本评测岗位JD.docx");
      await expect(section.locator(".office-source-review pre")).toContainText("必要项");
      await expect(section.getByRole("button", { name: /确认登记|确认创建/ })).toHaveCount(0);
    } else if (example.level === "L3") {
      await expect(section.getByRole("button", { name: /确认创建/ })).toBeVisible();
      await section.getByRole("button", { name: "确认创建测试任务" }).click();
      await expect(section.locator(".office-action-receipt")).toContainText("未通知真实同事");
    } else if (example.level === "L4") {
      const confirm = section.getByRole("button", { name: "确认登记测试发件" });
      await expect(confirm).toBeDisabled();
      const boxes = await section.getByRole("checkbox").all();
      expect(boxes).toHaveLength(3); // recipient, content, impact
      for (const box of boxes) await box.check();
      await confirm.click();
      await expect(section.locator(".office-action-receipt")).toContainText("未发送真实邮件");
    } else {
      await expect(section.getByRole("button", { name: /确认登记|确认创建/ })).toHaveCount(0);
      await expect(section.locator(".office-action-receipt")).toHaveCount(0);
      await expect(section.getByRole("button", { name: "下载人工处理说明" })).toBeVisible();
    }
  });
}

test("level cases fit mobile and never overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const section = await enter(page);
  await section.getByRole("button", { name: /^L4/ }).click();
  await expect(section.getByLabel("办理对象")).toHaveValue("wang-delivery");
  await section.getByRole("button", { name: /^L1/ }).click();
  await expect(section.getByLabel("办理对象")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../../outputs/demo3-examples-20261026/levels-mobile.png", fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await section.getByRole("button", { name: /^L5/ }).click();
  await page.screenshot({ path: "../../outputs/demo3-examples-20261026/levels-desktop.png", fullPage: true });
});
