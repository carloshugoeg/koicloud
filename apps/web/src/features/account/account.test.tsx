import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

function renderAccount() {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/account"] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

describe("E1-05 Cuenta", () => {
  it("renders profile, changes password, and shows success", async () => {
    const user = userEvent.setup();
    renderAccount();

    const page = await screen.findByTestId("account-page");
    expect(page).toBeInTheDocument();
    expect(screen.getByDisplayValue(demoUser.full_name)).toBeInTheDocument();
    expect(page).toHaveTextContent(demoUser.email);

    await user.type(screen.getByTestId("account-current-password"), "Sup3rSegura!2026");
    await user.type(screen.getByTestId("account-new-password"), "NuevaClave!2026");
    await user.click(screen.getByTestId("change-password-submit"));

    expect(await screen.findByTestId("password-saved")).toHaveTextContent(
      "Contraseña actualizada",
    );
  });

  it("shows password_too_weak without calling a too-short API password", async () => {
    const user = userEvent.setup();
    renderAccount();
    await screen.findByTestId("account-page");

    await user.type(screen.getByTestId("account-current-password"), "Sup3rSegura!2026");
    await user.type(screen.getByTestId("account-new-password"), "123456789");
    await user.click(screen.getByTestId("change-password-submit"));

    expect(await screen.findByText("password_too_weak")).toBeInTheDocument();
  });

  it("rejects delete when confirm_email mismatches", async () => {
    const user = userEvent.setup();
    renderAccount();
    await screen.findByTestId("account-page");

    await user.click(screen.getByTestId("delete-me-open"));
    const dialog = await screen.findByTestId("delete-me-dialog");
    expect(dialog).toHaveAttribute("role", "dialog");
    expect(dialog).toHaveAttribute("aria-labelledby", "delete-account-title");
    const input = await screen.findByTestId("delete-confirm-email");
    await user.type(input, "otro@koicloud.dev");
    expect(screen.getByTestId("delete-me-submit")).toBeDisabled();

    await user.clear(input);
    await user.type(input, demoUser.email);
    await user.click(screen.getByTestId("delete-me-submit"));

    await waitFor(() => {
      expect(useAuthStore.getState().session).toBeNull();
    });
  });

  it("closes delete dialog on Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();
    renderAccount();
    await screen.findByTestId("account-page");

    const trigger = screen.getByTestId("delete-me-open");
    await user.click(trigger);
    expect(await screen.findByTestId("delete-me-dialog")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByTestId("delete-me-dialog")).not.toBeInTheDocument();
    });
    expect(trigger).toHaveFocus();
  });

  it("shows email_mismatch from the API when confirm fails server-side", async () => {
    const user = userEvent.setup();
    server.use(
      http.delete("*/api/v1/me", () =>
        HttpResponse.json(
          {
            code: "email_mismatch",
            message: "El correo no coincide.",
            request_id: "req_mm",
          },
          { status: 422 },
        ),
      ),
    );
    renderAccount();
    await screen.findByTestId("account-page");
    await user.click(screen.getByTestId("delete-me-open"));
    await user.type(screen.getByTestId("delete-confirm-email"), demoUser.email);
    await user.click(screen.getByTestId("delete-me-submit"));
    expect(await screen.findByText("email_mismatch")).toBeInTheDocument();
  });

  it("resends verification when the account is unverified", async () => {
    const user = userEvent.setup();
    server.use(
      http.get("*/api/v1/me", () =>
        HttpResponse.json({
          user: { ...fixtures.session.user, email_verified: false },
          ponds_count: 0,
          subscription: null,
        }),
      ),
    );
    renderAccount();
    expect(await screen.findByTestId("account-resend")).toBeInTheDocument();
    await user.click(screen.getByTestId("resend-verification"));
    expect(await screen.findByTestId("resend-ok")).toBeInTheDocument();
  });
});
