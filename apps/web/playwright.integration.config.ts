import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig({
  ...base,
  webServer: [
    {
      command: '".venv/Scripts/python.exe" -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8011',
      cwd: "../..",
      env: { API_CORS_ORIGINS: "http://localhost:3011", STATE_STORE_MODE: "memory", DATABASE_DSN: "", LANGGRAPH_CHECKPOINT_DSN: "", LLM_API_KEY: "", LLM_BASE_URL: "" },
      url: "http://localhost:8011/v1/health",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: 'node node_modules/next/dist/bin/next dev --webpack --hostname 127.0.0.1 --port 3011',
      env: { NEXT_DIST_DIR: ".next-playwright", NEXT_PUBLIC_API_BASE_URL: "http://localhost:8011" },
      url: "http://localhost:3011",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
