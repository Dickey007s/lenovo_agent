import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beginRecording, guardRealRecording, recordingRoot } from "./recording-support";

test("[october] complete handoff and explicit judgment", async ({ browser }) => {
  const { page, mark, finish } = await beginRecording(browser, "04-judgment", "本次真实 API · 合成材料 · 不调用模型或外部服务");
  const guard = await guardRealRecording(page, true);
  await page.goto("/");
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  const section = page.getByRole("region", { name: "单步事项" });
  await section.getByLabel("事项类型").selectOption("compare_materials");
  await section.getByLabel("事项标题").fill("评审材料截止日期核对");
  await section.getByLabel("事项内容", { exact: true }).fill("项目邮件：评审材料须在周三提交。邮件尚未撤回。");
  await section.getByLabel("第二份材料").fill("会议记录：建议改为周五提交，尚未取得项目负责人确认。");
  await mark("输入与任务", "两份材料日期不同。任务是保留两份来源，让人决定本次采用口径，而非让模型猜答案。", 8);
  await section.getByRole("button", { name: "开始办理" }).click();
  await expect(section.getByRole("group", { name: "材料对照" })).toBeVisible();
  for (const radio of await section.getByRole("radio").all()) await expect(radio).not.toBeChecked();
  await section.locator(".office-comparison").first().scrollIntoViewIfNeeded();
  await mark("系统的边界", "系统保存并展示两份材料，不预选答案。确认需要人的选择与理由；不知道时可以暂缓。", 8);
  await section.getByRole("button", { name: "暂时无法判断，稍后处理" }).click();
  const downloadPromise = page.waitForEvent("download");
  await section.getByRole("button", { name: "下载人工处理说明" }).click();
  const download = await downloadPromise;
  const handoffPath = resolve(recordingRoot, "receipts", "handoff.txt");
  await download.saveAs(handoffPath);
  const handoff = readFileSync(handoffPath, "utf8");
  for (const text of ["需要谁决定什么", "周三", "周五", "最近 20 个 Run", "未通知他人", "已暂缓"]) expect(handoff).toContain(text);
  await mark("暂缓与交接", "暂缓保留现场。交接说明包含原文、版本、暂停原因、待决定事项和返回方式，不会通知或代替审批。", 9);
  await page.reload();
  await expect(section.locator(".office-control-context")).toContainText("已暂缓");
  await section.getByRole("radio", { name: "采用材料 A" }).check();
  await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
  await section.getByLabel("判断理由").fill("仍采用未撤回的正式邮件日期周三；周五只是建议，需要负责人另行确认。");
  await section.locator(".office-decision").scrollIntoViewIfNeeded();
  await mark("人工决定", "重新打开同一事项，选择材料 A 并说明理由。没有理由不能记录，暂缓也不会被当成同意。", 9);
  const saved = page.waitForResponse(r => r.url().endsWith("/action-controls") && r.request().method() === "POST");
  await section.getByRole("button", { name: "记录这次判断" }).click();
  const action = (await (await saved).json()).run.office_action;
  expect(action.status).toBe("decided");
  expect(action.model_called).toBe(false);
  expect(action.external_action).toBe("none");
  await section.locator(".office-decision-result").scrollIntoViewIfNeeded();
  await mark("输出与完成范围", "输出是人工判断记录，不是业务批准。原材料不变，也没有自动发邮件或启动下一项任务。", 9);
  expect(guard.blocked).toEqual([]);
  await finish({ source: "real isolated API", state: action.status, externalAction: action.external_action, modelCalled: false, handoffVerified: true, reloadVerified: true });
});

test("[october] missing fields and read-only handoff export", async ({ page }) => {
  await guardRealRecording(page, true);
  await page.goto("/");
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  const section = page.getByRole("region", { name: "单步事项" });
  await section.getByLabel("事项类型").selectOption("create_task");
  await section.getByRole("button", { name: "开始办理" }).click();
  await expect(section).toContainText("还需要补齐以下信息，尚未创建或发送");
  const writes: string[] = [];
  page.on("request", request => { if (request.method() === "POST") writes.push(request.url()); });
  const downloaded = page.waitForEvent("download");
  await section.getByRole("button", { name: "下载人工处理说明" }).click();
  const download = await downloaded;
  const body = readFileSync((await download.path())!, "utf8");
  expect(body).toContain("请事项发起人补齐");
  expect(body).toContain("截止日期：未指定");
  expect(writes).toHaveLength(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
});

test("handoff guards: unknown outcome and editing cannot export stale context", async ({ page }) => {
  const guard = await guardRealRecording(page, true);
  await page.goto("/");
  await page.getByRole("button", { name: "新建任务", exact: true }).click();
  await page.getByRole("button", { name: "办理事项", exact: true }).click();
  const section = page.getByRole("region", { name: "单步事项" });
  await section.getByLabel("事项类型").selectOption("create_task");
  await section.getByLabel("办理对象").selectOption("wang-engineering");
  await section.getByLabel("截止日期").fill("2026-10-23");
  await section.getByRole("button", { name: "开始办理" }).click();
  await section.getByRole("button", { name: "修改内容", exact: true }).click();
  await expect(section.getByRole("button", { name: "下载人工处理说明" })).toBeDisabled();
  await section.getByRole("button", { name: "放弃修改", exact: true }).click();
  await expect(section.getByRole("button", { name: "下载人工处理说明" })).toBeEnabled();
  await page.route("**/action-controls", async route => {
    await route.fetch({ headers: { ...route.request().headers(), "x-user-id": guard.owner } });
    await route.abort("failed");
  });
  await section.getByRole("button", { name: "确认创建测试任务" }).click();
  await expect(section.getByRole("alert")).toContainText("提交结果尚未确认");
  // SSE may already show the terminal receipt while the POST result is unknown.
  // In that case the pending-item export disappears instead of staying disabled.
  await expect(section.getByRole("button", { name: "下载人工处理说明" }).and(page.locator(":enabled"))).toHaveCount(0);
});
