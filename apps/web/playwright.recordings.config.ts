import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["harness-workbench.spec.ts", "office-recordings.spec.ts"],
  grep: /\[recording\]/,
  outputDir: "../../outputs/office-recordings-20261008/tests",
  workers: 1,
  fullyParallel: false,
  timeout: 180_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  use: {
    actionTimeout: 15_000,
    baseURL: "http://localhost:3000",
    channel: "msedge",
    headless: false,
    launchOptions: { slowMo: 180, args: ["--start-maximized"] },
    trace: "retain-on-failure",
  },
});
