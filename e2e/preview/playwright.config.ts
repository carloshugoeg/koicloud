import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "@playwright/test";

const previewRoot = path.dirname(fileURLToPath(import.meta.url));

const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ??
  "https://koicloud-web-git-w2-14-post-merge-hugos-projects-3379fa36.vercel.app";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./tests/global-setup.ts",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["json", { outputFile: path.join(previewRoot, "artifacts/playwright-report.json") }],
  ],
  use: {
    baseURL,
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        viewport: { width: 1440, height: 900 },
      },
    },
  ],
});
