import { render, screen } from "@testing-library/react";
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
});
