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
  it("renders the user's name and NIT", async () => {
    renderAccount();

    const page = await screen.findByTestId("account-page");
    expect(page).toBeInTheDocument();
    expect(screen.getByDisplayValue(demoUser.full_name)).toBeInTheDocument();
    expect(screen.getByDisplayValue(demoUser.nit ?? "")).toBeInTheDocument();
    expect(page).toHaveTextContent(demoUser.email);
  });

  it("saves an edited name and NIT", async () => {
    const user = userEvent.setup();
    renderAccount();
    await screen.findByTestId("account-page");

    const nameInput = screen.getByLabelText(/nombre completo/i);
    const nitInput = screen.getByLabelText(/^nit$/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Carlos Demo");
    await user.clear(nitInput);
    await user.type(nitInput, "0614-100199-102-4");
    await user.click(screen.getByRole("button", { name: /guardar cambios/i }));

    expect(await screen.findByTestId("profile-saved")).toHaveTextContent("Cambios guardados");
  });

  it("rejects a password change when new and confirm do not match", async () => {
    const user = userEvent.setup();
    renderAccount();
    await screen.findByTestId("account-page");

    await user.type(screen.getByTestId("account-current-password"), "Sup3rSegura!2026");
    await user.type(screen.getByTestId("account-new-password"), "NuevaClave!2026");
    await user.type(screen.getByTestId("account-confirm-password"), "OtraClave!2026");
    await user.click(screen.getByTestId("change-password-submit"));

    expect(await screen.findByText(/no coinciden/i)).toBeInTheDocument();
  });

  it("changes the password successfully", async () => {
    const user = userEvent.setup();
    renderAccount();
    await screen.findByTestId("account-page");

    await user.type(screen.getByTestId("account-current-password"), "Sup3rSegura!2026");
    await user.type(screen.getByTestId("account-new-password"), "NuevaClave!2026");
    await user.type(screen.getByTestId("account-confirm-password"), "NuevaClave!2026");
    await user.click(screen.getByTestId("change-password-submit"));

    expect(await screen.findByTestId("password-saved")).toHaveTextContent(
      "Contraseña actualizada",
    );
  });

  it("surfaces invalid_credentials from the API on a bad current password", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/me/change-password", () =>
        HttpResponse.json(
          {
            code: "invalid_credentials",
            message: "Correo o contraseña incorrectos.",
            request_id: "req_pw_bad",
          },
          { status: 401 },
        ),
      ),
    );
    renderAccount();
    await screen.findByTestId("account-page");

    await user.type(screen.getByTestId("account-current-password"), "WrongPass!2026");
    await user.type(screen.getByTestId("account-new-password"), "NuevaClave!2026");
    await user.type(screen.getByTestId("account-confirm-password"), "NuevaClave!2026");
    await user.click(screen.getByTestId("change-password-submit"));

    await waitFor(() => {
      expect(screen.getByText("invalid_credentials")).toBeInTheDocument();
    });
  });

  it("does not show the E1-05 scaffold placeholder copy", async () => {
    renderAccount();
    await screen.findByTestId("account-page");
    expect(screen.queryByText(/Scaffold de perfil/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Listo para conectar/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Ruta registrada/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Próximo paso/i)).not.toBeInTheDocument();
    expect(fixtures.session.user.email).toBeTruthy();
  });
});
