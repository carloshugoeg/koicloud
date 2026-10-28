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
  // Preview-only: set VITE_ENABLE_MOCKS=true in Vercel Preview env (never Production).
  // Do not key off hostname — git-main aliases would match a `-git-` regex.
  if (import.meta.env.VITE_ENABLE_MOCKS === "true") {
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
