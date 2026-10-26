/**
 * Fails if a catalog price literal sneaks back into production UI source.
 * Test files and MSW fixtures are excluded — they mirror API data.
 */
import { describe, expect, it } from "vitest";

const FORBIDDEN: { pattern: RegExp; reason: string }[] = [
  { pattern: /USD\s*0\.02/, reason: "hard-coded Pro hourly USD 0.02" },
  { pattern: /\$0\.02/, reason: "hard-coded $0.02" },
  { pattern: /0\.02\s*·\s*h/, reason: "hard-coded 0.02·h" },
  { pattern: /USD\s*5(?![\d.])/, reason: "hard-coded USD 5" },
  { pattern: /\$5(?![\d.])/, reason: "hard-coded $5" },
  { pattern: /4\.4643/, reason: "hard-coded checkout subtotal" },
  { pattern: /0\.5357/, reason: "hard-coded checkout IVA" },
];

const productionSources = import.meta.glob(["../**/*.{ts,tsx}"], {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

function isExcluded(relPath: string): boolean {
  if (relPath.includes(".test.")) {
    return true;
  }
  if (relPath.includes("/mocks/")) {
    return true;
  }
  if (relPath.includes("/__tests__/")) {
    return true;
  }
  if (relPath.endsWith("/api/schema.d.ts")) {
    return true;
  }
  return false;
}

describe("no hard-coded catalog prices in web UI", () => {
  it("scans production source for forbidden price literals", () => {
    const violations: string[] = [];

    for (const [relPath, text] of Object.entries(productionSources)) {
      if (isExcluded(relPath) || typeof text !== "string") {
        continue;
      }
      for (const { pattern, reason } of FORBIDDEN) {
        if (pattern.test(text)) {
          violations.push(`${relPath}: ${reason}`);
        }
      }
    }

    expect(violations, violations.join("\n")).toEqual([]);
  });
});
