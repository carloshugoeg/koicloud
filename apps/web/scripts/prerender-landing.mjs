import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { createServer } from "vite";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const htmlPath = join(root, "dist", "index.html");

const vite = await createServer({
  root,
  configFile: join(root, "vite.config.ts"),
  server: { middlewareMode: true },
  appType: "custom",
});

try {
  const { renderLandingHtml } = await vite.ssrLoadModule(
    "/src/features/landing/render-landing-html.tsx",
  );
  const fragment = renderLandingHtml();

  if (!fragment.includes("Tu Postgres en línea") || !fragment.includes("data-landing-prerender")) {
    throw new Error("renderLandingHtml() did not produce required landing markup.");
  }

  const html = readFileSync(htmlPath, "utf8");
  const replaced = html.replace(
    /<div id="root">[\s\S]*?<\/div>(?=\s*(?:<script|<\/body>))/i,
    `<div id="root">${fragment}</div>`,
  );

  if (replaced === html) {
    throw new Error("Could not locate #root in dist/index.html for landing prerender inject.");
  }

  writeFileSync(htmlPath, replaced);
  console.log("CA8 prerender injected from LandingPage SSR into", htmlPath);
} finally {
  await vite.close();
}
