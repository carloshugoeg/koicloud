import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";

function renderLandingRoute() {
  const router = createMemoryRouter(appRoutes, {
    initialEntries: ["/"],
  });

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );

  return router;
}

describe("E2-01 Landing pública y catálogo", () => {
  it("renders the hero section with heading, facts, and animated pond", () => {
    renderLandingRoute();

    // Brand y links
    expect(screen.getAllByText("KoiCloud").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: "Iniciar sesión" })).toHaveAttribute("href", "/login");
    expect(screen.getAllByRole("link", { name: "Crear cuenta" })[0]).toHaveAttribute("href", "/register");

    // Hero title & facts
    expect(
      screen.getByRole("heading", {
        name: "Tu Postgres en línea antes de que se enfríe el café.",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("~40 s")).toBeInTheDocument();
    expect(screen.getByText("de crear a conectar")).toBeInTheDocument();
    expect(screen.getByText("superficies: web, CLI, MCP")).toBeInTheDocument();
    expect(screen.getAllByText("USD 5").length).toBeGreaterThanOrEqual(1);

    // Estanque
    expect(screen.getByRole("img", { name: "Estanque de peces koi" })).toBeInTheDocument();
  });

  it("renders the three plans, highlighting Micro with Recomendado and simulated payment notice", async () => {
    renderLandingRoute();

    // Plan headings
    expect(await screen.findByRole("heading", { name: "Sandbox" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Micro" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro" })).toBeInTheDocument();

    // Micro badge
    expect(screen.getByText("Recomendado")).toBeInTheDocument();

    // Simulated payment notice
    expect(screen.getByText(/Pago simulado\./i)).toBeInTheDocument();
    expect(
      screen.getByText(/Este es un proyecto académico: no se realiza ningún cobro real/i),
    ).toBeInTheDocument();
  });

  it("renders the 'Cómo funciona' three-step guide", () => {
    renderLandingRoute();

    expect(screen.getByRole("heading", { name: "Contratas un plan" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Creas tu pond" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Te conectas" })).toBeInTheDocument();

    expect(screen.getByText("Paso 1")).toBeInTheDocument();
    expect(screen.getByText("Paso 2")).toBeInTheDocument();
    expect(screen.getByText("Paso 3")).toBeInTheDocument();
  });
});
