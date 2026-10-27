/**
 * Copy the preview-only sim into apps/web/api/_koi_sim for the Vercel Python
 * function. Canonical source stays in e2e/sim-backend/. Never runs in prod logic;
 * the handler gates on VERCEL_ENV === "preview".
 */
import { cpSync, mkdirSync, rmSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(webRoot, "..", "..");
const source = join(repoRoot, "e2e", "sim-backend");
const dest = join(webRoot, "api", "_koi_sim");

if (!existsSync(join(source, "app.py")) || !existsSync(join(source, "state.py"))) {
  console.error("prepare-preview-sim: missing e2e/sim-backend/{app,state}.py");
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(join(source, "app.py"), join(dest, "app.py"));
cpSync(join(source, "state.py"), join(dest, "state.py"));
console.log("prepare-preview-sim: copied e2e/sim-backend → api/_koi_sim");
