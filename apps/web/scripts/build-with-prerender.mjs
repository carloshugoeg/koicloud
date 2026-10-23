import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { resolveChromeExecutable } from "./resolve-chrome.mjs";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const chrome = resolveChromeExecutable();

const env = { ...process.env };
if (chrome) {
  env.PUPPETEER_EXECUTABLE_PATH = chrome;
  console.log("Prerender Chrome:", chrome);
} else {
  env.KOICLOUD_SKIP_PRERENDER_PLUGIN = "1";
  console.log(
    "No system Chrome; vite-plugin-prerender skipped (fragment fallback after build).",
  );
}

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

let verify = spawnSync("node", ["scripts/verify-prerender.mjs"], {
  cwd: root,
  env,
  stdio: "inherit",
});

if (verify.status !== 0) {
  console.log("Puppeteer prerender missing; injecting committed landing fragment.");
  const inject = spawnSync("node", ["scripts/inject-prerender-fallback.mjs"], {
    cwd: root,
    env,
    stdio: "inherit",
  });
  if (inject.status !== 0) process.exit(inject.status ?? 1);

  verify = spawnSync("node", ["scripts/verify-prerender.mjs"], {
    cwd: root,
    env,
    stdio: "inherit",
  });
}

process.exit(verify.status ?? 1);
