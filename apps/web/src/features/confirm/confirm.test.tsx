import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { confirmSearch, parseConfirmLocation, type ConfirmationProposal } from "@/features/confirm/proposal";
import { useAuthStore } from "@/lib/auth-store";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const TOKEN = "conf_create_pond_demo";
const SUMMARY = "Se creará el pond 'inventario-demo'. Expira en 5 min.";

type Hit = { method: string; token: string; body: string };

function proposalSearch(expiresAt = new Date(Date.now() + 5 * 60_000)) {
  const arrival = parseConfirmLocation({
    search: `?token=${TOKEN}&summary=${encodeURIComponent(SUMMARY)}&expires_at=${encodeURIComponent(expiresAt.toISOString())}`,
    state: null,
  });
  if (arrival.kind !== "ready") {
    throw new Error("fixture did not parse");
  }
  return { proposal: arrival.proposal, search: confirmSearch(arrival.proposal) };
}

function wireFor(proposal: ConfirmationProposal) {
  return {
    status: "confirmation_required" as const,
    token: proposal.token,
    summary: proposal.summary,
    expires_at: proposal.expiresAt.toISOString(),
    next: {
      cli_example: `koicloud confirm ${proposal.token}`,
      confirm_url: `/api/v1/confirm/${proposal.token}`,
    },
  };
}

function spyConfirm() {
  const hits: Hit[] = [];
  server.use(
    http.post("*/api/v1/confirm/:token", async ({ request, params }) => {
      hits.push({
        method: "POST",
        token: String(params.token),
        body: await request.text(),
      });
      return HttpResponse.json({});
    }),
    http.delete("*/api/v1/confirm/:token", async ({ request, params }) => {
      hits.push({
        method: "DELETE",
        token: String(params.token),
        body: await request.text(),
      });
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return hits;
}

function failConfirm(status: number, code: string) {
  server.use(
    http.post("*/api/v1/confirm/:token", () =>
      HttpResponse.json(
        { code, message: code, request_id: "req_confirm" },
        { status },
      ),
    ),
  );
}

function renderAt(
  entry: string | { pathname: string; search?: string; state?: unknown },
  signedIn = true,
) {
  useAuthStore.setState({
    session: signedIn
      ? {
          accessToken: fixtures.session.access_token,
          refreshToken: fixtures.session.refresh_token,
          user: fixtures.session.user,
        }
      : null,
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

describe("W2-16 confirm dialog", () => {
  it("confirms with one POST and shows the success notice", async () => {
    const user = userEvent.setup();
    const hits = spyConfirm();
    const { search } = proposalSearch();
    const router = renderAt(`/app/confirm${search}`);

    expect(await screen.findByTestId("confirm-summary")).toHaveTextContent(SUMMARY);
    expect(screen.getByTestId("confirm-token")).toHaveTextContent(TOKEN);
    expect(screen.getByTestId("confirm-token").className).toContain("font-mono");
    expect(screen.getByTestId("confirm-band").className).toContain("bg-marigold");
    const countdown = screen.getByTestId("confirm-countdown");
    expect(countdown.className).toContain("tabular-nums");
    expect(countdown.textContent).toMatch(/\d{2,}:\d{2}/);
    expect(countdown).not.toHaveTextContent("00:00");
    expect(screen.getByText("Expira")).toBeInTheDocument();
    expect(screen.getByTestId("confirm-dialog").querySelector(".koi")).toBeNull();

    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByTestId("app-notice")).toHaveTextContent("Acción confirmada.");
    expect(router.state.location.pathname).toBe("/app");
    expect(hits).toEqual([{ method: "POST", token: TOKEN, body: "" }]);
  });

  it("discards with one DELETE and does not POST", async () => {
    const user = userEvent.setup();
    const hits = spyConfirm();
    const { search } = proposalSearch();
    const router = renderAt(`/app/confirm${search}`);

    await screen.findByTestId("confirm-summary");
    await user.click(screen.getByRole("button", { name: "Descartar" }));

    expect(await screen.findByTestId("app-notice")).toHaveTextContent(
      "Propuesta descartada. No se ejecutó nada.",
    );
    expect(router.state.location.pathname).toBe("/app");
    expect(hits).toEqual([{ method: "DELETE", token: TOKEN, body: "" }]);
  });

  it("shows confirmation_not_found and disables both actions", async () => {
    const user = userEvent.setup();
    failConfirm(404, "confirmation_not_found");
    const { search } = proposalSearch();
    const router = renderAt(`/app/confirm${search}`);

    await screen.findByTestId("confirm-summary");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByText("No encontramos la confirmación solicitada.")).toBeInTheDocument();
    expect(screen.getByText("confirmation_not_found")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeDisabled();
    expect(router.state.location.pathname).toBe("/app/confirm");
  });

  it("shows confirmation_expired and leaves Descartar available", async () => {
    const user = userEvent.setup();
    failConfirm(410, "confirmation_expired");
    const { search } = proposalSearch();
    const router = renderAt(`/app/confirm${search}`);

    await screen.findByTestId("confirm-summary");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(await screen.findByText("La confirmación ya expiró.")).toBeInTheDocument();
    expect(screen.getByText("confirmation_expired")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeEnabled();
    expect(router.state.location.pathname).toBe("/app/confirm");
  });

  it("shows confirmation_action_mismatch and disables Confirmar", async () => {
    const user = userEvent.setup();
    failConfirm(409, "confirmation_action_mismatch");
    const { search } = proposalSearch();
    const router = renderAt(`/app/confirm${search}`);

    await screen.findByTestId("confirm-summary");
    await user.click(screen.getByRole("button", { name: "Confirmar" }));

    expect(
      await screen.findByText("La confirmación no corresponde a esta acción."),
    ).toBeInTheDocument();
    expect(screen.getByText("confirmation_action_mismatch")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeDisabled();
    expect(router.state.location.pathname).toBe("/app/confirm");
  });

  it("shows the empty state and sends no confirm request without a query", async () => {
    const hits = spyConfirm();
    renderAt("/app/confirm");

    expect(
      await screen.findByRole("heading", { name: "Falta una confirmación válida" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Abrí el enlace con el token, el resumen y la hora de expiración."),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("confirm-dialog")).not.toBeInTheDocument();
    expect(hits).toEqual([]);
  });

  it("redirects /app/confirmacion and keeps the query and state", async () => {
    const { proposal, search } = proposalSearch();
    const state = wireFor(proposal);
    const router = renderAt({ pathname: "/app/confirmacion", search, state });

    expect(await screen.findByTestId("confirm-summary")).toHaveTextContent(SUMMARY);
    expect(router.state.location.pathname).toBe("/app/confirm");
    expect(router.state.location.search).toContain(`token=${TOKEN}`);
    expect(router.state.location.state).toEqual(state);
  });

  it("reads the proposal from location state when the query is empty", async () => {
    const { proposal } = proposalSearch();
    renderAt({ pathname: "/app/confirm", state: wireFor(proposal) });

    expect(await screen.findByTestId("confirm-summary")).toHaveTextContent(SUMMARY);
    expect(screen.getByTestId("confirm-token")).toHaveTextContent(TOKEN);
  });

  it("sends guests to login", async () => {
    const { search } = proposalSearch();
    renderAt({ pathname: "/app/confirm", search }, false);

    expect(await screen.findByRole("heading", { name: "Iniciar sesión" })).toBeInTheDocument();
    expect(screen.queryByTestId("confirm-dialog")).not.toBeInTheDocument();
  });

  it("disables Confirmar on the local clock and still discards", async () => {
    const user = userEvent.setup();
    const hits = spyConfirm();
    const { search } = proposalSearch(new Date(Date.now() - 1000));
    renderAt(`/app/confirm${search}`);

    expect(await screen.findByTestId("confirm-countdown")).toHaveTextContent("00:00");
    expect(screen.getByText("La propuesta parece vencida.")).toBeInTheDocument();
    expect(screen.queryByText("confirmation_expired")).not.toBeInTheDocument();
    expect(screen.queryByText("La confirmación ya expiró.")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Descartar" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Descartar" }));

    expect(await screen.findByTestId("app-notice")).toHaveTextContent(
      "Propuesta descartada. No se ejecutó nada.",
    );
    expect(hits).toEqual([{ method: "DELETE", token: TOKEN, body: "" }]);
  });

  it("leaves the token pending when Escape closes the dialog", async () => {
    const user = userEvent.setup();
    const hits = spyConfirm();
    const { search } = proposalSearch();
    const router = renderAt(`/app/confirm${search}`);

    await screen.findByTestId("confirm-dialog");
    await user.keyboard("{Escape}");

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/app");
    });
    expect(screen.queryByTestId("app-notice")).not.toBeInTheDocument();
    expect(hits).toEqual([]);
  });
});
