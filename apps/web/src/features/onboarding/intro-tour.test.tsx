import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

/** Must match the production key helper once implemented. */
function tourStorageKey(userId: string) {
  return `koicloud:intro-tour-v1:${userId}`;
}

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });
}

function renderApp(entry: string) {
  seedSession();
  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

describe("W1-55 Intro tour", () => {
  beforeEach(() => {
    window.localStorage.removeItem(tourStorageKey(demoUser.id));
  });

  afterEach(() => {
    window.localStorage.removeItem(tourStorageKey(demoUser.id));
    cleanup();
  });

  it("shows the intro cards once for a user who has not finished the tour", async () => {
    renderApp("/app/ponds");

    const tour = await screen.findByTestId("intro-tour");
    expect(tour).toBeInTheDocument();
    expect(within(tour).getByTestId("intro-tour-cards")).toBeInTheDocument();
    expect(within(tour).getByRole("button", { name: /omitir/i })).toBeInTheDocument();
  });

  it("does not show the tour again after skip is persisted", async () => {
    const user = userEvent.setup();
    renderApp("/app/ponds");

    const tour = await screen.findByTestId("intro-tour");
    await user.click(within(tour).getByRole("button", { name: /omitir/i }));

    await waitFor(() => {
      expect(screen.queryByTestId("intro-tour")).not.toBeInTheDocument();
    });
    expect(window.localStorage.getItem(tourStorageKey(demoUser.id))).toBe("done");

    cleanup();
    renderApp("/app/ponds");

    await screen.findByTestId("sidebar-rail");
    expect(screen.queryByTestId("intro-tour")).not.toBeInTheDocument();
  });

  it("replays the tour from the Cuenta page", async () => {
    const user = userEvent.setup();
    window.localStorage.setItem(tourStorageKey(demoUser.id), "done");
    renderApp("/app/account");

    await screen.findByTestId("account-page");
    expect(screen.queryByTestId("intro-tour")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("replay-intro-tour"));

    const tour = await screen.findByTestId("intro-tour");
    expect(tour).toBeInTheDocument();
    expect(window.localStorage.getItem(tourStorageKey(demoUser.id))).not.toBe("done");
  });

  it("points coachmarks at the real nav items for ponds, planes and cuenta", async () => {
    const user = userEvent.setup();
    renderApp("/app/ponds");

    const tour = await screen.findByTestId("intro-tour");
    const cards = within(tour).getByTestId("intro-tour-cards");
    await user.click(within(cards).getByRole("button", { name: /siguiente/i }));
    await user.click(within(cards).getByRole("button", { name: /siguiente/i }));
    await user.click(within(cards).getByRole("button", { name: /siguiente/i }));

    const coach = await screen.findByTestId("intro-tour-coachmark");
    expect(coach).toHaveTextContent("Aquí ves tus ponds");
    expect(document.querySelector('[data-tour-target="ponds"]')).toBeTruthy();

    await user.click(within(coach).getByRole("button", { name: /siguiente/i }));
    expect(await screen.findByTestId("intro-tour-coachmark")).toHaveTextContent(
      "Aquí ves tus planes",
    );
    expect(document.querySelector('[data-tour-target="plans"]')).toBeTruthy();

    await user.click(
      within(screen.getByTestId("intro-tour-coachmark")).getByRole("button", {
        name: /siguiente/i,
      }),
    );
    expect(await screen.findByTestId("intro-tour-coachmark")).toHaveTextContent(
      "Aquí ves tu cuenta",
    );
    expect(document.querySelector('[data-tour-target="account"]')).toBeTruthy();
  });
});

describe("W1-55 Toasts on catalog errors", () => {
  beforeEach(() => {
    window.localStorage.setItem(tourStorageKey(demoUser.id), "done");
  });

  afterEach(() => {
    window.localStorage.removeItem(tourStorageKey(demoUser.id));
    cleanup();
  });

  it("shows a toast with the catalog message when creating a pond fails", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/ponds", () =>
        HttpResponse.json(
          {
            code: "quota_exceeded",
            message: "quota",
            request_id: "req_quota_toast",
          },
          { status: 409 },
        ),
      ),
    );

    seedSession();
    const router = createMemoryRouter(appRoutes, {
      initialEntries: ["/app/ponds/new"],
    });
    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>,
    );

    await user.type(await screen.findByTestId("create-pond-name"), "inventario-mvp");
    await user.click(screen.getByTestId("create-pond-submit"));

    const toastNode = await screen.findByTestId("toast");
    expect(toastNode).toHaveTextContent("Alcanzaste el máximo de ponds de tu plan.");
    expect(fixtures.session.user.id).toBe(demoUser.id);
  });
});
