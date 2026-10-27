import { defineConfig, devices } from "@playwright/test";

// Defaults keep the original ports; override when something else (e.g. WeChat on macOS) already owns 8011.
const apiPort = process.env.E2E_API_PORT ?? "8011";
const webPort = process.env.E2E_WEB_PORT ?? "3011";
// 127.0.0.1, not localhost: Node resolves localhost to ::1 first, but uvicorn/next bind IPv4 only here.
const host = process.env.E2E_HOST ?? "localhost";
const apiUrl = `http://${host}:${apiPort}`;
const webUrl = `http://${host}:${webPort}`;

export default defineConfig({
  testDir: "./e2e",
  outputDir: "../../outputs/playwright",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: "list",
  use: {
    baseURL: webUrl,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "system-browser",
      use: {
        ...devices["Desktop Chrome"],
        // The local machine has Edge but no Chrome installation. Override with
        // PLAYWRIGHT_CHANNEL=chrome where system Chrome is available.
        channel: process.env.PLAYWRIGHT_CHANNEL ?? "msedge",
      },
    },
  ],
  webServer: [
    {
      command:
        `pnpm exec cross-env API_CORS_ORIGINS=${webUrl} LANGGRAPH_CHECKPOINT_DSN= DATABASE_DSN= LLM_BASE_URL= LLM_API_KEY= ` +
        `uv --directory ../.. run uvicorn services.api.app.main:app --host 127.0.0.1 --port ${apiPort}`,
      url: `${apiUrl}/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        `pnpm exec cross-env NEXT_DIST_DIR=.next-playwright NEXT_PUBLIC_API_BASE_URL=${apiUrl} ` +
        `next dev --hostname 127.0.0.1 --port ${webPort}`,
      url: webUrl,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
