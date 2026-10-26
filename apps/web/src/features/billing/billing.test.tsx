import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const ACTIVE_ID = fixtures.subscriptionList[0].id;
const EXPIRED_ID = fixtures.subscriptionList[1].id;
const CUTOFF_LABEL = "22 oct 2026, 02:00 p. m.";

function renderAt(entry: string) {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });

  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: 0 },
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("W2-15 Historial de suscripciones", () => {
  it("lists plan, phase, period, and cancel only for an active subscription", async () => {
    renderAt("/app/billing");

    expect(await screen.findByRole("heading", { name: "Facturación" })).toBeInTheDocument();
    const activeRow = await screen.findByTestId(`subscription-row-${ACTIVE_ID}`);
    expect(within(activeRow).getByText("Micro")).toBeInTheDocument();
    expect(within(activeRow).getByText("Activa")).toBeInTheDocument();
    expect(within(activeRow).getByText("●")).toBeInTheDocument();
    expect(within(activeRow).getByRole("button", { name: "Cancelar al corte" })).toBeInTheDocument();

    const expiredRow = screen.getByTestId(`subscription-row-${EXPIRED_ID}`);
    expect(within(expiredRow).getByText("Sandbox")).toBeInTheDocument();
    expect(within(expiredRow).getByText("Vencida")).toBeInTheDocument();
    expect(within(expiredRow).queryByRole("button", { name: "Cancelar al corte" })).not.toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Factura" })).not.toBeInTheDocument();
  });

  it("confirms the cutoff, then shows the scheduled-cancel badge", async () => {
    const user = userEvent.setup();
    renderAt("/app/billing");

    const activeRow = await screen.findByTestId(`subscription-row-${ACTIVE_ID}`);
    await user.click(within(activeRow).getByRole("button", { name: "Cancelar al corte" }));

    const dialog = await screen.findByTestId("cancel-subscription-dialog");
    expect(within(dialog).getByText(/plan Micro sigue activo/i)).toBeInTheDocument();
    expect(screen.getByTestId("cancel-period-end")).toHaveTextContent(CUTOFF_LABEL);
    expect(within(activeRow).getByText("Activa")).toBeInTheDocument();

    await user.click(within(dialog).getByRole("button", { name: "Confirmar cancelación al corte" }));

    await waitFor(() => {
      expect(screen.queryByTestId("cancel-subscription-dialog")).not.toBeInTheDocument();
    });
    const updated = screen.getByTestId(`subscription-phase-${ACTIVE_ID}`);
    expect(updated).toHaveTextContent("Se cancela al corte");
    expect(updated).toHaveTextContent("◐");
    expect(updated).not.toHaveTextContent("Cancelada");
    expect(
      within(screen.getByTestId(`subscription-row-${ACTIVE_ID}`)).queryByRole("button", {
        name: "Cancelar al corte",
      }),
    ).not.toBeInTheDocument();
  });

  it("shows the empty history without a pond", async () => {
    server.use(
      http.get("*/api/v1/subscriptions", () =>
        HttpResponse.json({ subscriptions: [], next_cursor: null }),
      ),
    );
    renderAt("/app/billing");

    const empty = await screen.findByTestId("billing-empty");
    expect(within(empty).getByRole("heading", { name: "Sin suscripciones" })).toBeInTheDocument();
    expect(within(empty).queryByRole("img")).not.toBeInTheDocument();
    expect(empty.querySelector(".koi, .pond-water-panel")).toBeNull();
    expect(within(empty).getByRole("link", { name: "Ver planes" })).toHaveAttribute("href", "/app/planes");
  });

  it("shows an error with retry when the list fails", async () => {
    server.use(
      http.get("*/api/v1/subscriptions", () =>
        HttpResponse.json(
          { code: "internal_error", message: "boom", request_id: "req_subs" },
          { status: 500 },
        ),
      ),
    );
    renderAt("/app/billing");

    expect(await screen.findByTestId("billing-error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
    expect(screen.getByText("Algo salió mal. Revisá los logs e intentá de nuevo.")).toBeInTheDocument();
  });

  it("keeps usage and invoices on /app/uso", async () => {
    renderAt("/app/uso?month=2026-09");

    expect(await screen.findByRole("heading", { name: "Septiembre 2026" })).toBeInTheDocument();
    expect(await screen.findByText("KOI-202609-0001")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancelar al corte" })).not.toBeInTheDocument();
  });

  it("shows the loading label before rows arrive", async () => {
    server.use(
      http.get("*/api/v1/subscriptions", async () => {
        await delay(200);
        return HttpResponse.json({
          subscriptions: fixtures.subscriptionList,
          next_cursor: null,
        });
      }),
    );
    renderAt("/app/billing");

    expect(screen.getByTestId("billing-loading")).toHaveTextContent("Cargando suscripciones…");
    expect(await screen.findByTestId(`subscription-row-${ACTIVE_ID}`)).toBeInTheDocument();
  });
});
