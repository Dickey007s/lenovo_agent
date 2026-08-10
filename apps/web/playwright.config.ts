import { defineConfig, devices } from "@playwright/test";

const apiUrl = "http://localhost:8011";
const webUrl = "http://localhost:3011";

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
        `pnpm exec cross-env API_CORS_ORIGINS=${webUrl} LANGGRAPH_CHECKPOINT_DSN= DATABASE_DSN= ` +
        "uv --directory ../.. run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8011",
      url: `${apiUrl}/v1/health`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command:
        `pnpm exec cross-env NEXT_PUBLIC_API_BASE_URL=${apiUrl} ` +
        "next dev --hostname 127.0.0.1 --port 3011",
      url: webUrl,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
