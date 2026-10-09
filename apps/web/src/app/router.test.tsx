import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { adminUser, demoUser } from "@/mocks/fixtures";
import type { AuthSession } from "@/lib/auth-store";
import { useAuthStore } from "@/lib/auth-store";

function renderRoute(entry: string, session?: AuthSession) {
  useAuthStore.setState({ session: session ?? null });

  const router = createMemoryRouter(appRoutes, {
    initialEntries: [entry],
  });

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("app router scaffold", () => {
  it("redirects guests to login", async () => {
    renderRoute("/app");

    expect(
      await screen.findByRole("heading", { name: "Iniciar sesión" }),
    ).toBeInTheDocument();
  });

  it("renders the dashboard inside the authenticated shell", async () => {
    renderRoute("/app", {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    });

    expect(await screen.findByRole("heading", { name: "Ponds" })).toBeInTheDocument();
    expect(await screen.findByTestId("ponds-dashboard")).toBeInTheDocument();
    expect(screen.getByText("Operador Demo")).toBeInTheDocument();
  });

  it("exposes admin navigation to administrators", async () => {
    renderRoute("/app/admin/users", {
      accessToken: "access_admin_token",
      refreshToken: "refresh_admin_token",
      user: adminUser,
    });

    const userHeadings = await screen.findAllByRole("heading", { name: "Usuarios" });

    expect(userHeadings).toHaveLength(2);
    expect(screen.getByRole("link", { name: "Bitácora" })).toBeInTheDocument();
  });
});
