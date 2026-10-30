import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionBootGate } from "@/app/session-boot-gate";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

function queryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: 0 },
    },
  });
}

function renderAt(path: string, skipBoot: boolean) {
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] });
  render(
    <QueryClientProvider client={queryClient()}>
      <SessionBootGate skipBoot={skipBoot}>
        <RouterProvider router={router} />
      </SessionBootGate>
    </QueryClientProvider>,
  );
  return router;
}

function seedMemorySession(refreshToken: string) {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken,
      user: fixtures.session.user,
    },
  });
}

async function refreshBodyToken(request: Request) {
  const raw = await request.text();
  if (!raw.trim()) {
    return undefined;
  }
  const body = JSON.parse(raw) as { refresh_token?: unknown };
  return typeof body.refresh_token === "string" && body.refresh_token.length > 0
    ? body.refresh_token
    : undefined;
}

describe("journey reload", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", () => undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("journey: reload keeps session", async () => {
    const refreshCalls: string[] = [];
    server.use(
      http.post("*/api/v1/auth/refresh", async ({ request }) => {
        refreshCalls.push((await refreshBodyToken(request)) ?? "");
        return HttpResponse.json(fixtures.refreshed);
      }),
    );
    useAuthStore.setState({ session: null });

    renderAt("/app/ponds", false);

    expect(await screen.findByRole("heading", { name: "Tus ponds" })).toBeInTheDocument();
    expect(screen.getByText("Operador Demo")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Iniciar sesión" })).not.toBeInTheDocument();
    expect(refreshCalls).toEqual([""]);
    expect(useAuthStore.getState().session).toMatchObject({
      accessToken: fixtures.refreshed.access_token,
      user: { email: "demo@koicloud.dev" },
    });
  });

  it("journey: no refresh cookie shows login", async () => {
    useAuthStore.setState({ session: null });

    renderAt("/app/ponds", false);

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Tus ponds" })).not.toBeInTheDocument();
    expect(useAuthStore.getState().session).toBeNull();
  });

  it("journey: bad refresh cookie shows login", async () => {
    const intercepted = window.fetch.bind(window);
    vi.stubGlobal("fetch", (input: RequestInfo | URL, init?: RequestInit) => {
      const headers = new Headers(input instanceof Request ? input.headers : undefined);
      if (init?.headers) {
        new Headers(init.headers).forEach((value, key) => {
          headers.set(key, value);
        });
      }
      headers.set("cookie", "koi_refresh=not-a-real-refresh");
      return intercepted(input, { ...init, headers });
    });
    useAuthStore.setState({ session: null });

    renderAt("/app/ponds", false);

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Tus ponds" })).not.toBeInTheDocument();
    expect(useAuthStore.getState().session).toBeNull();
  });

  it("journey: reload refresh failure logs out", async () => {
    let refreshCalls = 0;
    server.use(
      http.post("*/api/v1/auth/refresh", () => {
        refreshCalls += 1;
        return HttpResponse.json(
          { code: "token_invalid", message: "Token inválido", request_id: "req_reload" },
          { status: 401 },
        );
      }),
    );
    useAuthStore.setState({ session: null });

    renderAt("/app/ponds", false);

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Tus ponds" })).not.toBeInTheDocument();
    expect(refreshCalls).toBe(1);
    expect(useAuthStore.getState().session).toBeNull();
  });
});

describe("session refresh and logout", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });

  it("auth: expired access refreshes silently", async () => {
    server.use(
      http.post("*/api/v1/auth/refresh", async ({ request }) => {
        const token = await refreshBodyToken(request);
        if (token) {
          return HttpResponse.json(
            { code: "token_invalid", message: "body token", request_id: "req_body" },
            { status: 401 },
          );
        }
        return HttpResponse.json(fixtures.refreshed);
      }),
      http.get("*/api/v1/ponds", ({ request }) => {
        if (request.headers.get("authorization") !== `Bearer ${fixtures.refreshed.access_token}`) {
          return HttpResponse.json(
            { code: "token_expired", message: "expiró", request_id: "req_exp" },
            { status: 401 },
          );
        }
        return HttpResponse.json({ ponds: [], next_cursor: null });
      }),
    );
    seedMemorySession("");

    renderAt("/app/ponds", true);

    expect(await screen.findByTestId("ponds-empty")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Iniciar sesión" })).not.toBeInTheDocument();
    expect(useAuthStore.getState().session?.accessToken).toBe(fixtures.refreshed.access_token);
  });

  it("journey: logout returns to login", async () => {
    const logoutCalls: string[] = [];
    server.use(
      http.post("*/api/v1/auth/logout", ({ request }) => {
        logoutCalls.push(request.headers.get("authorization") ?? "");
        return new HttpResponse(null, { status: 204 });
      }),
    );
    seedMemorySession(fixtures.session.refresh_token);
    const user = userEvent.setup();

    renderAt("/app/ponds", true);

    expect(await screen.findByRole("heading", { name: "Tus ponds" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    await waitFor(() => {
      expect(logoutCalls).toEqual([`Bearer ${fixtures.session.access_token}`]);
    });
    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(useAuthStore.getState().session).toBeNull();
  });

  it("journey: logout failure still returns to login", async () => {
    server.use(
      http.post("*/api/v1/auth/logout", () => {
        return HttpResponse.json(
          { code: "internal_error", message: "falló", request_id: "req_logout" },
          { status: 500 },
        );
      }),
    );
    seedMemorySession(fixtures.session.refresh_token);
    const user = userEvent.setup();

    renderAt("/app/ponds", true);

    expect(await screen.findByRole("heading", { name: "Tus ponds" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cerrar sesión" }));

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(useAuthStore.getState().session).toBeNull();
  });
});
