import { defineConfig } from "@playwright/test";
import base from "./playwright.integration.config";

export default defineConfig({
  ...base,
  testMatch: ["harness-workbench.spec.ts", "october-copilot.spec.ts"],
  grep: /\[october\]|\[recording\] 03/,
  timeout: 240_000,
  outputDir: "../../outputs/copilot-delivery-20261019/browser",
  use: { ...base.use, headless: false, launchOptions: { slowMo: 160 } },
});
