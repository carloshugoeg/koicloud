import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));
const htmlPath = join(root, "..", "dist", "index.html");
const html = readFileSync(htmlPath, "utf8");

const required = [
  "Tu Postgres en línea antes de que se enfríe el café.",
  "Cómo funciona",
  "Crear cuenta",
  "data-landing-prerender",
];

const missing = required.filter((snippet) => !html.includes(snippet));
if (missing.length > 0) {
  console.error("CA8 prerender check failed. Missing in dist/index.html:");
  for (const snippet of missing) {
    console.error(`  - ${snippet}`);
  }
  process.exit(1);
}

console.log("CA8 prerender OK:", htmlPath, `(${html.length} bytes)`);
