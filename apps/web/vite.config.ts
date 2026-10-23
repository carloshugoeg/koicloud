import { existsSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const require = createRequire(import.meta.url);
const vitePrerender = require("vite-plugin-prerender") as typeof import("vite-plugin-prerender").default & {
  PuppeteerRenderer: new (options?: Record<string, unknown>) => unknown;
};
const PuppeteerRenderer = vitePrerender.PuppeteerRenderer;

const rootDir = fileURLToPath(new URL(".", import.meta.url));

function resolveChromeForPrerender(): string | undefined {
  const candidates = [
    process.env.PUPPETEER_EXECUTABLE_PATH,
    process.env.CHROME_PATH,
    "/usr/bin/google-chrome-stable",
    "/usr/bin/google-chrome",
    "/usr/local/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
  ].filter(Boolean) as string[];
  return candidates.find((candidate) => existsSync(candidate));
}

export default defineConfig(({ command }) => {
  const chromePath = resolveChromeForPrerender();

  return {
    plugins: [
      react(),
      ...(command === "build"
        ? [
            vitePrerender({
              staticDir: path.join(rootDir, "dist"),
              routes: ["/"],
              renderer: new PuppeteerRenderer({
                headless: true,
                renderAfterElementExists: "[data-landing-prerender]",
                args: [
                  "--no-sandbox",
                  "--disable-setuid-sandbox",
                  "--disable-dev-shm-usage",
                ],
                // Bundled puppeteer@1 (via vite-plugin-prerender) ships Chromium too
                // old for this Vite 8 / React 19 bundle. Prefer a modern system Chrome.
                ...(chromePath ? { executablePath: chromePath } : {}),
              }),
              postProcess(renderedRoute: { html: string }) {
                if (!renderedRoute.html.includes("Tu Postgres en línea")) {
                  throw new Error(
                    "Prerender of / did not include landing hero content in HTML.",
                  );
                }
                return renderedRoute;
              },
            }),
          ]
        : []),
    ],
    resolve: {
      alias: {
        "@": fileURLToPath(new URL("./src", import.meta.url)),
      },
    },
    server: {
      port: 4173,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      globals: true,
      css: true,
      coverage: {
        reporter: ["text", "html"],
      },
    },
  };
});
