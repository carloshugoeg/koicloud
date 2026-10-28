import { afterEach, describe, expect, it } from "vitest";
import { forbidMocksInProduction } from "./forbid-mocks-in-production";

type Resolved = {
  command: string;
  mode: string;
  env: Record<string, string>;
};

function run(config: Resolved) {
  const plugin = forbidMocksInProduction();
  const hook = plugin.configResolved;
  (hook as (c: Resolved) => void)(config);
}

describe("forbidMocksInProduction", () => {
  const prev = {
    VERCEL: process.env.VERCEL,
    VERCEL_ENV: process.env.VERCEL_ENV,
  };

  afterEach(() => {
    if (prev.VERCEL === undefined) delete process.env.VERCEL;
    else process.env.VERCEL = prev.VERCEL;
    if (prev.VERCEL_ENV === undefined) delete process.env.VERCEL_ENV;
    else process.env.VERCEL_ENV = prev.VERCEL_ENV;
  });

  it("throws on local production build with mocks", () => {
    delete process.env.VERCEL;
    delete process.env.VERCEL_ENV;
    expect(() =>
      run({ command: "build", mode: "production", env: { VITE_ENABLE_MOCKS: "true" } }),
    ).toThrow(/VITE_ENABLE_MOCKS/);
  });

  it("throws on Vercel production with mocks", () => {
    process.env.VERCEL = "1";
    process.env.VERCEL_ENV = "production";
    expect(() =>
      run({ command: "build", mode: "production", env: { VITE_ENABLE_MOCKS: "true" } }),
    ).toThrow(/VITE_ENABLE_MOCKS/);
  });

  it("allows Vercel Preview with mocks (vite mode is still production)", () => {
    process.env.VERCEL = "1";
    process.env.VERCEL_ENV = "preview";
    expect(() =>
      run({ command: "build", mode: "production", env: { VITE_ENABLE_MOCKS: "true" } }),
    ).not.toThrow();
  });

  it("allows production build when mocks are unset", () => {
    delete process.env.VERCEL;
    expect(() => run({ command: "build", mode: "production", env: {} })).not.toThrow();
  });
});
