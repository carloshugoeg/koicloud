import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { ToastHost } from "@/lib/toast-host";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const POND_ID = fixtures.pond.id;

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

describe("W2-06 Detalle del pond y conexión", () => {
  it("polls while provisioning and shows En línea when the pond becomes ready", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    let calls = 0;
    server.use(
      http.get(`*/api/v1/ponds/${POND_ID}`, () => {
        calls += 1;
        const observed_state = calls < 2 ? "provisioning" : "running";
        return HttpResponse.json({
          pond: { ...fixtures.pond, id: POND_ID, observed_state },
        });
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-status-badge")).toHaveTextContent("Aprovisionando…");
    expect(screen.getByTestId("pond-in-progress")).toBeInTheDocument();

    await vi.advanceTimersByTimeAsync(4_500);
    await waitFor(() => {
      expect(screen.getByTestId("pond-status-badge")).toHaveTextContent("En línea");
    });
    expect(screen.queryByTestId("pond-in-progress")).not.toBeInTheDocument();
    vi.useRealTimers();
  });

  it("shows the failed state with last_error", async () => {
    server.use(
      http.get(`*/api/v1/ponds/${POND_ID}`, () =>
        HttpResponse.json({
          pond: {
            ...fixtures.pond,
            id: POND_ID,
            observed_state: "failed",
            healthy: false,
            last_error: "disk_full",
          },
        }),
      ),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-status-badge")).toHaveTextContent("Con fallas");
    expect(screen.getByTestId("pond-failed")).toHaveTextContent("Último error: disk_full");
  });

  it("shows connection fields and En línea badge for a running pond", async () => {
    renderDetail();

    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    expect(screen.getByTestId("pond-status-badge")).toHaveTextContent("En línea");
    expect(await screen.findByTestId("conn-host")).toHaveTextContent(fixtures.connection.host);
    expect(screen.getByTestId("conn-port")).toHaveTextContent(String(fixtures.connection.port));
    expect(screen.getByTestId("conn-user")).toHaveTextContent(fixtures.connection.username);
    expect(screen.getByTestId("conn-db")).toHaveTextContent(fixtures.connection.database);
    expect(screen.getByTestId("conn-password")).toHaveTextContent("••••••••");
    expect(screen.queryByText(fixtures.connection.password)).not.toBeInTheDocument();
  });

  it("reveals the password only after Revelar and copies the URI", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    renderDetail();
    expect(await screen.findByTestId("conn-password")).toHaveTextContent("••••••••");

    await user.click(screen.getByTestId("reveal-password"));
    expect(screen.getByTestId("conn-password")).toHaveTextContent(fixtures.connection.password);

    await user.click(screen.getByTestId("copy-uri"));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(fixtures.connection.uri);
    });
    expect(screen.getByTestId("copy-uri")).toHaveTextContent("URI copiada");
    expect(screen.getByTestId("toast")).toHaveTextContent("URI copiada");
  });

  it("shows catalog message for pond_not_found without a stack", async () => {
    server.use(
      http.get(`*/api/v1/ponds/${POND_ID}`, () =>
        HttpResponse.json(
          { code: "pond_not_found", message: "missing", request_id: "req_pond" },
          { status: 404 },
        ),
      ),
    );
    renderDetail();

    expect(await screen.findByTestId("pond-detail-error")).toBeInTheDocument();
    expect(screen.getByText("No encontramos ese pond.")).toBeInTheDocument();
    expect(screen.getByText("pond_not_found")).toBeInTheDocument();
    expect(screen.queryByText(/at Object|TypeError|stack/i)).not.toBeInTheDocument();
  });

  it("posts backup now as 202 while the pond is running", async () => {
    const user = userEvent.setup();
    let status = 0;
    let confirmToken: string | null = "unset";
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/backups`, ({ request }) => {
        status = 202;
        confirmToken = request.headers.get("X-KOI-Confirm-Token");
        return HttpResponse.json(
          {
            backup: {
              ...fixtures.backups[1],
              completed_at: null,
              expires_at: null,
              status: "queued",
            },
            job: {
              attempts: 0,
              created_at: "2026-10-26T15:00:00Z",
              id: "job_backup_01",
              node_id: "node-sv-01",
              pond_id: POND_ID,
              status: "queued",
              type: "backup_pond",
            },
          },
          { status: 202 },
        );
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    expect(screen.queryByTestId("retry-failed")).not.toBeInTheDocument();
    await user.click(screen.getByTestId("backup-now"));

    expect(await screen.findByText("Respaldo encolado")).toBeInTheDocument();
    expect(status).toBe(202);
    expect(confirmToken).toBeNull();
  });

  it("posts retry as 202 when the pond failed", async () => {
    const user = userEvent.setup();
    let status = 0;
    let confirmToken: string | null = "unset";
    server.use(
      http.get(`*/api/v1/ponds/${POND_ID}`, () =>
        HttpResponse.json({
          pond: {
            ...fixtures.pond,
            healthy: false,
            last_error: "driver timeout",
            observed_state: "failed",
          },
        }),
      ),
      http.post(`*/api/v1/ponds/${POND_ID}/retry`, ({ request }) => {
        status = 202;
        confirmToken = request.headers.get("X-KOI-Confirm-Token");
        return HttpResponse.json(
          {
            job: {
              attempts: 1,
              created_at: "2026-10-26T15:00:00Z",
              id: "job_retry_01",
              node_id: "node-sv-01",
              pond_id: POND_ID,
              status: "queued",
              type: "backup_pond",
            },
          },
          { status: 202 },
        );
      }),
    );

    renderDetail();
    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    expect(screen.queryByTestId("backup-now")).not.toBeInTheDocument();
    await user.click(screen.getByTestId("retry-failed"));

    expect(await screen.findByText("Reintento encolado")).toBeInTheDocument();
    expect(status).toBe(202);
    expect(confirmToken).toBeNull();
  });
});
