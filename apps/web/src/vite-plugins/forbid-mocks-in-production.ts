import type { Plugin } from "vite";

/**
 * Fail closed: production builds must never embed MSW via VITE_ENABLE_MOCKS=true.
 * Preview/dev may set the flag; Vercel Production must not.
 */
export function forbidMocksInProduction(): Plugin {
  return {
    name: "forbid-vite-enable-mocks-in-production",
    configResolved(config) {
      if (config.command !== "build") {
        return;
      }
      if (config.mode !== "production") {
        return;
      }
      const fromEnv = config.env.VITE_ENABLE_MOCKS ?? process.env.VITE_ENABLE_MOCKS;
      if (fromEnv === "true") {
        throw new Error(
          "VITE_ENABLE_MOCKS=true is forbidden for production builds. " +
            "Set it only on Vercel Preview (or local dev), never Production.",
        );
      }
    },
  };
}
