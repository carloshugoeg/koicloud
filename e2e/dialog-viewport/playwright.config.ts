import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const root = path.dirname(fileURLToPath(import.meta.url));
const webRoot = path.resolve(root, "../../apps/web");
const port = 5174;

if (port === 5173) {
  throw new Error("dialog-viewport must not use port 5173");
}

const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL,
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  webServer: {
    command: `pnpm exec vite --host 127.0.0.1 --port ${port} --strictPort`,
    cwd: webRoot,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ...process.env,
      VITE_ENABLE_MOCKS: "false",
      VITE_API_BASE_URL: "",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
