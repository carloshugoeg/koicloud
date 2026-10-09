import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import type { Pond } from "@/api/hooks/ponds";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });
}

function renderPonds(queryClient?: QueryClient) {
  seedSession();
  const client =
    queryClient ??
    new QueryClient({
      defaultOptions: {
        queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
        mutations: { retry: 0 },
      },
    });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/ponds"] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return client;
}

describe("W2-04 Dashboard de ponds", () => {
  it("renders four KPI, pond grid cells, and hides host:port when not running", async () => {
    renderPonds();

    const dashboard = await screen.findByTestId("ponds-dashboard");
    expect(within(dashboard).getByText("Ponds en línea")).toBeInTheDocument();
    expect(within(dashboard).getByText("Almacenamiento")).toBeInTheDocument();
    expect(within(dashboard).getAllByText("Plan").length).toBeGreaterThanOrEqual(1);
    expect(within(dashboard).getAllByText("Uso del mes").length).toBeGreaterThanOrEqual(1);

    const grid = within(dashboard).getByRole("list", { name: "Rejilla del estanque" });
    expect(within(grid).getAllByRole("listitem")).toHaveLength(fixtures.ponds.length);

    const runningRow = screen.getByText("inventario-demo").closest("tr");
    expect(runningRow).not.toBeNull();
    expect(within(runningRow as HTMLElement).getByText(/puerto 15007/)).toBeInTheDocument();

    const provisioningRow = screen.getByText("reportes-demo").closest("tr");
    expect(provisioningRow).not.toBeNull();
    expect(within(provisioningRow as HTMLElement).getByText("—")).toBeInTheDocument();
  });

  it("shows empty state with CTA to create a pond", async () => {
    server.use(
      http.get("*/api/v1/ponds", () => HttpResponse.json({ ponds: [], next_cursor: null })),
    );
    renderPonds();

    expect(await screen.findByTestId("ponds-empty")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crear pond" })).toHaveAttribute(
      "href",
      "/app/ponds/new",
    );
  });

  it("shows error state with Reintentar", async () => {
    server.use(
      http.get("*/api/v1/ponds", () =>
        HttpResponse.json(
          { code: "internal_error", message: "boom", request_id: "req_ponds" },
          { status: 500 },
        ),
      ),
    );
    renderPonds();

    expect(await screen.findByTestId("ponds-error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });

  it("flashes a row for 600ms when observed_state changes without reordering", async () => {
    let ponds: Pond[] = fixtures.ponds;
    server.use(
      http.get("*/api/v1/ponds", () =>
        HttpResponse.json({ ponds, next_cursor: null }),
      ),
    );

    const client = renderPonds();
    expect(await screen.findByText("inventario-demo")).toBeInTheDocument();

    const namesBefore = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.querySelector("td")?.textContent);

    ponds = fixtures.ponds.map((pond, index) =>
      index === 0
        ? { ...pond, observed_state: "failed", healthy: false, last_error: "driver timeout" }
        : pond,
    );
    await client.invalidateQueries({ queryKey: ["ponds"] });

    await waitFor(() => {
      const row = screen.getByText("inventario-demo").closest("tr");
      expect(row).toHaveAttribute("data-flash", "true");
    });

    const namesAfter = screen
      .getAllByRole("row")
      .slice(1)
      .map((row) => row.querySelector("td")?.textContent);
    expect(namesAfter).toEqual(namesBefore);

    await waitFor(
      () => {
        const row = screen.getByText("inventario-demo").closest("tr");
        expect(row).toHaveAttribute("data-flash", "false");
      },
      { timeout: 1_200 },
    );
  });
});
