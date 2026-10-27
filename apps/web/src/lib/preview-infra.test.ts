import vercel from "../../vercel.json";
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

type VercelConfig = {
  rewrites: Array<{ source: string; destination: string }>;
};

describe("preview infra (vercel + theme)", () => {
  it("routes /api/v1 ahead of the SPA app.html fallback", () => {
    const config = vercel as VercelConfig;
    const sources = config.rewrites.map((r) => r.source);
    const apiIdx = sources.findIndex((s) => s.includes("/api/v1"));
    const spaIdx = sources.findIndex((s) => s.includes("(?!assets/"));
    expect(apiIdx).toBeGreaterThanOrEqual(0);
    expect(spaIdx).toBeGreaterThan(apiIdx);
    expect(sources[spaIdx]).toMatch(/api\//);
    expect(config.rewrites[apiIdx]?.destination).toMatch(/\/api\?koi_path=/);
  });

  it("declares self-contained @theme token utilities for preview CSS", () => {
    const css = readFileSync(
      join(dirname(fileURLToPath(import.meta.url)), "..", "index.css"),
      "utf8",
    );
    expect(css).toMatch(/@theme\s+inline\s*\{/);
    for (const token of [
      "--color-marigold",
      "--color-turquoise-700",
      "--color-bone-raised",
      "--color-warn",
      "--color-bone",
    ]) {
      expect(css).toContain(token);
    }
    expect(css).toMatch(/\.shadow-dialog\s*\{/);
    // Do not ship #137's shadcn semantic aliases here (self-contained token set).
    expect(css).not.toContain("--color-primary:");
  });
});
