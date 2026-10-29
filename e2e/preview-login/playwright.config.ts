import { defineConfig } from "@playwright/test";

const DEFAULT_PREVIEW_ORIGIN =
  "https://koicloud-web-git-w1-preview-login-gate-hugos-projects-3379fa36.vercel.app";

function previewBaseURL(): string {
  const raw = (
    process.env.PLAYWRIGHT_BASE_URL ||
    process.env.KOI_PUBLIC_BASE_URL ||
    DEFAULT_PREVIEW_ORIGIN
  ).trim();

  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    throw new Error(
      "Set PLAYWRIGHT_BASE_URL or KOI_PUBLIC_BASE_URL to an absolute Vercel Preview URL. The value was not a URL.",
    );
  }

  const host = url.hostname.toLowerCase();
  const local =
    host === "localhost" || host === "127.0.0.1" || host === "::1" || host === "0.0.0.0";
  if (local) {
    throw new Error(
      "Refusing localhost. Set PLAYWRIGHT_BASE_URL or KOI_PUBLIC_BASE_URL to the Vercel Preview origin.",
    );
  }

  if (url.protocol !== "https:" && url.protocol !== "http:") {
    throw new Error("The Preview base URL must use http or https.");
  }

  return url.origin;
}

export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  expect: { timeout: 20_000 },
  fullyParallel: true,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: previewBaseURL(),
    trace: "off",
    video: "off",
    screenshot: "off",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
