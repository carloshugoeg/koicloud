import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { confirmSearch } from "@/features/confirm/proposal";
import { demoUser } from "@/mocks/fixtures";
import { server } from "@/mocks/server";
import { useAuthStore } from "@/lib/auth-store";

const expiresAt = new Date(Date.now() + 5 * 60_000);

function renderConfirm(search: string) {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });

  const router = createMemoryRouter(appRoutes, {
    initialEntries: [`/app/confirm?${search}`],
  });

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );

  return router;
}

describe("confirm dialog", () => {
  it("confirms a valid deep link and shows a notice on /app", async () => {
    const user = userEvent.setup();
    const search = confirmSearch({
      token: "conf_create_pond_demo" as never,
      summary: "Se creará el pond 'inventario-demo'.",
      expiresAt,
    });
    const router = renderConfirm(search);

    expect(await screen.findByTestId("confirm-summary")).toHaveTextContent("inventario-demo");
    await user.click(screen.getByTestId("confirm-submit"));

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/app");
    });
    expect(await screen.findByTestId("app-notice")).toHaveTextContent("Acción confirmada.");
  });

  it("handles 404 confirmation_not_found", async () => {
    const user = userEvent.setup();
    const search = confirmSearch({
      token: "conf_not_found" as never,
      summary: "Propuesta de prueba.",
      expiresAt,
    });
    const router = renderConfirm(search);

    await user.click(await screen.findByTestId("confirm-submit"));
    expect(await screen.findByText("No encontramos la confirmación solicitada.")).toBeInTheDocument();
    expect(screen.getByText("confirmation_not_found")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-submit")).toBeDisabled();
    expect(router.state.location.pathname).toBe("/app/confirm");
  });

  it("handles 410 confirmation_expired", async () => {
    const user = userEvent.setup();
    const expired = confirmSearch({
      token: "conf_expired" as never,
      summary: "Propuesta vencida.",
      expiresAt,
    });
    renderConfirm(expired);
    await user.click(await screen.findByTestId("confirm-submit"));
    expect(await screen.findByText("La confirmación ya expiró.")).toBeInTheDocument();
    expect(screen.getByText("confirmation_expired")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-submit")).toBeDisabled();
  });

  it("handles 409 confirmation_action_mismatch", async () => {
    const user = userEvent.setup();
    const search = confirmSearch({
      token: "conf_mismatch" as never,
      summary: "Propuesta distinta.",
      expiresAt,
    });
    renderConfirm(search);
    await user.click(await screen.findByTestId("confirm-submit"));
    expect(await screen.findByText("La confirmación no corresponde a esta acción.")).toBeInTheDocument();
    expect(screen.getByText("confirmation_action_mismatch")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-submit")).toBeDisabled();
  });

  it("shows empty state when the query is missing", async () => {
    useAuthStore.setState({
      session: {
        accessToken: "access_demo_token",
        refreshToken: "refresh_demo_token",
        user: demoUser,
      },
    });
    const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/confirm"] });
    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );
    expect(await screen.findByTestId("confirm-invalid")).toBeInTheDocument();
  });

  it("discards without executing", async () => {
    const user = userEvent.setup();
    let deleted = false;
    server.use(
      http.delete("*/api/v1/confirm/:token", () => {
        deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const search = confirmSearch({
      token: "conf_create_pond_demo" as never,
      summary: "Se creará el pond 'inventario-demo'.",
      expiresAt,
    });
    const router = renderConfirm(search);
    await user.click(await screen.findByTestId("confirm-discard"));
    await waitFor(() => {
      expect(deleted).toBe(true);
      expect(router.state.location.pathname).toBe("/app");
    });
    expect(await screen.findByTestId("app-notice")).toHaveTextContent("Propuesta descartada");
  });

  it("opens the same summary from the Spanish alias", async () => {
    const search = confirmSearch({
      token: "conf_create_pond_demo" as never,
      summary: "Se creará el pond 'inventario-demo'.",
      expiresAt,
    });
    useAuthStore.setState({
      session: {
        accessToken: "access_demo_token",
        refreshToken: "refresh_demo_token",
        user: demoUser,
      },
    });
    const router = createMemoryRouter(appRoutes, {
      initialEntries: [`/app/confirmacion?${search}`],
    });
    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );
    expect(await screen.findByTestId("confirm-summary")).toHaveTextContent("inventario-demo");
    expect(router.state.location.pathname).toBe("/app/confirm");
  });
});
