import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { ERROR_CODES } from "@/lib/errors";

/** Pull CATALOG keys from the preview sim (canonical e2e/sim-backend/state.py). */
function simCatalogCodes(): string[] {
  const path = resolve(__dirname, "../../../../e2e/sim-backend/state.py");
  const source = readFileSync(path, "utf8");
  const start = source.indexOf("CATALOG:");
  if (start < 0) {
    throw new Error(`CATALOG dict not found in ${path}`);
  }
  const brace = source.indexOf("{", start);
  if (brace < 0) {
    throw new Error(`CATALOG opening brace not found in ${path}`);
  }
  let depth = 0;
  let end = -1;
  for (let i = brace; i < source.length; i += 1) {
    const ch = source[i];
    if (ch === "{") depth += 1;
    if (ch === "}") {
      depth -= 1;
      if (depth === 0) {
        end = i;
        break;
      }
    }
  }
  if (end < 0) {
    throw new Error(`CATALOG closing brace not found in ${path}`);
  }
  const body = source.slice(brace + 1, end);
  return [...body.matchAll(/"([a-z_]+)":/g)].map((row) => row[1]);
}

describe("error catalog parity", () => {
  it("matches e2e sim CATALOG keys exactly to lib/errors.ts (no invented MCP variants)", () => {
    const sim = simCatalogCodes().sort();
    const web = [...ERROR_CODES].sort();
    expect(web).toHaveLength(26);
    expect(sim).toEqual(web);
    expect(sim).not.toContain("method_not_found");
    expect(sim).not.toContain("invalid_params");
    expect(sim).not.toContain("backup_not_found");
  });
});
