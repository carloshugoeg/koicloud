import { execFileSync } from "node:child_process";
import { existsSync, readdirSync, statSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const cacheDir = join(root, ".chrome-for-testing");

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

function findUnder(dir, depth = 0) {
  if (depth > 6 || !existsSync(dir)) return null;
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    let st;
    try {
      st = statSync(full);
    } catch {
      continue;
    }
    if (
      st.isFile() &&
      (name === "chrome" || name === "chrome.exe" || name === "Google Chrome for Testing")
    ) {
      return full;
    }
    if (st.isDirectory()) {
      const found = findUnder(full, depth + 1);
      if (found) return found;
    }
  }
  return null;
}

export function resolveChromeExecutable() {
  for (const candidate of SYSTEM_CANDIDATES) {
    if (candidate && existsSync(candidate)) return candidate;
  }

  const cached = findUnder(cacheDir);
  if (cached) return cached;

  console.log("No system Chrome found; installing Chrome for Testing into", cacheDir);
  execFileSync(
    "pnpm",
    ["dlx", "@puppeteer/browsers", "install", "chrome@stable", `--path=${cacheDir}`],
    { cwd: root, stdio: "inherit", env: process.env },
  );

  const installed = findUnder(cacheDir);
  if (!installed) {
    throw new Error("Chrome for Testing install finished but no chrome binary was found.");
  }
  return installed;
}
