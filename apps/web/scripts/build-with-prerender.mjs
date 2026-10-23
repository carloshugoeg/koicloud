import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { resolveChromeExecutable } from "./resolve-chrome.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const chrome = resolveChromeExecutable();
console.log("Prerender Chrome:", chrome);

const env = { ...process.env, PUPPETEER_EXECUTABLE_PATH: chrome };

const tsc = spawnSync(
  "pnpm",
  ["exec", "tsc", "-p", "tsconfig.app.json", "--noEmit"],
  { cwd: root, env, stdio: "inherit" },
);
if (tsc.status !== 0) process.exit(tsc.status ?? 1);

const build = spawnSync("pnpm", ["exec", "vite", "build"], {
  cwd: root,
  env,
  stdio: "inherit",
});
if (build.status !== 0) process.exit(build.status ?? 1);

const verify = spawnSync("node", ["scripts/verify-prerender.mjs"], {
  cwd: root,
  env,
  stdio: "inherit",
});
process.exit(verify.status ?? 1);
