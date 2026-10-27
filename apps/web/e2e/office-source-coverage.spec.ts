import { expect, test } from "@playwright/test";

for (const width of [1920, 390]) {
  test(`original workspace can inspect the last of 212 actual source rows at ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 1200 });
    const posts: string[] = [];
    const errors: string[] = [];
    page.on("request", request => { if (request.method() === "POST") posts.push(request.url()); });
    page.on("pageerror", error => errors.push(error.message));
    await page.goto("/");
    await page.getByRole("button", { name: "新建任务", exact: true }).click();
    await page.getByRole("textbox", { name: "搜索文件或目录" }).fill("用户交互行为日志.xlsx");
    await page.locator(".workspace-tree-file").filter({ hasText: "用户交互行为日志.xlsx" }).click();
    const rows = page.locator(".table-preview tbody tr");
    await expect(rows).toHaveCount(212);
    await rows.last().scrollIntoViewIfNeeded();
    await expect(rows.last()).toBeVisible();
    await expect(rows.last().locator(".row-number")).toHaveText("213");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
    expect(overflow).toBe(false);
    expect(posts).toEqual([]);
    expect(errors).toEqual([]);
    await page.screenshot({ path: `../../outputs/ui-focus-20261008/screenshots/source-tail-${width}.png` });
  });
}
