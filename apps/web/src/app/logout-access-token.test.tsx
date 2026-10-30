import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import type { AuthSession } from "@/lib/auth-store";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const session: AuthSession = {
  accessToken: "access_demo_token",
  refreshToken: "refresh_demo_token",
  user: demoUser,
};

function renderApp() {
  useAuthStore.setState({ session });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app"] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("logout revokes the access token", () => {
  it("asks the API to revoke the access token and returns to login", async () => {
    const user = userEvent.setup();
    const logoutCalls: Array<string | null> = [];
    server.use(
      http.post("*/api/v1/auth/logout", ({ request }) => {
        logoutCalls.push(request.headers.get("Authorization"));
        return new HttpResponse(null, { status: 204 });
      }),
    );

    renderApp();
    expect(await screen.findByRole("heading", { name: "Ponds" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    await waitFor(() => {
      expect(logoutCalls).toEqual(["Bearer access_demo_token"]);
    });
    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar sesión" })).not.toBeInTheDocument();
  });

  it("shows login when a later request rejects the access token", async () => {
    server.use(
      http.get("*/api/v1/ponds", () =>
        HttpResponse.json(
          { code: "token_invalid", message: "El token enviado no es válido." },
          { status: 401 },
        ),
      ),
    );

    renderApp();

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cerrar sesión" })).not.toBeInTheDocument();
  });
});
