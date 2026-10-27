import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const webRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

describe("preview infra (vercel + theme)", () => {
  it("routes /api/v1 ahead of the SPA app.html fallback", () => {
    const vercel = JSON.parse(readFileSync(join(webRoot, "vercel.json"), "utf8")) as {
      rewrites: Array<{ source: string; destination: string }>;
    };
    const sources = vercel.rewrites.map((r) => r.source);
    const apiIdx = sources.findIndex((s) => s.includes("/api/v1"));
    const spaIdx = sources.findIndex((s) => s.includes("(?!assets/"));
    expect(apiIdx).toBeGreaterThanOrEqual(0);
    expect(spaIdx).toBeGreaterThan(apiIdx);
    expect(sources[spaIdx]).toMatch(/api\//);
    expect(vercel.rewrites[apiIdx]?.destination).toMatch(/\/api\?koi_path=/);
  });

  it("declares Tailwind v4 @theme color tokens so utilities can emit", () => {
    const css = readFileSync(join(webRoot, "src/index.css"), "utf8");
    expect(css).toMatch(/@theme\s+inline\s*\{/);
    for (const token of [
      "--color-marigold",
      "--color-turquoise-700",
      "--color-bone-raised",
      "--color-bone",
    ]) {
      expect(css).toContain(token);
    }
    expect(css).toMatch(/\.shadow-dialog\s*\{/);
  });
});
