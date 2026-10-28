/**
 * Vendor apps/api into apps/web/api/_koi_api for the Vercel Python ASGI entry.
 * Canonical source stays in apps/api/. Preview-only; production handler returns 404.
 */
import { cpSync, mkdirSync, rmSync, existsSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoRoot = join(webRoot, "..", "..");
const apiRoot = join(repoRoot, "apps", "api");
const dest = join(webRoot, "api", "_koi_api");

const appPkg = join(apiRoot, "app");
const alembicDir = join(apiRoot, "alembic");
const alembicIni = join(apiRoot, "alembic.ini");

if (!existsSync(join(appPkg, "main.py"))) {
  console.error("prepare-preview-api: missing apps/api/app/main.py");
  process.exit(1);
}
if (!existsSync(alembicDir) || !existsSync(alembicIni)) {
  console.error("prepare-preview-api: missing apps/api alembic assets");
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
cpSync(appPkg, join(dest, "app"), { recursive: true });
cpSync(alembicDir, join(dest, "alembic"), { recursive: true });
cpSync(alembicIni, join(dest, "alembic.ini"));
writeFileSync(join(dest, "README.md"), "Vendored from apps/api at build time. Do not edit.\n");
console.log("prepare-preview-api: copied apps/api → api/_koi_api");
