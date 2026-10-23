import { existsSync } from "node:fs";

const SYSTEM_CANDIDATES = [
  process.env.PUPPETEER_EXECUTABLE_PATH,
  process.env.CHROME_PATH,
  "/usr/bin/google-chrome-stable",
  "/usr/bin/google-chrome",
  "/usr/local/bin/google-chrome",
  "/usr/bin/chromium",
  "/usr/bin/chromium-browser",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

/**
 * Resolve a modern system Chrome for vite-plugin-prerender.
 * Does not download Chrome for Testing: Vercel/CI images lack the shared
 * libraries that Chrome for Testing needs (e.g. libnspr4.so).
 */
export function resolveChromeExecutable() {
  for (const candidate of SYSTEM_CANDIDATES) {
    if (candidate && existsSync(candidate)) return candidate;
  }
  return null;
}
