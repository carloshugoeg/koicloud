import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const indexPath = join(root, "dist", "index.html");
const spaShellPath = join(root, "dist", "app.html");

const indexHtml = readFileSync(indexPath, "utf8");
const spaHtml = readFileSync(spaShellPath, "utf8");

const required = [
  "Tu Postgres en línea antes de que se enfríe el café.",
  "Cómo funciona",
  "Crear cuenta",
  "data-landing-prerender",
];

const missing = required.filter((snippet) => !indexHtml.includes(snippet));
if (missing.length > 0) {
  console.error("CA8 prerender check failed. Missing in dist/index.html:");
  for (const snippet of missing) {
    console.error(`  - ${snippet}`);
  }
  process.exit(1);
}

const emptyRoot =
  /<div id="root">\s*<\/div>/.test(spaHtml) || /<div id="root"><\/div>/.test(spaHtml);
if (!emptyRoot) {
  console.error("CA8 SPA shell check failed: dist/app.html #root must be empty.");
  process.exit(1);
}

if (spaHtml.includes("data-landing-prerender") || spaHtml.includes("Tu Postgres en línea")) {
  console.error(
    "CA8 SPA shell check failed: dist/app.html must not contain landing prerender markup.",
  );
  process.exit(1);
}

console.log("CA8 prerender OK:", indexPath, `(${indexHtml.length} bytes)`);
console.log("CA8 SPA shell OK:", spaShellPath, "(empty #root)");
