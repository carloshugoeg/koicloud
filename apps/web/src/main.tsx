import "@fontsource-variable/fraunces";
import "@fontsource/instrument-sans/400.css";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { createAppRouter } from "@/app/router";
import "./index.css";

async function enableMocks() {
  // Keep the dynamic import reachable so Vite does not tree-shake MSW when the
  // build-time env flag is unset. Production hosts never match `-git-…vercel.app`.
  const envFlag = String(import.meta.env.VITE_ENABLE_MOCKS ?? "") === "true";
  const vercelPreviewHost =
    typeof window !== "undefined" &&
    /-git-[\w.-]+\.vercel\.app$/i.test(window.location.hostname);
  if (envFlag || vercelPreviewHost) {
    const { worker } = await import("@/mocks/browser");
    await worker.start({ onUnhandledRequest: "bypass" });
  }
}

async function bootstrap() {
  await enableMocks();

  const container = document.getElementById("root");
  if (!container) {
    throw new Error("No se encontró el contenedor principal.");
  }

  createRoot(container).render(
    <StrictMode>
      <AppProviders>
        <RouterProvider router={createAppRouter()} />
      </AppProviders>
    </StrictMode>,
  );
}

void bootstrap();
