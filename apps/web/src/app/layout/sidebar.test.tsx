import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { demoUser } from "@/mocks/fixtures";
import { useAuthStore } from "@/lib/auth-store";

function setViewport(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  window.dispatchEvent(new Event("resize"));
}

function renderApp(width: number) {
  setViewport(width);
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });

  const router = createMemoryRouter(appRoutes, {
    initialEntries: ["/app/ponds"],
  });

  return render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("AppShell sidebar — groups, active, collapse (§5.1)", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    setViewport(1280);
    useAuthStore.setState({ session: null });
    sessionStorage.clear();
  });

  it("renders §5.1 groups in expanded desktop mode", async () => {
    renderApp(1280);

    const rail = await screen.findByTestId("sidebar-rail");
    expect(rail).toHaveAttribute("data-collapsed", "false");

    expect(within(rail).getByText("Estanque")).toBeInTheDocument();
    expect(within(rail).getByText("Consumo")).toBeInTheDocument();
    expect(within(rail).getByText("Agente")).toBeInTheDocument();
    expect(within(rail).getByText("Cuenta")).toBeInTheDocument();

    expect(within(rail).getByRole("link", { name: "Ponds" })).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: "Crear pond" })).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: "Uso del mes" })).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: "Facturación" })).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: "Planes" })).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: "Acceso agente" })).toBeInTheDocument();
    expect(within(rail).getByRole("link", { name: "Perfil" })).toBeInTheDocument();

    const ponds = within(rail).getByRole("link", { name: "Ponds" });
    expect(ponds).toHaveAttribute("aria-current", "page");
    expect(ponds.className).toMatch(/bg-turquoise-100/);
  });

  it("collapses to icon rail below 1024 px", async () => {
    renderApp(900);

    const rail = await screen.findByTestId("sidebar-rail");
    expect(rail).toHaveAttribute("data-collapsed", "true");
    const groupLabel = within(rail).getByText("Estanque");
    expect(groupLabel).toHaveClass("sr-only");
    expect(within(rail).getByRole("link", { name: "Ponds" })).toBeInTheDocument();
    expect(screen.queryByTestId("nav-menu-button")).not.toBeInTheDocument();
  });

  it("uses Sheet + hamburger below 768 px", async () => {
    const user = userEvent.setup();
    renderApp(360);

    expect(await screen.findByTestId("nav-menu-button")).toBeInTheDocument();
    expect(screen.queryByTestId("sidebar-sheet")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("nav-menu-button"));
    const sheet = await screen.findByTestId("sidebar-sheet");
    expect(within(sheet).getByText("Estanque")).toBeInTheDocument();
    expect(within(sheet).getByRole("link", { name: "Crear pond" })).toBeInTheDocument();

    await user.click(within(sheet).getByRole("button", { name: "Cerrar menú" }));
    expect(screen.queryByTestId("sidebar-sheet")).not.toBeInTheDocument();
  });
});

describe("session boot DataState (CA3)", () => {
  beforeEach(() => {
    sessionStorage.clear();
    useAuthStore.setState({ session: null });
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    });
  });

  afterEach(() => {
    sessionStorage.clear();
    useAuthStore.setState({ session: null });
  });

  it("restores session from sessionStorage through SessionBootGate", async () => {
    sessionStorage.setItem(
      "koicloud.session",
      JSON.stringify({
        accessToken: "access_demo_token",
        refreshToken: "refresh_demo_token",
        user: demoUser,
      }),
    );

    setViewport(1280);
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/app/ponds"],
    });

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    expect(await screen.findByTestId("ponds-dashboard")).toBeInTheDocument();
    expect(useAuthStore.getState().session?.accessToken).toBe("access_demo_token");
  });
});
