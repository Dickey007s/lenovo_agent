import { expect, test } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { beginRecording, guardRealRecording, recordingRoot } from "./recording-support";

if (process.env.RECORD_OFFICE_DEMO === "1") {
  test("[recording] 01 real workspace and task input", async ({ browser }) => {
    const { page, mark, finish } = await beginRecording(browser, "01-workspace", "真实资料库 API · 未启动模型任务");
    const guard = await guardRealRecording(page, false);
    await page.goto("/");
    await page.getByRole("button", { name: "新建任务", exact: true }).click();
    await expect(page.getByRole("textbox", { name: "任务指令" })).toBeVisible();
    await mark("统一入口", "从办公资料库开始：查看材料、输入目标，仍在原系统内。");
    const directory = page.getByRole("button", { name: "资料目录", exact: true });
    if (await directory.getAttribute("aria-expanded") !== "true") await directory.click();
    await page.getByRole("textbox", { name: "搜索文件或目录" }).fill("PRD");
    const file = page.getByRole("treeitem", { name: "打开 产品管理/PRD_v2.5.md", exact: true });
    await expect(file).toBeVisible();
    await mark("找到来源", "输入是现有办公资料；目录搜索只帮助浏览，不改变任务的整库范围。");
    await file.click();
    await expect(page.locator(".file-preview h2")).toHaveText("PRD_v2.5.md");
    await page.locator(".file-preview").scrollIntoViewIfNeeded();
    await mark("安全预览", "打开 PRD 原文预览，先确认材料内容；此处没有修改源文件。", 7);
    await page.getByRole("textbox", { name: "任务指令" }).fill("核对产品上线条件、搜索 Agent 风险和用户交互问题，形成有文件依据的跨职能简报。");
    await mark("写明工作目标", "目标：把多份办公材料整理成可核对的跨职能简报。本段只填写草稿，没有点击启动。", 7);
    expect(guard.blocked).toEqual([]);
    await finish({ source: "live API", modelTaskStarted: false, mutations: 0 });
  });

  test("[recording] 04 real human judgment and persisted receipt", async ({ browser }) => {
    const { page, mark, finish } = await beginRecording(browser, "04-judgment", "真实单步事项 API · 示例材料 · 无模型调用");
    const guard = await guardRealRecording(page, true);
    await page.goto("/");
    await page.getByRole("button", { name: "新建任务", exact: true }).click();
    await page.getByRole("button", { name: "办理事项", exact: true }).click();
    const section = page.getByRole("region", { name: "单步事项" });
    await section.getByLabel("事项类型").selectOption("compare_materials");
    await section.getByLabel("事项标题").fill("评审材料截止日期核对（录屏示例）");
    await mark("输入两份材料", "任务：两份材料的截止日期不同，需要人决定本次草稿采用哪个口径。", 7);
    const started = page.waitForResponse(r => r.url().endsWith("/runs") && r.request().method() === "POST");
    await section.getByRole("button", { name: "开始办理" }).click();
    const startBody = await (await started).json();
    await expect(section.getByRole("group", { name: "材料对照" })).toBeVisible();
    await expect(section.getByRole("radio", { name: "采用材料 A" })).not.toBeChecked();
    await expect(section.getByRole("radio", { name: "采用材料 B" })).not.toBeChecked();
    await mark("在分歧处停下", "系统并排展示材料 A 与 B，不预选答案，也不把材料分歧自动判定成业务事实。", 7);
    await section.getByRole("radio", { name: "采用材料 B" }).check();
    await expect(section.getByRole("button", { name: "记录这次判断" })).toBeDisabled();
    await section.getByLabel("判断理由").fill("录屏示例：本次草稿暂采用较新的会议记录；正式截止日期仍需负责人确认。");
    await mark("人工选择并说明理由", "人工选择材料 B，写下采用理由；没有理由时，提交按钮不可用。", 7);
    const saved = page.waitForResponse(r => r.url().endsWith("/action-controls") && r.request().method() === "POST");
    await section.getByRole("button", { name: "记录这次判断" }).click();
    const body = await (await saved).json();
    const action = body.run.office_action;
    expect(action.status).toBe("decided");
    expect(action.model_called).toBe(false);
    expect(action.external_action).toBe("none");
    await expect(section.locator(".office-decision-result")).toContainText("不是业务审批");
    await mark("输出判断记录", "产出：带选择和理由的人工判断记录。它不是业务审批，也没有发送邮件或改动外部系统。", 7);
    const downloaded = page.waitForEvent("download");
    await section.getByRole("button", { name: "下载本次内容" }).click();
    const download = await downloaded;
    await download.saveAs(resolve(recordingRoot, "receipts", "human-judgment.txt"));
    await page.reload();
    await expect(section.locator(".office-action-state")).toContainText("人工判断已记录");
    await mark("刷新后仍可查看", "刷新页面后再次读到同一判断；已下载对应文本。当前 memory 状态库不支持服务重启后恢复。", 6);
    expect(guard.blocked).toEqual([]);
    const facts = { runId: body.run.run_id, initialStatus: startBody.run.office_action.status,
      finalStatus: action.status, revision: action.revision, modelCalled: action.model_called,
      externalAction: action.external_action, receiptKind: action.receipt.kind,
      reloadVerified: true, downloadedFile: "receipts/human-judgment.txt", stateStore: "memory" };
    writeFileSync(resolve(recordingRoot, "receipts", "human-judgment-facts.json"), JSON.stringify(facts, null, 2));
    await finish(facts);
  });
}
