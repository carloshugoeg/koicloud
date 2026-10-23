import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");

const tsc = spawnSync(
  "pnpm",
  ["exec", "tsc", "-p", "tsconfig.app.json", "--noEmit"],
  { cwd: root, stdio: "inherit" },
);
if (tsc.status !== 0) process.exit(tsc.status ?? 1);

const build = spawnSync("pnpm", ["exec", "vite", "build"], {
  cwd: root,
  stdio: "inherit",
});
if (build.status !== 0) process.exit(build.status ?? 1);

const prerender = spawnSync("node", ["scripts/prerender-landing.mjs"], {
  cwd: root,
  stdio: "inherit",
});
if (prerender.status !== 0) process.exit(prerender.status ?? 1);

const verify = spawnSync("node", ["scripts/verify-prerender.mjs"], {
  cwd: root,
  stdio: "inherit",
});
process.exit(verify.status ?? 1);
