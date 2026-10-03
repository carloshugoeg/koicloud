import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { server } from "@/mocks/server";

function renderAuthRoute(initialEntry: string) {
  useAuthStore.setState({ session: null });
  const router = createMemoryRouter(appRoutes, { initialEntries: [initialEntry] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

describe("W2-01 Auth flows (register, verify, login)", () => {
  it("registers a new account, shows the 24h verification copy, and does not log in implicitly", async () => {
    const user = userEvent.setup();
    renderAuthRoute("/register");

    expect(await screen.findByRole("heading", { name: "Crea tu cuenta" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Nombre completo"), "Ana López");
    await user.type(screen.getByLabelText("Correo"), "ana@ejemplo.gt");
    await user.type(screen.getByLabelText("Contraseña"), "Sup3rSegura!2026");
    await user.type(screen.getByLabelText("NIT (opcional)"), "0614-100199-102-4");
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));

    expect(await screen.findByRole("heading", { name: "Revisa tu correo" })).toBeInTheDocument();
    expect(screen.getByText(/ana@ejemplo\.gt/i)).toBeInTheDocument();
    expect(screen.getByText(/Vence en 24 horas/i)).toBeInTheDocument();
    expect(screen.getByText("email_verified = false")).toBeInTheDocument();
    expect(useAuthStore.getState().session).toBeNull();
  });

  it("displays code-based error when registration fails with email_taken", async () => {
    server.use(
      http.post("*/api/v1/auth/register", () =>
        HttpResponse.json({ code: "email_taken", message: "Taken", request_id: "req_1" }, { status: 409 }),
      ),
    );
    const user = userEvent.setup();
    renderAuthRoute("/register");

    await user.type(screen.getByLabelText("Nombre completo"), "Ana López");
    await user.type(screen.getByLabelText("Correo"), "ana@ejemplo.gt");
    await user.type(screen.getByLabelText("Contraseña"), "Sup3rSegura!2026");
    await user.click(screen.getByRole("button", { name: "Crear cuenta" }));

    expect(await screen.findByText("Ese correo ya está registrado.")).toBeInTheDocument();
    expect(screen.getByText("email_taken")).toBeInTheDocument();
  });

  it("consumes a valid verification token and navigates to login", async () => {
    const user = userEvent.setup();
    const router = renderAuthRoute("/verify?token=verify_token_123");

    expect(await screen.findByText("email_verified = true")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continuar a iniciar sesión" }));
    await waitFor(() => expect(router.state.location.pathname).toBe("/login"));
  });

  it("shows translated error message by code without stack trace when verification token is invalid or expired", async () => {
    server.use(
      http.post("*/api/v1/auth/verify", () =>
        HttpResponse.json({ code: "token_expired", message: "Expired", request_id: "req_2" }, { status: 401 }),
      ),
    );
    renderAuthRoute("/verify?token=expired_token_999");

    expect(await screen.findByText("Tu sesión expiró. Iniciá sesión otra vez.")).toBeInTheDocument();
    expect(screen.getByText("token_expired")).toBeInTheDocument();
  });

  it("logs in, persists session in auth store, and redirects to /app or next param", async () => {
    const user = userEvent.setup();
    const router = renderAuthRoute("/login?next=/app/plans");

    await user.type(screen.getByLabelText("Correo"), "demo@koicloud.dev");
    await user.type(screen.getByLabelText("Contraseña"), "Sup3rSegura!2026");
    await user.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    await waitFor(() => {
      expect(useAuthStore.getState().session?.accessToken).toBe("access_demo_token");
      expect(router.state.location.pathname).toBe("/app/plans");
    });
  });

  it("shows code-based error on login failure (invalid_credentials / email_not_verified)", async () => {
    server.use(
      http.post("*/api/v1/auth/login", () =>
        HttpResponse.json({ code: "email_not_verified", message: "Unverified", request_id: "req_3" }, { status: 403 }),
      ),
    );
    const user = userEvent.setup();
    renderAuthRoute("/login");

    await user.type(screen.getByLabelText("Correo"), "ana@ejemplo.gt");
    await user.type(screen.getByLabelText("Contraseña"), "Sup3rSegura!2026");
    await user.click(screen.getByRole("button", { name: "Iniciar sesión" }));

    expect(await screen.findByText("Verificá tu correo antes de continuar.")).toBeInTheDocument();
    expect(screen.getByText("email_not_verified")).toBeInTheDocument();
    expect(useAuthStore.getState().session).toBeNull();
  });
});

describe("W2-02 Forgot and reset password flows", () => {
  it("shows a neutral confirmation after forgot submit regardless of email existence", async () => {
    const user = userEvent.setup();
    renderAuthRoute("/forgot");

    expect(await screen.findByRole("heading", { name: "Recuperar acceso" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Correo"), "ghost@ejemplo.gt");
    await user.click(screen.getByRole("button", { name: "Enviar enlace" }));

    expect(await screen.findByRole("heading", { name: "Revisa tu correo" })).toBeInTheDocument();
    expect(screen.getByText(/ghost@ejemplo\.gt/i)).toBeInTheDocument();
    expect(screen.getByText(/no confirmamos si el correo está registrado/i)).toBeInTheDocument();
  });

  it("resets password with a valid token and shows the final success state", async () => {
    const user = userEvent.setup();
    renderAuthRoute("/reset?token=reset_token_123");

    expect(await screen.findByRole("heading", { name: "Restablecer contraseña" })).toBeInTheDocument();
    await user.type(screen.getByLabelText("Nueva contraseña"), "NuevaClave!2026");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "NuevaClave!2026");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));

    expect(await screen.findByRole("heading", { name: "Contraseña actualizada" })).toBeInTheDocument();
    expect(screen.getByText("password_reset = true")).toBeInTheDocument();
  });

  it("shows code-based error and recovery exit when reset token is expired", async () => {
    server.use(
      http.post("*/api/v1/auth/reset", () =>
        HttpResponse.json({ code: "token_expired", message: "Expired", request_id: "req_reset" }, { status: 401 }),
      ),
    );
    const user = userEvent.setup();
    renderAuthRoute("/reset?token=expired_reset");

    await user.type(screen.getByLabelText("Nueva contraseña"), "NuevaClave!2026");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "NuevaClave!2026");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));

    expect(await screen.findByText("Tu sesión expiró. Iniciá sesión otra vez.")).toBeInTheDocument();
    expect(screen.getByText("token_expired")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Volver a recuperar acceso" })).toBeInTheDocument();
  });

  it("shows password_too_weak inline from code when reset rejects the password", async () => {
    server.use(
      http.post("*/api/v1/auth/reset", () =>
        HttpResponse.json(
          { code: "password_too_weak", message: "Weak", request_id: "req_weak" },
          { status: 422 },
        ),
      ),
    );
    const user = userEvent.setup();
    renderAuthRoute("/reset?token=reset_token_weak");

    await user.type(screen.getByLabelText("Nueva contraseña"), "short");
    await user.type(screen.getByLabelText("Confirmar contraseña"), "short");
    await user.click(screen.getByRole("button", { name: "Guardar contraseña" }));

    expect(await screen.findByText("La contraseña no cumple los requisitos mínimos.")).toBeInTheDocument();
    expect(screen.getByText("password_too_weak")).toBeInTheDocument();
  });
});
