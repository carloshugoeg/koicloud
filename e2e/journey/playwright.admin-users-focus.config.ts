import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const journey = path.dirname(fileURLToPath(import.meta.url));
const web = path.resolve(journey, "../../apps/web");

export default defineConfig({
  testDir: "./tests",
  testMatch: "**/admin-users-focus.spec.ts",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "off",
    video: "off",
    screenshot: "off",
    viewport: { width: 1440, height: 900 },
  },
  webServer: {
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
});
