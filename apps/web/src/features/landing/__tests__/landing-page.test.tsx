import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { appRoutes } from "@/app/router";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const API_ROOT = "*/api/v1";

function renderLandingRoute() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: 0 },
    },
  });
  const router = createMemoryRouter(appRoutes, {
    initialEntries: ["/"],
  });

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );

  return router;
}

describe("E2-01 Landing pública y catálogo", () => {
  it("renders the hero section with heading, facts, and animated pond", () => {
    renderLandingRoute();

    expect(screen.getAllByText("KoiCloud").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByRole("link", { name: "Iniciar sesión" })).toHaveAttribute(
      "href",
      "/login",
    );
    expect(screen.getAllByRole("link", { name: "Crear cuenta" })[0]).toHaveAttribute(
      "href",
      "/register",
    );

    expect(
      screen.getByRole("heading", {
        name: "Tu Postgres en línea antes de que se enfríe el café.",
      }),
    ).toBeInTheDocument();

    expect(screen.getByText("~40 s")).toBeInTheDocument();
    expect(screen.getByText("de crear a conectar")).toBeInTheDocument();
    expect(screen.getByText("superficies: web, CLI, MCP")).toBeInTheDocument();
    expect(screen.getAllByText("USD 5").length).toBeGreaterThanOrEqual(1);

    expect(screen.getByRole("img", { name: "Estanque de peces koi" })).toBeInTheDocument();
    expect(screen.getByTestId("landing-sticky-cta")).toBeInTheDocument();
  });

  it("renders plan cards from GET /plans (MSW) with Micro highlighted", async () => {
    const customPlans = [
      {
        ...fixtures.plans[0],
        description: "MSW Sandbox custom",
        max_ponds: 2,
        max_storage_gb: 3,
      },
      {
        ...fixtures.plans[1],
        description: "MSW Micro custom",
        max_ponds: 4,
        max_storage_gb: 8,
        price_monthly_usd: 7,
      },
      {
        ...fixtures.plans[2],
        description: "MSW Pro custom",
        max_ponds: 12,
        max_storage_gb: 30,
      },
    ];

    server.use(
      http.get(`${API_ROOT}/plans`, () => {
        return HttpResponse.json({ plans: customPlans, next_cursor: null });
      }),
    );

    renderLandingRoute();

    expect(await screen.findByRole("heading", { name: "Sandbox" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Micro" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro" })).toBeInTheDocument();

    expect(screen.getByText("MSW Sandbox custom")).toBeInTheDocument();
    expect(screen.getByText("MSW Micro custom")).toBeInTheDocument();
    expect(screen.getByText("MSW Pro custom")).toBeInTheDocument();
    expect(screen.getByText("2 ponds · 3 GB")).toBeInTheDocument();
    expect(screen.getByText("4 ponds · 8 GB")).toBeInTheDocument();
    expect(screen.getByText("12 ponds · 30 GB")).toBeInTheDocument();
    expect(screen.getByText("$7")).toBeInTheDocument();
    expect(screen.getByText("Pospago")).toBeInTheDocument();
    expect(screen.queryByText(/0\.02/)).not.toBeInTheDocument();
    expect(screen.getByText("Recomendado")).toBeInTheDocument();

    expect(screen.getByText(/Pago simulado\./i)).toBeInTheDocument();
    expect(
      screen.getByText(/Este es un proyecto académico: no se realiza ningún cobro real/i),
    ).toBeInTheDocument();
  });

  it("shows error state when GET /plans fails", async () => {
    server.use(
      http.get(`${API_ROOT}/plans`, () => {
        return HttpResponse.json(
          { code: "internal_error", message: "boom", request_id: "req_landing_plans" },
          { status: 500 },
        );
      }),
    );

    renderLandingRoute();

    expect(await screen.findByTestId("landing-plans-error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
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
