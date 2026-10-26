import { expect, test, type Page } from "@playwright/test";
import examples from "../app/office-action-examples.json";

async function enter(page: Page, id: string) {
  await page.goto("/");
  if ((page.viewportSize()?.width ?? 1280) <= 1000) await page.getByRole("button", { name: "展开工作区导航" }).click();
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "Demo 3 · 人机共驾", exact: true }).click();
  const close = page.getByRole("button", { name: "收起工作区导航" });
  if (await close.isVisible()) await close.click();
  const section = page.getByRole("region", { name: "单步事项" });
  const picker = section.locator(".office-action-examples");
  await expect(picker).not.toHaveAttribute("open");
  await picker.locator("summary").click();
  const writes: string[] = [];
  page.on("request", req => { if (req.method() === "POST") writes.push(req.url()); });
  await section.getByLabel("选择演示案例").selectOption(id);
  expect(writes).toHaveLength(0);
  return section;
}

for (const example of examples) {
  test(`preset ${example.id}: real API boundary and human controls`, async ({ page }) => {
    const section = await enter(page, example.id);
    await expect(section.getByLabel("事项标题")).toHaveValue(example.input.title);
    await expect(section.getByLabel("事项内容", { exact: true })).toHaveValue(example.input.content);
    const response = page.waitForResponse(r => r.url().endsWith("/v1/harness/runs") && r.request().method() === "POST");
    await section.getByRole("button", { name: "开始办理", exact: true }).click();
    const action = (await (await response).json()).run.office_action;
    expect(action.status).toBe(example.expected_status);
    expect(action.external_action).toBe("none");
    expect(action.model_called).toBe(false);
    await expect(section.getByLabel("选择演示案例")).toHaveCount(0);
    if (action.status === "needs_input") {
      await expect(section.getByRole("button", { name: /确认创建/ })).toHaveCount(0);
      if (!example.input.target) await section.getByLabel("办理对象").selectOption("wang-delivery");
      if (!example.input.due_date) await section.getByLabel("截止日期").fill("2026-11-06");
      await section.getByRole("button", { name: "更新内容并重新核对" }).click();
      await section.getByRole("button", { name: "确认创建测试任务" }).click();
      await expect(section.locator(".office-action-receipt")).toContainText("未通知真实同事");
    } else if (action.status === "denied") {
      await expect(section.getByRole("button", { name: /确认登记|确认创建/ })).toHaveCount(0);
      await expect(section.locator(".office-action-receipt")).toHaveCount(0);
      await expect(section.getByRole("button", { name: "下载人工处理说明" })).toBeVisible();
    } else if (action.status === "awaiting_confirmation") {
      if (example.input.operation === "send_message") {
        const confirm = section.getByRole("button", { name: "确认登记测试发件" });
        await expect(confirm).toBeDisabled();
        for (const box of await section.getByRole("checkbox").all()) await box.check();
        if (example.id === "recheck-change") {
          await section.getByRole("button", { name: "修改内容", exact: true }).click();
          await section.getByLabel("事项内容", { exact: true }).fill("您好，建议周五下午评审，具体时间待双方确认。");
          await section.getByRole("button", { name: "更新内容并重新核对" }).click();
          await expect(confirm).toBeDisabled();
          for (const box of await section.getByRole("checkbox").all()) { await expect(box).not.toBeChecked(); await box.check(); }
          await expect(section.locator(".office-recheck-notice")).toContainText("旧核对已失效");
        }
        await confirm.click();
        await expect(section.locator(".office-action-receipt")).toContainText("未发送真实邮件");
      } else {
        await section.getByRole("button", { name: "确认创建测试任务" }).click();
        await expect(section.locator(".office-action-receipt")).toContainText("未通知真实同事");
      }
    } else if (action.status === "awaiting_decision") {
      await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
      for (const radio of await section.getByRole("radio").all()) await expect(radio).not.toBeChecked();
      if (example.id === "defer-judgment") {
        await section.getByRole("button", { name: "暂时无法判断，稍后处理" }).click();
        await expect(section.locator(".office-action-state")).toContainText("已暂缓");
        await section.getByRole("button", { name: "办理另一件事项" }).click();
        await section.getByRole("button", { name: "开始办理" }).click();
        await expect(section.locator(".office-action-receipt")).toBeVisible();
        await section.locator(".office-recent > summary").click();
        await section.getByRole("button", { name: new RegExp(example.input.title) }).click();
        await expect(section.locator(".office-action-state")).toContainText("已暂缓");
        await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
      } else {
        await section.getByRole("radio", { name: "采用材料 A" }).check();
        await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
        await section.getByLabel("判断理由").fill("当前按已发布邮件准备；仍需负责人确认是否有正式更正。");
        await section.getByRole("button", { name: "记录这次判断" }).click();
        await expect(section.locator(".office-decision-result")).toContainText("不是业务审批");
      }
    } else if (action.status === "draft_ready") {
      expect(action.source_excerpt).toBe(example.input.content);
      await expect(section.locator(".office-source-review pre")).toHaveText(example.input.content);
      if (example.id === "excerpt-edit") {
        await section.getByRole("button", { name: "编辑这份草稿" }).click();
        await section.getByLabel("编辑摘录草稿").fill("人工修订：联调结果仍待复核，不作为对外发布结论。");
        await section.getByRole("button", { name: "保存草稿修改" }).click();
        await expect(section.locator(".office-source-review pre")).toHaveText(example.input.content);
        await section.locator(".office-action-history > summary").click();
        await section.getByRole("button", { name: "取回第 1 版内容" }).click();
        await section.getByRole("button", { name: "保存为新的草稿版本" }).click();
        await expect(section.locator(".office-action-state")).toContainText("第 3 版");
      }
      await expect(section.getByRole("button", { name: /确认登记|确认创建/ })).toHaveCount(0);
    } else {
      await section.getByRole("button", { name: "撤销此次整理" }).click();
      await expect(section.locator(".office-action-preview pre")).toHaveText(example.input.content);
    }
  });
}

test("preset changes clear irrelevant input and fit mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const section = await enter(page, "conflicting-deadline");
  await section.getByLabel("选择演示案例").selectOption("outbound-review");
  await expect(section.getByLabel("第二份材料")).toHaveCount(0);
  await section.getByLabel("选择演示案例").selectOption("tidy-notes");
  await expect(section.getByLabel("办理对象")).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({ path: "../../outputs/demo3-examples-20261026/mobile.png", fullPage: true });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await section.getByLabel("选择演示案例").selectOption("conflicting-deadline");
  await page.screenshot({ path: "../../outputs/demo3-examples-20261026/desktop.png", fullPage: true });
});
