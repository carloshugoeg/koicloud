import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, vi } from "vitest";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { ToastHost } from "@/lib/toast-host";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const POND_ID = fixtures.pond.id;

const EMPTY_SCHEMA = { tables: [] as const };

const TWO_TABLES_SCHEMA = {
  tables: [
    {
      name: "public.orders",
      estimated_rows: 2,
      columns: [
        { name: "id", type: "integer", nullable: false, default: null },
        { name: "label", type: "text", nullable: false, default: "'x'::text" },
      ],
    },
    {
      name: "public.items",
      estimated_rows: 12,
      columns: [
        { name: "sku", type: "text", nullable: false, default: null },
        { name: "qty", type: "integer", nullable: true, default: null },
      ],
    },
  ],
};

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });
}

function renderDetail(entry = `/app/ponds/${POND_ID}`) {
  seedSession();
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: 0 },
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
      <ToastHost />
    </QueryClientProvider>,
  );
}

function schemaPath() {
  return `*/api/v1/ponds/${POND_ID}/schema`;
}

afterEach(() => {
  vi.useRealTimers();
});

describe("Pond table explorer (#207)", () => {
  it("shows idle Tablas UI on mount and does not GET /schema until Recargar", async () => {
    let schemaGets = 0;
    server.use(
      http.get(schemaPath(), () => {
        schemaGets += 1;
        return HttpResponse.json(EMPTY_SCHEMA);
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    expect(screen.getByTestId("pond-tables-idle")).toBeInTheDocument();
    expect(screen.getByTestId("pond-tables-reload")).toHaveTextContent("Recargar");
    expect(screen.getByTestId("pond-tables-status")).toHaveAttribute("aria-live", "polite");

    await new Promise((resolve) => {
      setTimeout(resolve, 1500);
    });
    expect(schemaGets).toBe(0);
  });

  it("Recargar with empty schema shows exact empty copy", async () => {
    const user = userEvent.setup();
    server.use(http.get(schemaPath(), () => HttpResponse.json(EMPTY_SCHEMA)));

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    await user.click(screen.getByTestId("pond-tables-reload"));

    expect(await screen.findByTestId("pond-tables-empty")).toHaveTextContent(
      "Esta pond aún no tiene tablas",
    );
  });

  it("Recargar lists schema-qualified tables from the response", async () => {
    const user = userEvent.setup();
    server.use(http.get(schemaPath(), () => HttpResponse.json(TWO_TABLES_SCHEMA)));

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    await user.click(screen.getByTestId("pond-tables-reload"));

    const list = await screen.findByTestId("pond-tables-list");
    const rows = within(list).getAllByTestId("pond-tables-table");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveAttribute("data-table-name", "public.orders");
    expect(rows[1]).toHaveAttribute("data-table-name", "public.items");
    expect(list).toHaveTextContent("public.orders");
    expect(list).toHaveTextContent("public.items");
  });

  it("expanding a table shows columns and estimated rows with tabular intent", async () => {
    const user = userEvent.setup();
    server.use(http.get(schemaPath(), () => HttpResponse.json(TWO_TABLES_SCHEMA)));

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    await user.click(screen.getByTestId("pond-tables-reload"));

    const list = await screen.findByTestId("pond-tables-list");
    const ordersRow = within(list)
      .getAllByTestId("pond-tables-table")
      .find((row) => row.getAttribute("data-table-name") === "public.orders");
    expect(ordersRow).toBeTruthy();

    await user.click(within(ordersRow as HTMLElement).getByTestId("pond-tables-expand"));

    const columns = within(ordersRow as HTMLElement).getByTestId("pond-tables-columns");
    expect(columns).toHaveTextContent("id");
    expect(columns).toHaveTextContent("integer");
    expect(columns).toHaveTextContent("label");
    expect(columns).toHaveTextContent("text");
    expect(columns.textContent).toMatch(/nulo|Sí|No/i);

    const estimated = within(ordersRow as HTMLElement).getByTestId(
      "pond-tables-estimated-rows",
    );
    expect(estimated).toHaveTextContent("2");
    expect(estimated.className.split(/\s+/)).toContain("tabular-nums");
  });

  it("schema error shows Reintentar and refetch recovers", async () => {
    const user = userEvent.setup();
    let calls = 0;
    server.use(
      http.get(schemaPath(), () => {
        calls += 1;
        if (calls === 1) {
          return HttpResponse.json(
            {
              code: "internal_error",
              message: "schema boom",
              request_id: "req_schema_err",
            },
            { status: 500 },
          );
        }
        return HttpResponse.json(TWO_TABLES_SCHEMA);
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    await user.click(screen.getByTestId("pond-tables-reload"));

    const errorBand = await screen.findByTestId("pond-tables-error");
    expect(errorBand).toBeInTheDocument();
    const retry = within(errorBand).getByRole("button", { name: "Reintentar" });
    await user.click(retry);

    expect(await screen.findByTestId("pond-tables-list")).toBeInTheDocument();
    expect(screen.getByText("public.orders")).toBeInTheDocument();
    expect(calls).toBe(2);
  });

  it("stopped pond shows not-running state and Recargar does not hit /schema", async () => {
    const user = userEvent.setup();
    let schemaGets = 0;
    server.use(
      http.get(`*/api/v1/ponds/${POND_ID}`, () =>
        HttpResponse.json({
          pond: {
            ...fixtures.pond,
            desired_state: "stopped",
            observed_state: "stopped",
            healthy: false,
          },
        }),
      ),
      http.get(schemaPath(), () => {
        schemaGets += 1;
        return HttpResponse.json(EMPTY_SCHEMA);
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    expect(screen.getByTestId("pond-tables-not-running")).toBeInTheDocument();
    expect(screen.getByTestId("pond-tables-not-running").textContent).toMatch(/ejecuci[oó]n/i);

    const reload = screen.getByTestId("pond-tables-reload");
    expect(reload).toBeDisabled();
    await user.click(reload);
    expect(schemaGets).toBe(0);
  });

  it("does not poll /schema after a successful load without another press", async () => {
    const user = userEvent.setup();
    let schemaGets = 0;
    server.use(
      http.get(schemaPath(), () => {
        schemaGets += 1;
        return HttpResponse.json(TWO_TABLES_SCHEMA);
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    await user.click(screen.getByTestId("pond-tables-reload"));
    expect(await screen.findByTestId("pond-tables-list")).toBeInTheDocument();
    expect(schemaGets).toBe(1);

    await new Promise((resolve) => {
      setTimeout(resolve, 5_000);
    });
    expect(schemaGets).toBe(1);
  });

  it("marks Recargar aria-busy while loading and updates the polite live region", async () => {
    const user = userEvent.setup();
    let release!: () => void;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    server.use(
      http.get(schemaPath(), async () => {
        await gate;
        return HttpResponse.json(TWO_TABLES_SCHEMA);
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-tables")).toBeInTheDocument();
    const reload = screen.getByTestId("pond-tables-reload");
    const clickPromise = user.click(reload);

    await waitFor(() => {
      expect(reload).toHaveAttribute("aria-busy", "true");
    });
    expect(document.activeElement).toBe(reload);
    expect(screen.getByTestId("pond-tables-loading")).toBeInTheDocument();

    release();
    await clickPromise;
    expect(await screen.findByTestId("pond-tables-list")).toBeInTheDocument();
    await waitFor(() => {
      expect(reload).not.toHaveAttribute("aria-busy", "true");
    });
    expect(document.activeElement).toBe(reload);

    const status = screen.getByTestId("pond-tables-status");
    expect(status).toHaveAttribute("aria-live", "polite");
    expect(status.textContent?.length ?? 0).toBeGreaterThan(0);
  });
});
