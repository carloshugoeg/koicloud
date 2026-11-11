import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { appRoutes } from "@/app/router";
import { LANDING_WHAT_IS } from "@/features/landing/landing-copy";
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
  it("renders the hero qué-es copy, signup link, thesis, and pond", () => {
    renderLandingRoute();

    expect(screen.getAllByText("KoiCloud").length).toBeGreaterThanOrEqual(1);
    const loginLinks = screen.getAllByRole("link", { name: "Iniciar sesión" });
    expect(loginLinks.length).toBeGreaterThanOrEqual(1);
    expect(loginLinks[0]).toHaveAttribute("href", "/login");

    const heroSignup = screen.getByTestId("landing-hero-signup");
    expect(heroSignup).toHaveAttribute("href", "/register");
    expect(heroSignup).toHaveTextContent("Crear cuenta");

    expect(screen.getByTestId("landing-what-is")).toHaveTextContent(LANDING_WHAT_IS);
    expect(
      screen.getByRole("heading", {
        name: LANDING_WHAT_IS,
      }),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        /Si tu sistema no puede ser operado por agentes hoy en día, nadie lo va a usar\./,
      ),
    ).toBeInTheDocument();

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
        unit_price: 7,
      },
      {
        ...fixtures.plans[2],
        description: "MSW Pro custom",
        max_ponds: 12,
        max_storage_gb: 30,
        unit_price: 0.02,
        billing_model: "hourly" as const,
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
    expect(screen.getByText("2 ponds")).toBeInTheDocument();
    expect(screen.getByText("4 ponds")).toBeInTheDocument();
    expect(screen.getByText("12 ponds")).toBeInTheDocument();
    expect(screen.queryByText(/GB/)).not.toBeInTheDocument();
    expect(screen.getByTestId("landing-plan-price-micro")).toHaveTextContent("$7/mes");
    expect(screen.getByTestId("landing-plan-price-sandbox")).toHaveTextContent("Gratis");
    expect(screen.getByTestId("landing-plan-price-pro")).toHaveTextContent("$0.02/h");
    expect(screen.getByText("Recomendado")).toBeInTheDocument();
    expect(screen.queryByText(/USD \d/)).not.toBeInTheDocument();

    expect(screen.getAllByText(/Pago simulado\./i).length).toBeGreaterThanOrEqual(1);
    expect(
      screen.getAllByText(/Este es un proyecto académico: no se realiza ningún cobro real/i)
        .length,
    ).toBeGreaterThanOrEqual(1);
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

  it("renders how-it-works, agents, surfaces, faq, and final CTA", () => {
    renderLandingRoute();

    expect(screen.getByRole("heading", { name: "Creas tu cuenta" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Levantas un pond" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Operas como quieras" })).toBeInTheDocument();

    expect(screen.getByRole("heading", { name: "Hecho para agentes" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Tres formas de operarlo" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Preguntas honestas" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Abre tu primer pond hoy" })).toBeInTheDocument();
  });
});
