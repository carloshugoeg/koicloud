import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

function renderBilling() {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/billing"] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

describe("W2-15 Historial de suscripciones", () => {
  it("lists the subscription with a readable phase and no invoice column", async () => {
    renderBilling();

    expect(await screen.findByRole("heading", { name: "Suscripciones" })).toBeInTheDocument();
    const subscription = fixtures.subscriptionResponse.subscription;
    const row = await screen.findByTestId(`subscription-${subscription.id}`);
    expect(within(row).getByText(subscription.plan_id)).toBeInTheDocument();
    expect(within(row).getByText("Activa")).toBeInTheDocument();
    expect(within(row).getByText("2026-09-22 → 2026-10-22")).toBeInTheDocument();
    expect(within(row).getByRole("button", { name: "Cancelar al corte" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Factura" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("suspended-banner")).not.toBeInTheDocument();
  });

  it("marks cancel_at_period_end after canceling at period end", async () => {
    const user = userEvent.setup();
    renderBilling();

    await user.click(await screen.findByRole("button", { name: "Cancelar al corte" }));
    const dialog = await screen.findByTestId("cancel-subscription-dialog");
    await user.click(within(dialog).getByRole("button", { name: "Cancelar al corte" }));

    const row = await screen.findByTestId(`subscription-${fixtures.subscriptionResponse.subscription.id}`);
    await waitFor(() => {
      expect(within(row).getByText("Se cancela al corte")).toBeInTheDocument();
    });
    expect(within(row).queryByRole("button", { name: "Cancelar al corte" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("cancel-subscription-dialog")).not.toBeInTheDocument();
  });

  it("shows an empty history without a pond", async () => {
    server.use(
      http.get("*/api/v1/subscriptions", () => {
        return HttpResponse.json({ subscriptions: [], next_cursor: null });
      }),
    );
    renderBilling();

    expect(await screen.findByTestId("billing-empty")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver planes" })).toHaveAttribute("href", "/app/planes");
    expect(screen.queryByTestId("data-state-empty")).not.toBeInTheDocument();
  });

  it("shows the catalog message when the list fails", async () => {
    server.use(
      http.get("*/api/v1/subscriptions", () => {
        return HttpResponse.json(
          { code: "internal_error", message: "raw", request_id: "req_subs" },
          { status: 500 },
        );
      }),
    );
    renderBilling();

    expect(await screen.findByTestId("billing-error", {}, { timeout: 5000 })).toBeInTheDocument();
    expect(screen.getByText("Algo salió mal. Revisá los logs e intentá de nuevo.")).toBeInTheDocument();
    expect(screen.queryByText("raw")).not.toBeInTheDocument();
  });
});
