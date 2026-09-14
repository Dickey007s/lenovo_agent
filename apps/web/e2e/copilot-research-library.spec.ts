import { expect, test } from "@playwright/test";
import path from "node:path";
import { pathToFileURL } from "node:url";
import library from "../../../docs/reports/copilot-research-library-20260911/sources.json";

const reportDir = path.resolve(process.cwd(), "../../docs/reports/copilot-research-library-20260911");

for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
  test(`research library stays usable offline at ${viewport.width}px`, async ({ page, context }) => {
    const failures: string[] = [];
    const networkRequests: string[] = [];
    page.on("pageerror", error => failures.push(error.message));
    page.on("console", message => { if (message.type() === "error") failures.push(message.text()); });
    page.on("request", request => { if (/^https?:/.test(request.url())) networkRequests.push(request.url()); });
    await context.setOffline(true);
    await page.setViewportSize(viewport);
    await page.goto(pathToFileURL(path.join(reportDir, "index.html")).href);
    await expect(page.getByRole("heading", { name: "人机共驾研究库", exact: true })).toBeVisible();
    await expect(page.locator(".source-row")).toHaveCount(library.sources.length);
    const noOverflow = async () => {
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    };
    await noOverflow();
    const capture = async (name: string) => {
      if (process.env.CAPTURE_RESEARCH_SCREENSHOTS === "1") {
        await page.screenshot({ path: path.join(reportDir, "screenshots", `${name}-${viewport.width}.png`) });
      }
    };
    await capture("library");
    await page.getByRole("combobox", { name: "类型", exact: true }).selectOption("paper");
    await expect(page.locator(".source-row")).toHaveCount(library.sources.filter(source => source.type === "paper").length);
    await page.getByRole("searchbox").fill("unlikely-no-result-9f2b");
    await expect(page.getByRole("heading", { name: "没有匹配的来源" })).toBeVisible();
    await page.locator("#empty-reset").click();
    await expect(page.locator(".source-row")).toHaveCount(library.sources.length);
    await page.getByRole("searchbox").fill("LangGraph");
    await expect(page.locator(".source-row")).toHaveCount(1);
    const trigger = page.getByRole("button", { name: "研究详情" });
    await trigger.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText("未在本仓库安装或实测此框架");
    await expect(dialog.getByRole("link", { name: "打开原始来源" })).toHaveAttribute("href", library.sources.find(source => source.id === "S10")!.url);
    expect(await dialog.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true);
    const bounds = await dialog.boundingBox();
    expect(bounds!.x).toBeGreaterThanOrEqual(0);
    expect(bounds!.x + bounds!.width).toBeLessThanOrEqual(viewport.width + 1);
    await capture("detail");
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
    await expect(trigger).toBeFocused();
    await page.getByRole("tab", { name: "来源库", exact: true }).press("ArrowRight");
    await expect(page.getByRole("tab", { name: "规则与 Demo" })).toHaveAttribute("aria-selected", "true");
    await page.getByRole("combobox", { name: "适用 Demo", exact: true }).selectOption("Demo3");
    await expect(page.locator(".rule-row")).toHaveCount(library.rules.filter(rule => rule.demos.includes("Demo3")).length);
    expect(await page.locator(".flow-band small").evaluateAll(elements => elements.every(el =>
      el.getBoundingClientRect().height <= Number.parseFloat(getComputedStyle(el).lineHeight) * 1.5
    ))).toBe(true);
    await noOverflow();
    await capture("mapping");
    await page.getByRole("tab", { name: "核验账本" }).click();
    await expect(page.locator("#ledger tr")).toHaveCount(library.sources.length);
    await expect(page.locator("#limitations")).toContainText("PDF");
    await noOverflow();
    await capture("ledger");
    expect(networkRequests).toEqual([]);
    expect(failures).toEqual([]);
    await context.setOffline(false);
  });
}
