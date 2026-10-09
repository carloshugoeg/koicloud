import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
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
    </QueryClientProvider>,
  );
}

describe("W2-08 Respaldos y restauración", () => {
  it("lists backups and shows the pre_delete chip", async () => {
    renderBackups();

    const page = await screen.findByTestId("backups-page");
    expect(page.querySelector('[data-kind="pre_delete"]')).not.toBeNull();
    expect(page.querySelector('[data-kind="daily"]')).not.toBeNull();
    expect(page.querySelector('[data-kind="on_demand"]')).not.toBeNull();
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
});
