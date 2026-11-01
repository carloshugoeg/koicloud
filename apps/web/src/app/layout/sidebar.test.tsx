import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
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

function renderApp(width: number, status: "active" | "suspended" = "active") {
  setViewport(width);
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: { ...demoUser, status },
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
  afterEach(() => {
    setViewport(1280);
    useAuthStore.setState({ session: null });
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
    expect(within(rail).getByRole("link", { name: "Uso y facturación" })).toBeInTheDocument();
    expect(within(rail).queryByRole("link", { name: "Uso del mes" })).not.toBeInTheDocument();
    expect(within(rail).queryByRole("link", { name: "Facturación" })).not.toBeInTheDocument();
    expect(within(rail).queryByRole("link", { name: "Planes" })).not.toBeInTheDocument();
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

  it("shows the suspended banner for a suspended account", async () => {
    renderApp(1280, "suspended");

    const banner = await screen.findByTestId("suspended-banner");
    expect(banner).toHaveTextContent("Tu cuenta está suspendida.");
    expect(banner.className).toContain("border-marigold");
    expect(banner).toHaveTextContent("No puedes crear ponds ni ejecutar SQL.");
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

  it("closes the sheet on Escape and returns focus to the hamburger", async () => {
    const user = userEvent.setup();
    renderApp(360);

    const menu = await screen.findByTestId("nav-menu-button");
    await user.click(menu);

    const sheet = await screen.findByTestId("sidebar-sheet");
    const close = within(sheet).getByRole("button", { name: "Cerrar menú" });
    expect(close).toHaveFocus();

    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("sidebar-sheet")).not.toBeInTheDocument();
    expect(menu).toHaveFocus();
  });

  it("keeps Tab focus inside the open sheet dialog", async () => {
    const user = userEvent.setup();
    renderApp(360);

    await user.click(await screen.findByTestId("nav-menu-button"));
    const sheet = await screen.findByTestId("sidebar-sheet");
    const dialog = within(sheet).getByRole("dialog", { name: "Navegación" });

    expect(within(dialog).getByRole("button", { name: "Cerrar menú" })).toHaveFocus();

    // Cycle forward through focusables; after the last, wrap to the first.
    for (let i = 0; i < 20; i += 1) {
      await user.tab();
      expect(dialog.contains(document.activeElement)).toBe(true);
    }

    await user.tab({ shift: true });
    expect(dialog.contains(document.activeElement)).toBe(true);
  });
});
