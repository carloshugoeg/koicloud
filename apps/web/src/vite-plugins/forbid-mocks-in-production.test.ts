import { describe, expect, it } from "vitest";
import { forbidMocksInProduction } from "./forbid-mocks-in-production";

describe("forbidMocksInProduction", () => {
  it("throws when production build has VITE_ENABLE_MOCKS=true", () => {
    const plugin = forbidMocksInProduction();
    const hook = plugin.configResolved;
    expect(hook).toBeTypeOf("function");
    expect(() =>
      // vitest Plugin types allow sync or async; call as sync guard.
      (hook as (config: { command: string; mode: string; env: Record<string, string> }) => void)({
        command: "build",
        mode: "production",
        env: { VITE_ENABLE_MOCKS: "true" },
      }),
    ).toThrow(/VITE_ENABLE_MOCKS/);
  });

  it("allows production build when mocks are unset", () => {
    const plugin = forbidMocksInProduction();
    const hook = plugin.configResolved;
    expect(() =>
      (hook as (config: { command: string; mode: string; env: Record<string, string> }) => void)({
        command: "build",
        mode: "production",
        env: {},
      }),
    ).not.toThrow();
  });

  it("allows preview/dev even with mocks enabled", () => {
    const plugin = forbidMocksInProduction();
    const hook = plugin.configResolved;
    expect(() =>
      (hook as (config: { command: string; mode: string; env: Record<string, string> }) => void)({
        command: "serve",
        mode: "development",
        env: { VITE_ENABLE_MOCKS: "true" },
      }),
    ).not.toThrow();
  });
});
