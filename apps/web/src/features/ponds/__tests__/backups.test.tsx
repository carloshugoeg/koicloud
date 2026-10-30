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

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });
}

function renderBackups(entry = `/app/ponds/${POND_ID}/backups`) {
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

describe("W2-08 Respaldos y restauración", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("lists backups and shows the pre_delete chip", async () => {
    renderBackups();

    const page = await screen.findByTestId("backups-page");
    expect(page.querySelector('[data-kind="pre_delete"]')).not.toBeNull();
    expect(page.querySelector('[data-kind="daily"]')).not.toBeNull();
    expect(page.querySelector('[data-kind="on_demand"]')).not.toBeNull();
  });

  it("fills Expira from expires_at instead of a blank column", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-26T15:00:00Z"));
    renderBackups();

    const cells = await screen.findAllByTestId("backup-expires");
    expect(cells.map((cell) => cell.textContent)).toEqual(["vencido", "vencido", "—"]);
    expect(cells[0]).toHaveAttribute("title", "2026-09-29 14:00");
    expect(cells[1]).toHaveAttribute("title", "2026-09-29 05:55");
    expect(cells[2]).not.toHaveAttribute("title");
  });

  it("keeps Restaurar disabled until the pond name matches exactly", async () => {
    const user = userEvent.setup();
    renderBackups();

    expect(await screen.findByTestId("backups-page")).toBeInTheDocument();
    const restoreButtons = await screen.findAllByRole("button", { name: "Restaurar…" });
    await user.click(restoreButtons[0]);

    const dialog = await screen.findByTestId("restore-dialog");
    const confirm = within(dialog).getByTestId("restore-confirm-button");
    expect(confirm).toBeDisabled();

    await user.type(within(dialog).getByTestId("restore-confirm-input"), "nombre-incorrecto");
    expect(confirm).toBeDisabled();

    await user.clear(within(dialog).getByTestId("restore-confirm-input"));
    await user.type(within(dialog).getByTestId("restore-confirm-input"), fixtures.pond.name);
    expect(confirm).toBeEnabled();
  });

  it("closes the restore dialog on Escape and returns focus to Restaurar…", async () => {
    const user = userEvent.setup();
    renderBackups();

    expect(await screen.findByTestId("backups-page")).toBeInTheDocument();
    const restoreBtn = (await screen.findAllByRole("button", { name: "Restaurar…" }))[0];
    await user.click(restoreBtn);

    const dialog = await screen.findByRole("dialog", { name: /Restaurar respaldo/i });
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby", "restore-title");

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: /Restaurar respaldo/i })).not.toBeInTheDocument();
    });
    expect(restoreBtn).toHaveFocus();
  });

  it("posts backup_id and shows the queued job on happy restore", async () => {
    const user = userEvent.setup();
    let postedBody: unknown = null;
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/restore`, async ({ request }) => {
        postedBody = await request.json();
        return HttpResponse.json(
          {
            job: {
              id: "job_restore_01",
              type: "restore_pond",
              status: "queued",
              attempts: 0,
              created_at: "2026-09-22T21:00:00Z",
              node_id: "node-sv-01",
              pond_id: POND_ID,
            },
          },
          { status: 202 },
        );
      }),
    );

    renderBackups();
    expect(await screen.findByTestId("backups-page")).toBeInTheDocument();
    await user.click((await screen.findAllByRole("button", { name: "Restaurar…" }))[0]);

    const dialog = await screen.findByTestId("restore-dialog");
    await user.type(within(dialog).getByTestId("restore-confirm-input"), fixtures.pond.name);
    await user.click(within(dialog).getByTestId("restore-confirm-button"));

    await waitFor(() => {
      expect(screen.getByTestId("restore-queued")).toBeInTheDocument();
    });
    expect(postedBody).toEqual({ backup_id: fixtures.backups[0].id });
    expect(screen.getByText("job_restore_01")).toBeInTheDocument();
    expect(screen.queryByTestId("toast")).not.toBeInTheDocument();
  });

  it("shows empty and error data states", async () => {
    server.use(
      http.get(`*/api/v1/ponds/${POND_ID}/backups`, () =>
        HttpResponse.json({ backups: [], next_cursor: null }),
      ),
    );
    renderBackups();
    expect(await screen.findByTestId("backups-empty")).toBeInTheDocument();
  });

  it("posts backup now as 202 and toasts Respaldo encolado", async () => {
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

    renderBackups();
    await user.click(await screen.findByTestId("backup-now"));
    const dialog = await screen.findByTestId("backup-confirm-dialog");
    await user.click(within(dialog).getByTestId("backup-confirm-button"));

    expect(await screen.findByText("Respaldo encolado")).toBeInTheDocument();
    expect(status).toBe(202);
    expect(confirmToken).toBeNull();
  });

  it("toasts the catalog message when backup now fails", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/backups`, () =>
        HttpResponse.json(
          { code: "pond_busy", message: "busy", request_id: "req_busy" },
          { status: 409 },
        ),
      ),
    );

    renderBackups();
    await user.click(await screen.findByTestId("backup-now"));
    const dialog = await screen.findByTestId("backup-confirm-dialog");
    await user.click(within(dialog).getByTestId("backup-confirm-button"));

    expect(await screen.findByText("Ese pond ya tiene una operación en curso.")).toBeInTheDocument();
    expect(screen.queryByText("Respaldo encolado")).not.toBeInTheDocument();
  });

  // RF-15 — confirmación local antes de POST /backups desde la página de respaldos
  it("confirms before queuing Respaldar ahora from the backups page", async () => {
    const user = userEvent.setup();
    renderBackups();
    expect(await screen.findByTestId("backup-now")).toBeInTheDocument();
    await user.click(screen.getByTestId("backup-now"));
    const dialog = await screen.findByTestId("backup-confirm-dialog");
    await user.click(within(dialog).getByTestId("backup-confirm-button"));
    expect(await screen.findByText("Respaldo encolado")).toBeInTheDocument();
  });
});
