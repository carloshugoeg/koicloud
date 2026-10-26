/**
 * Fails if plans UI hard-codes backup retention copy instead of PlanOut.
 */
import { describe, expect, it } from "vitest";

const FORBIDDEN: { pattern: RegExp; reason: string }[] = [
  { pattern: /Diarios \(7 días\)/, reason: "hard-coded Micro retention" },
  { pattern: /Diarios \(30 días\)/, reason: "hard-coded Pro retention" },
];

const productionSources = import.meta.glob(["../features/plans/plans-page.tsx"], {
  eager: true,
  query: "?raw",
  import: "default",
}) as Record<string, string>;

describe("no hard-coded backup retention in plans page", () => {
  it("requires backup_retention_days and forbids fixed Diarios literals", () => {
    const entries = Object.entries(productionSources);
    expect(entries.length).toBeGreaterThan(0);

    const violations: string[] = [];
    for (const [relPath, text] of entries) {
      if (typeof text !== "string") {
        continue;
      }
      if (!text.includes("backup_retention_days")) {
        violations.push(`${relPath}: missing backup_retention_days`);
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
