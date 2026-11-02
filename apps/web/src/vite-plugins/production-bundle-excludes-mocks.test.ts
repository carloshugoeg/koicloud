import { spawnSync } from "node:child_process";
import { mkdtempSync, readdirSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const WEB_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

const MARKERS = [
  "mockServiceWorker",
  "setupWorker",
  "msw/browser",
  "isMockedResponse",
  "mora@ejemplo.gt",
  "Operador Demo",
  "inventario-demo",
  "Carlos Hugo Escobar",
  "suspended@koicloud.dev",
  "Usuario Suspendido",
];

function walk(dir: string): string[] {
  const files: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) {
      files.push(...walk(full));
    } else {
      files.push(full);
    }
  }
  return files;
}

describe("production bundle excludes MSW and fixtures", () => {
  it("vite production build ships no mock worker and no fixture accounts", () => {
    const outDir = mkdtempSync(path.join(tmpdir(), "koi-prod-"));
    const env: NodeJS.ProcessEnv = { ...process.env, NODE_ENV: "production" };
    delete env.VITE_ENABLE_MOCKS;

    const result = spawnSync(
      "pnpm",
      ["exec", "vite", "build", "--outDir", outDir, "--emptyOutDir"],
      { cwd: WEB_ROOT, env, encoding: "utf8" },
    );

    expect(result.status, `${result.stdout}\n${result.stderr}`).toBe(0);

    const hits: string[] = [];
    for (const file of walk(outDir)) {
      const rel = path.relative(outDir, file);
      let text: string;
      try {
        text = readFileSync(file, "utf8");
      } catch {
        continue;
      }
      for (const marker of MARKERS) {
        if (rel.includes(marker) || text.includes(marker)) {
          hits.push(`${rel}: ${marker}`);
        }
      }
    }

    expect(hits, hits.join("\n")).toEqual([]);
  }, 180_000);
});
