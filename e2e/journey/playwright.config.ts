import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const root = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(root, "../../apps/web");

export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  webServer: [
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5173 --strictPort",
      cwd: webRoot,
      url: "http://127.0.0.1:5173",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_ENABLE_MOCKS: "false",
        VITE_API_BASE_URL: "",
      },
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5174 --strictPort",
      cwd: webRoot,
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        ...process.env,
        VITE_ENABLE_MOCKS: "true",
        VITE_API_BASE_URL: "",
      },
    },
  ],
  projects: [
    {
      name: "chromium",
      testIgnore: "**/msw-session.spec.ts",
      use: {
        browserName: "chromium",
        baseURL: "http://127.0.0.1:5173",
        viewport: { width: 1440, height: 900 },
      },
    },
    {
      name: "msw",
      testMatch: "**/msw-session.spec.ts",
      use: {
        browserName: "chromium",
        baseURL: "http://127.0.0.1:5174",
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
