import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { server } from "@/mocks/server";

const QA_USER = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1",
  email: "qa+1@koicloud.test",
  full_name: "QA Uno",
  role: "client" as const,
  status: "active" as const,
  email_verified: true,
  created_at: "2026-11-01T12:00:00Z",
  active_subscription_plan: "pro",
};

const DEMO_USER = {
  id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2",
  email: "demo@koicloud.test",
  full_name: "Cuenta Demo",
  role: "client" as const,
  status: "active" as const,
  email_verified: true,
  created_at: "2026-10-01T12:00:00Z",
  active_subscription_plan: "micro",
};

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function installNetwork() {
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    const method = (
      input instanceof Request ? input.method : (init?.method ?? "GET")
    ).toUpperCase();

    if (method === "GET" && url.includes("/api/v1/admin/users")) {
      return jsonResponse({ users: [QA_USER, DEMO_USER], next_cursor: null });
    }
    if (method === "GET" && url.includes("/api/v1/admin/ponds")) {
      return jsonResponse({ ponds: [], next_cursor: null });
    }
    return jsonResponse({ code: "internal_error", message: "unmocked" }, 500);
  });
}

function renderUsersScreen() {
  useAuthStore.setState({
    session: {
      accessToken: "access_admin_token",
      refreshToken: "refresh_admin_token",
      user: {
        id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa0",
        email: "qa-admin@koicloud.test",
        full_name: "QA Admin",
        role: "admin",
        status: "active",
        email_verified: true,
        nit: null,
        created_at: "2026-09-01T12:00:00Z",
      },
    },
  });

  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/admin/users"] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("admin users from the API client with MSW off", () => {
  beforeAll(() => {
    server.close();
  });

  beforeEach(() => {
    installNetwork();
  });

  afterAll(() => {
    vi.unstubAllGlobals();
    server.listen({ onUnhandledRequest: "error" });
  });

  it("renders the accounts returned by the network", async () => {
    renderUsersScreen();

    expect(await screen.findByText("QA Uno")).toBeInTheDocument();
    expect(screen.getByText("qa+1@koicloud.test")).toBeInTheDocument();
    expect(screen.getByText("Cuenta Demo")).toBeInTheDocument();
    expect(screen.getByText("demo@koicloud.test")).toBeInTheDocument();
    expect(screen.getByText("pro")).toBeInTheDocument();
    expect(screen.queryByText("Carlos Hugo Escobar")).not.toBeInTheDocument();
    expect(screen.queryByText("Usuario Suspendido")).not.toBeInTheDocument();
    expect(screen.queryByText("carlos@koicloud.dev")).not.toBeInTheDocument();
    expect(screen.queryByText("suspended@koicloud.dev")).not.toBeInTheDocument();
    expect(screen.queryByText("Operador Demo")).not.toBeInTheDocument();
    expect(screen.queryByText("Sofía Mora")).not.toBeInTheDocument();
  });

  it("filters those accounts by the search box", async () => {
    const user = userEvent.setup();
    renderUsersScreen();
    await screen.findByText("QA Uno");

    await user.type(screen.getByRole("textbox", { name: /buscar/i }), "qa");

    expect(screen.getByText("QA Uno")).toBeInTheDocument();
    expect(screen.queryByText("Cuenta Demo")).not.toBeInTheDocument();
    expect(screen.getByTestId("admin-users-summary")).toHaveTextContent("1 cuentas visibles");
  });

  it("appends the next page when Cargar más is used", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = (
        input instanceof Request ? input.method : (init?.method ?? "GET")
      ).toUpperCase();
      if (method === "GET" && url.includes("/api/v1/admin/users")) {
        const cursor = new URL(url).searchParams.get("cursor");
        if (cursor == null) {
          return jsonResponse({ users: [QA_USER], next_cursor: "page-2" });
        }
        expect(cursor).toBe("page-2");
        return jsonResponse({ users: [DEMO_USER], next_cursor: null });
      }
      if (method === "GET" && url.includes("/api/v1/admin/ponds")) {
        return jsonResponse({ ponds: [], next_cursor: null });
      }
      return jsonResponse({ code: "internal_error", message: "unmocked" }, 500);
    });

    renderUsersScreen();

    expect(await screen.findByText("QA Uno")).toBeInTheDocument();
    expect(screen.queryByText("Cuenta Demo")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Cargar más" }));

    expect(await screen.findByText("Cuenta Demo")).toBeInTheDocument();
    expect(screen.getByText("QA Uno")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cargar más" })).not.toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /buscar/i }), "demo");
    expect(screen.getByText("Cuenta Demo")).toBeInTheDocument();
    expect(screen.queryByText("QA Uno")).not.toBeInTheDocument();
  });

  it("keeps focus on Cargar más while the next page loads", async () => {
    const user = userEvent.setup();
    let releaseNext: () => void = () => {};
    const gate = new Promise<void>((resolve) => {
      releaseNext = resolve;
    });
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = (
        input instanceof Request ? input.method : (init?.method ?? "GET")
      ).toUpperCase();
      if (method === "GET" && url.includes("/api/v1/admin/users")) {
        const cursor = new URL(url).searchParams.get("cursor");
        if (cursor == null) {
          return jsonResponse({ users: [QA_USER], next_cursor: "page-2" });
        }
        await gate;
        return jsonResponse({ users: [DEMO_USER], next_cursor: "page-3" });
      }
      if (method === "GET" && url.includes("/api/v1/admin/ponds")) {
        return jsonResponse({ ponds: [], next_cursor: null });
      }
      return jsonResponse({ code: "internal_error", message: "unmocked" }, 500);
    });

    try {
      renderUsersScreen();
      expect(await screen.findByText("QA Uno")).toBeInTheDocument();
      await user.click(screen.getByRole("button", { name: "Cargar más" }));

      const busy = await screen.findByRole("button", { name: "Cargando…" });
      expect(busy).toHaveFocus();
      expect(busy).toBeEnabled();
      expect(busy).toHaveAttribute("aria-busy", "true");

      releaseNext();
      expect(await screen.findByText("Cuenta Demo")).toBeInTheDocument();
      expect(screen.getByText("QA Uno")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Cargar más" })).toHaveFocus();
    } finally {
      releaseNext();
    }
  });

  it("shows an inline error and retries the next page without dropping loaded rows", async () => {
    const user = userEvent.setup();
    let failCursor = true;
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = (
        input instanceof Request ? input.method : (init?.method ?? "GET")
      ).toUpperCase();
      if (method === "GET" && url.includes("/api/v1/admin/users")) {
        const cursor = new URL(url).searchParams.get("cursor");
        if (cursor == null) {
          return jsonResponse({ users: [QA_USER], next_cursor: "page-2" });
        }
        if (failCursor) {
          return jsonResponse({ code: "internal_error", message: "internal_error" }, 500);
        }
        return jsonResponse({ users: [DEMO_USER], next_cursor: null });
      }
      if (method === "GET" && url.includes("/api/v1/admin/ponds")) {
        return jsonResponse({ ponds: [], next_cursor: null });
      }
      return jsonResponse({ code: "internal_error", message: "unmocked" }, 500);
    });

    renderUsersScreen();
    expect(await screen.findByText("QA Uno")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cargar más" }));

    const page = screen.getByTestId("admin-users-page");
    const alert = await within(page).findByRole("alert");
    expect(alert).toHaveTextContent(/No pudimos cargar más usuarios\./);
    expect(screen.getByText("QA Uno")).toBeInTheDocument();
    expect(screen.queryByText("Cuenta Demo")).not.toBeInTheDocument();
    expect(screen.queryByTestId("admin-users-error")).not.toBeInTheDocument();

    failCursor = false;
    await user.click(within(alert).getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText("Cuenta Demo")).toBeInTheDocument();
    expect(screen.getByText("QA Uno")).toBeInTheDocument();
    expect(within(page).queryByRole("alert")).not.toBeInTheDocument();
  });

  it("names the search as a filter over loaded users and hints when more pages remain", async () => {
    const user = userEvent.setup();
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = (
        input instanceof Request ? input.method : (init?.method ?? "GET")
      ).toUpperCase();
      if (method === "GET" && url.includes("/api/v1/admin/users")) {
        const cursor = new URL(url).searchParams.get("cursor");
        if (cursor == null) {
          return jsonResponse({ users: [QA_USER], next_cursor: "page-2" });
        }
        return jsonResponse({ users: [DEMO_USER], next_cursor: null });
      }
      if (method === "GET" && url.includes("/api/v1/admin/ponds")) {
        return jsonResponse({ ponds: [], next_cursor: null });
      }
      return jsonResponse({ code: "internal_error", message: "unmocked" }, 500);
    });

    renderUsersScreen();
    expect(await screen.findByText("QA Uno")).toBeInTheDocument();

    expect(screen.getByRole("textbox", { name: /buscar/i })).toHaveAttribute(
      "placeholder",
      "Filtrar usuarios cargados",
    );
    expect(screen.getByText("Cargá más para buscar en el resto")).toBeInTheDocument();

    await user.type(screen.getByRole("textbox", { name: /buscar/i }), "zzz-no-existe");
    expect(screen.getByTestId("admin-users-empty")).toHaveTextContent("No hay usuarios con ese filtro.");
    expect(screen.getByText("Cargá más para buscar en el resto")).toBeInTheDocument();
    expect(screen.queryByText("No hay usuarios.")).not.toBeInTheDocument();
  });

  it("says there are no users yet when the list is empty and no filter is set", async () => {
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input instanceof Request ? input.url : String(input);
      const method = (
        input instanceof Request ? input.method : (init?.method ?? "GET")
      ).toUpperCase();
      if (method === "GET" && url.includes("/api/v1/admin/users")) {
        return jsonResponse({ users: [], next_cursor: null });
      }
      if (method === "GET" && url.includes("/api/v1/admin/ponds")) {
        return jsonResponse({ ponds: [], next_cursor: null });
      }
      return jsonResponse({ code: "internal_error", message: "unmocked" }, 500);
    });

    renderUsersScreen();
    expect(await screen.findByTestId("admin-users-empty")).toHaveTextContent(/^No hay usuarios\.$/);
    expect(screen.queryByText("No hay usuarios con ese filtro.")).not.toBeInTheDocument();
    expect(screen.queryByText("Cargá más para buscar en el resto")).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /buscar/i })).toHaveAttribute(
      "placeholder",
      "Filtrar usuarios cargados",
    );
  });
});
