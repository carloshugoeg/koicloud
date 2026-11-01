import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const journey = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(journey, "../..");
const api = path.join(repo, "apps/api");
const web = path.join(repo, "apps/web");
const homeUv = path.join(process.env.HOME ?? "", ".local/bin/uv");
const uv = fs.existsSync(homeUv) ? homeUv : "uv";

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/sql-console.spec.ts",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  globalSetup: "./sql-global-setup.ts",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "off",
    video: "off",
    screenshot: "off",
    viewport: { width: 1440, height: 900 },
  },
  webServer: [
    {
      command: `${uv} run uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: api,
      url: "http://127.0.0.1:8000/health",
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5173 --strictPort",
      cwd: web,
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_ENABLE_MOCKS: "false",
        VITE_API_BASE_URL: "",
      },
    },
  ],
});
