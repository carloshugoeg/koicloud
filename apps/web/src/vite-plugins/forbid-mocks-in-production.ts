import type { Plugin } from "vite";

/**
 * Fail closed when MSW would ship to real production.
 * Vercel Preview also runs `vite build` (mode=production) with VITE_ENABLE_MOCKS;
 * only VERCEL_ENV=production (or a non-Vercel local production build) is forbidden.
 */
export function forbidMocksInProduction(): Plugin {
  return {
    name: "forbid-vite-enable-mocks-in-production",
    configResolved(config) {
      if (config.command !== "build") {
        return;
      }

      const mocks =
        (config.env.VITE_ENABLE_MOCKS ?? process.env.VITE_ENABLE_MOCKS) === "true";
      if (!mocks) {
        return;
      }

      const vercelEnv = process.env.VERCEL_ENV;
      const onVercel = process.env.VERCEL === "1";
      const vercelProduction = onVercel && vercelEnv === "production";
      const localProductionBuild = !onVercel && config.mode === "production";

      if (vercelProduction || localProductionBuild) {
        throw new Error(
          "VITE_ENABLE_MOCKS=true is forbidden for production builds. " +
            "Set it only on Vercel Preview (VERCEL_ENV=preview) or local serve, never Production.",
        );
      }
    },
  };
}
