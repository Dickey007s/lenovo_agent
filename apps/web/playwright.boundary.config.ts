import { defineConfig, devices } from '@playwright/test';

// Standalone file-only report checks: no API, web server or provider process.
export default defineConfig({
  testDir:'./e2e',
  testMatch:'copilot-boundary-design.spec.ts',
  outputDir:'../../outputs/playwright-boundary',
  workers:1,
  timeout:60_000,
  reporter:'list',
  use:{...devices['Desktop Chrome'],channel:process.env.PLAYWRIGHT_CHANNEL??'msedge',trace:'retain-on-failure',screenshot:'only-on-failure'},
});
