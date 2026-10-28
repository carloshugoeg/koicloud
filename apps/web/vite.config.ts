import path from "node:path";
import { fileURLToPath, URL } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { forbidMocksInProduction } from "./src/vite-plugins/forbid-mocks-in-production";

const rootDir = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [react(), forbidMocksInProduction()],
  resolve: {
    alias: {
      "@": path.join(rootDir, "src"),
    },
  },
  server: {
    port: 4173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    css: true,
    coverage: {
      reporter: ["text", "html"],
    },
  },
});
