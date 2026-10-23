import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const htmlPath = join(root, "dist", "index.html");
const fragmentPath = join(root, "scripts", "landing-prerender-fragment.html");

const html = readFileSync(htmlPath, "utf8");
const fragment = readFileSync(fragmentPath, "utf8");

if (!fragment.includes("Tu Postgres en línea") || !fragment.includes("data-landing-prerender")) {
  throw new Error("landing-prerender-fragment.html is missing required landing markup.");
}

if (html.includes("data-landing-prerender") && html.includes("Tu Postgres en línea")) {
  console.log("Prerender already present; fallback inject skipped.");
  process.exit(0);
}

if (!html.includes('<div id="root"></div>') && !html.includes('<div id="root">\n')) {
  // root may already have whitespace children
}

const replaced = html.replace(
  /<div id="root">[\s\S]*?<\/div>(?=\s*(?:<script|<\/body>))/i,
  `<div id="root">${fragment}</div>`,
);

if (replaced === html) {
  throw new Error("Could not locate #root in dist/index.html for fallback prerender inject.");
}

writeFileSync(htmlPath, replaced);
console.log("CA8 fallback prerender injected into", htmlPath);
