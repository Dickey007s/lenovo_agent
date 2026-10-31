import { expect, test } from "@playwright/test";

// Runs against the real API with no model configured (see playwright.config.ts), so only the
// fixed-rule office actions and the rule-based minutes split are exercised: deterministic.
test.describe("workflow tree and minutes intake", () => {
  test("L4 waits for a human; hover shows a summary and details list the eight dimensions", async ({ page }) => {
    await page.setViewportSize({ width: 1500, height: 1000 });
    await page.goto("/");
    await page.getByText("Demo 3 · 人机共驾").first().click();
    await page.getByRole("button", { name: /^L4/ }).click();
    await page.getByRole("button", { name: /启动 Control Loop/ }).click();

    const node = page.locator(".wf-node").first();
    await expect(node).toBeVisible();
    await expect(node).toContainText("L4");
    await expect(page.getByText("任务状态 · 等你确认")).toBeVisible();
    await expect(page.getByRole("button", { name: "中断任务" })).toHaveCount(0); // fixed rules: nothing to interrupt

    await node.hover();
    const card = page.getByRole("tooltip");
    await expect(card).toContainText("AL3");
    await card.getByRole("button", { name: "查看详情" }).click();
    const detail = page.locator(".wf-detail");
    for (const label of ["动作和对象", "数据流向", "状态变化", "影响范围", "恢复能力", "意图和证据", "权限和制度", "使用环境"])
      await expect(detail).toContainText(label);
    await expect(detail).toContainText("决定等级");
    await page.keyboard.press("Escape");
    await expect(page.getByRole("tooltip")).toHaveCount(0);
  });

  test("L5 is shown as rejected and handed to a person", async ({ page }) => {
    await page.goto("/");
    await page.getByText("Demo 3 · 人机共驾").first().click();
    await page.getByRole("button", { name: /^L5/ }).click();
    await page.getByRole("button", { name: /启动 Control Loop/ }).click();
    await expect(page.getByText("任务状态 · 已拒绝，转人工")).toBeVisible();
    await expect(page.locator(".wf-node").first()).toContainText("L5");
  });

  test("meeting minutes are split into to-dos and wait for confirmation in Demo 2", async ({ page }) => {
    await page.goto("/");
    await page.getByText("从会议纪要拆分待办").click();
    await page.getByRole("button", { name: "载入示例纪要" }).click();
    await page.getByRole("button", { name: "拆分待办" }).click();

    await expect(page.getByText(/已从会议纪要拆出 3 项待办/)).toBeVisible();
    await expect(page.locator(".todo-batch textarea")).toHaveCount(3);
    await expect(page.locator(".todo-batch textarea").first()).toHaveValue(/外卖商户BD岗位JD/);
    await expect(page.getByRole("button", { name: "开始全部待办" })).toBeEnabled();
    // Nothing was started by the split itself.
    await expect(page.getByText("0 / 3 项已完成")).toHaveCount(0);
  });
});
