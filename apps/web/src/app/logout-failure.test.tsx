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

const STILL_ACTIVE = "La sesión puede seguir activa en el servidor.";

function renderApp() {
  useAuthStore.setState({ session });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app"] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("logout when the revoke request fails", () => {
  it("warns, keeps the logged-out marker, and does not reject", async () => {
    window.localStorage.clear();
    const user = userEvent.setup();
    const reasons: string[] = [];
    const onRejection = (event: PromiseRejectionEvent) => {
      reasons.push(String(event.reason));
      event.preventDefault();
    };
    window.addEventListener("unhandledrejection", onRejection);
    const logoutCalls: Array<string | null> = [];
    server.use(
      http.post("*/api/v1/auth/logout", ({ request }) => {
        logoutCalls.push(request.headers.get("Authorization"));
        return HttpResponse.error();
      }),
    );

    renderApp();
    expect(await screen.findByRole("heading", { name: "Ponds" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(await screen.findByText(STILL_ACTIVE)).toBeInTheDocument();
    await waitFor(() => {
      expect(logoutCalls).toEqual(["Bearer access_demo_token"]);
    });
    expect(window.localStorage.getItem("koi_logged_out")).toBe("pending");
    expect(useAuthStore.getState().session).toBeNull();
    await waitFor(() => {
      expect(reasons).toEqual([]);
    });
    window.removeEventListener("unhandledrejection", onRejection);
  });
});
