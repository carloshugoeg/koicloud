import { rmSync } from "node:fs";
import path from "node:path";
import type { Plugin, ResolvedConfig } from "vite";

function mocksRequested(config: ResolvedConfig) {
  return (config.env.VITE_ENABLE_MOCKS ?? process.env.VITE_ENABLE_MOCKS) === "true";
}

/**
 * Fail closed when MSW would ship to real production.
 * Vercel Preview also runs `vite build` (mode=production) with VITE_ENABLE_MOCKS;
 * only VERCEL_ENV=production (or a non-Vercel local production build) is forbidden.
 * A production build that does not ask for mocks also drops public/mockServiceWorker.js.
 */
export function forbidMocksInProduction(): Plugin {
  let resolved: ResolvedConfig | undefined;

  return {
    name: "forbid-vite-enable-mocks-in-production",
    configResolved(config) {
      resolved = config;
      if (config.command !== "build") {
        return;
      }

      const mocks = mocksRequested(config);
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
    closeBundle() {
      if (!resolved || resolved.command !== "build" || mocksRequested(resolved)) {
        return;
      }
      rmSync(path.resolve(resolved.root, resolved.build.outDir, "mockServiceWorker.js"), {
        force: true,
      });
    },
  };
}
