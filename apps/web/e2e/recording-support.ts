import { expect, type Browser, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

export const recordingRoot = process.env.OFFICE_RECORDING_ROOT || resolve(process.cwd(), "../../docs/reports/office-agent-recordings-20261008");

export async function beginRecording(browser: Browser, id: string, provenance: string) {
  mkdirSync(resolve(recordingRoot, "raw"), { recursive: true });
  mkdirSync(resolve(recordingRoot, "stills"), { recursive: true });
  mkdirSync(resolve(recordingRoot, "receipts"), { recursive: true });
  const context = await browser.newContext({
    baseURL: process.env.OFFICE_RECORDING_URL || "http://localhost:3000", viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1, locale: "zh-CN", serviceWorkers: "block",
    recordVideo: { dir: resolve(recordingRoot, "raw"), size: { width: 1920, height: 1080 } },
  });
  const page = await context.newPage();
  const started = Date.now();
  const steps: { time: number; title: string; caption: string; still: string }[] = [];
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  // This is a recording cursor, not a product control or an execution fact.
  await page.addInitScript(() => {
    document.addEventListener("DOMContentLoaded", () => {
      const cursor = document.createElement("div");
      cursor.setAttribute("data-recording-cursor", "");
      cursor.style.cssText = "position:fixed;z-index:2147483647;pointer-events:none;width:24px;height:24px;border:3px solid #0058d8;border-radius:50%;background:#fff8;box-shadow:0 0 0 5px #0058d81f;transform:translate(-50%,-50%);left:-100px;top:-100px";
      document.body.append(cursor);
      document.addEventListener("mousemove", e => { cursor.style.left = `${e.clientX}px`; cursor.style.top = `${e.clientY}px`; });
      document.addEventListener("mousedown", () => { cursor.style.background = "#f5ae38bb"; });
      document.addEventListener("mouseup", () => { cursor.style.background = "#fff8"; });
    });
  });
  async function mark(title: string, caption: string, seconds = 5) {
    const still = `stills/${id}-${String(steps.length + 1).padStart(2, "0")}.png`;
    steps.push({ time: (Date.now() - started) / 1000, title, caption, still });
    await page.screenshot({ path: resolve(recordingRoot, still), fullPage: false });
    await page.waitForTimeout(seconds * 1000);
  }
  async function finish(facts: Record<string, unknown> = {}) {
    expect(errors, "No unhandled page errors during the recording").toEqual([]);
    const video = page.video();
    await context.close();
    await video!.saveAs(resolve(recordingRoot, "raw", `${id}.webm`));
    await video!.delete();
    writeFileSync(resolve(recordingRoot, "raw", `${id}.json`), JSON.stringify({
      id, provenance, recordedAt: new Date().toISOString(), browser: "Microsoft Edge (headed)",
      url: process.env.OFFICE_RECORDING_URL || "http://localhost:3000", viewport: { width: 1920, height: 1080 },
      steps, pageErrors: errors, facts,
    }, null, 2));
  }
  return { page, mark, finish };
}

export async function guardRealRecording(page: Page, allowAction: boolean) {
  const blocked: string[] = [];
  const owner = `office_recordings_${Date.now()}`;
  await page.route("**/v1/**", async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const mutation = !["GET", "HEAD", "OPTIONS"].includes(request.method());
    const safeActionStart = path === "/v1/harness/runs" && request.method() === "POST" && Boolean(request.postDataJSON()?.action);
    const safeActionControl = /\/action-controls$/.test(path) && request.method() === "POST";
    if (mutation && !(allowAction && (safeActionStart || safeActionControl))) {
      blocked.push(path);
      return route.abort("blockedbyclient");
    }
    return route.continue({ headers: { ...request.headers(), "x-user-id": owner } });
  });
  return { blocked, owner };
}
