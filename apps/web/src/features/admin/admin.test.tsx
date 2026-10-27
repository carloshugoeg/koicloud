import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import {
  adminClientUser,
  adminSuspendedUser,
  adminUser,
  demoUser,
  fixtures,
} from "@/mocks/fixtures";
import { resetAdminUsersState } from "@/mocks/handlers";
import { server } from "@/mocks/server";

function sessionUserFromAdmin(user: typeof adminUser) {
  return {
    id: user.id,
    email: user.email,
    full_name: user.full_name,
    role: user.role,
    status: user.status,
    email_verified: user.email_verified,
    nit: "0614-220999-101-3",
    created_at: user.created_at,
  };
}

function renderAdmin(entry: string, asAdmin = true) {
  useAuthStore.setState({
    session: {
      accessToken: asAdmin ? "access_admin_token" : "access_demo_token",
      refreshToken: asAdmin ? "refresh_admin_token" : "refresh_demo_token",
      user: asAdmin ? sessionUserFromAdmin(adminUser) : demoUser,
    },
  });

  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
  return router;
}

describe("W2-10 Panel admin", () => {
  beforeEach(() => {
    resetAdminUsersState();
  });

  it("renders the users table with plan and pond counts by owner_email", async () => {
    renderAdmin("/app/admin/users");

    expect(await screen.findByTestId("admin-users-page")).toBeInTheDocument();
    expect(screen.getByText(adminClientUser.full_name)).toBeInTheDocument();
    expect(screen.getByText(adminSuspendedUser.email)).toBeInTheDocument();
    expect(screen.getAllByText("micro").length).toBeGreaterThan(0);
    expect(await screen.findByTestId(`pond-count-${adminClientUser.id}`)).toHaveTextContent("1");
    expect(screen.getByTestId(`pond-count-${adminSuspendedUser.id}`)).toHaveTextContent("1");
    expect(screen.getByTestId(`pond-count-${adminUser.id}`)).toHaveTextContent("0");

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText("Estado"), "suspended");
    expect(screen.queryByText(adminClientUser.full_name)).not.toBeInTheDocument();
    expect(screen.getByText(adminSuspendedUser.full_name)).toBeInTheDocument();
  });

  it("closes the suspend dialog on Escape and returns focus to that row Suspender", async () => {
    const user = userEvent.setup();
    renderAdmin("/app/admin/users");
    await screen.findByTestId("admin-users-page");

    const suspendBtn = screen.getByTestId(`suspend-${adminClientUser.id}`);
    await user.click(suspendBtn);

    const dialog = await screen.findByRole("dialog", { name: /Suspender a/i });
    expect(dialog).toHaveAttribute("aria-labelledby", "suspend-dialog-title");
    expect(dialog).toHaveAttribute("aria-modal", "true");

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: /Suspender a/i })).not.toBeInTheDocument();
    });
    expect(suspendBtn).toHaveFocus();
  });

  it("suspends a user after email confirmation and motivo", async () => {
    const user = userEvent.setup();
    renderAdmin("/app/admin/users");
    await screen.findByTestId("admin-users-page");

    await user.click(screen.getByTestId(`suspend-${adminClientUser.id}`));
    const dialog = await screen.findByTestId("suspend-dialog");
    expect(within(dialog).getByText(/siguen corriendo/i)).toBeInTheDocument();
    expect(within(dialog).getByText(/queda en la bitácora/i)).toBeInTheDocument();

    expect(screen.getByTestId("suspend-submit")).toBeDisabled();
    await user.type(screen.getByTestId("suspend-confirm-email"), adminClientUser.email);
    expect(screen.getByTestId("suspend-submit")).toBeEnabled();
    await user.type(screen.getByTestId("suspend-motivo"), "abuso de recursos");
    expect(screen.getByTestId("suspend-submit")).toBeEnabled();

    await user.click(screen.getByTestId("suspend-submit"));
    await waitFor(() => {
      expect(screen.queryByTestId("suspend-dialog")).not.toBeInTheDocument();
    });
    expect(await screen.findByTestId(`reactivate-${adminClientUser.id}`)).toBeInTheDocument();

    renderAdmin("/app/admin/audit");
    const reasonRow = await screen.findByTestId("audit-row-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa01");
    expect(reasonRow).toHaveTextContent("suspend_user");
    expect(reasonRow).toHaveTextContent("reason=abuso de recursos");
  });

  it("keeps the suspend dialog open and shows suspend-error on API failure", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/admin/users/:userId/suspend", () =>
        HttpResponse.json(
          {
            code: "confirmation_action_mismatch",
            message: "confirmation_action_mismatch",
          },
          { status: 409 },
        ),
      ),
    );

    renderAdmin("/app/admin/users");
    await screen.findByTestId("admin-users-page");
    await user.click(screen.getByTestId(`suspend-${adminClientUser.id}`));
    await user.type(screen.getByTestId("suspend-confirm-email"), adminClientUser.email);
    await user.type(screen.getByTestId("suspend-motivo"), "prueba");
    await user.click(screen.getByTestId("suspend-submit"));

    expect(await screen.findByTestId("suspend-error")).toHaveTextContent(
      "La confirmación no corresponde a esta acción.",
    );
    expect(screen.getByTestId("suspend-dialog")).toBeInTheDocument();
  });

  it("renders ponds with Spanish state labels in filters and badges", async () => {
    const user = userEvent.setup();
    renderAdmin("/app/admin/ponds");
    expect(await screen.findByTestId("admin-ponds-page")).toBeInTheDocument();
    expect(screen.getByText("inventario-demo")).toBeInTheDocument();

    const stateSelect = screen.getByLabelText("Estado");
    expect(within(stateSelect).getByRole("option", { name: "En cola" })).toBeInTheDocument();
    expect(within(stateSelect).getByRole("option", { name: "Eliminando…" })).toBeInTheDocument();
    expect(within(stateSelect).getByRole("option", { name: "Eliminado" })).toBeInTheDocument();
    expect(
      within(screen.getByTestId("admin-pond-row-66666666-6666-6666-6666-666666666666")).getByText(
        /En línea/,
      ),
    ).toBeInTheDocument();

    await user.selectOptions(stateSelect, "failed");
    expect(screen.queryByText("inventario-demo")).not.toBeInTheDocument();
    expect(screen.getByText("analytics-gt")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("admin-pond-row-77777777-7777-7777-7777-777777777777")).getByText(
        /Con fallas/,
      ),
    ).toBeInTheDocument();
  });

  it("shows — for pond counts when GET /admin/ponds fails", async () => {
    server.use(
      http.get("*/api/v1/admin/ponds", () =>
        HttpResponse.json(
          { code: "internal_error", message: "internal_error" },
          { status: 500 },
        ),
      ),
    );

    renderAdmin("/app/admin/users");
    expect(await screen.findByTestId("admin-users-page")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId(`pond-count-${adminClientUser.id}`)).toHaveTextContent("—");
    });
    expect(screen.getByTestId(`pond-count-${adminSuspendedUser.id}`)).toHaveTextContent("—");
    expect(screen.getByTestId(`pond-count-${adminUser.id}`)).toHaveTextContent("—");
  });

  it("shows — for pond counts and a more-results note when ponds return next_cursor", async () => {
    server.use(
      http.get("*/api/v1/admin/ponds", () =>
        HttpResponse.json({
          ponds: fixtures.adminPonds,
          next_cursor: "page-2",
        }),
      ),
      http.get("*/api/v1/admin/users", () =>
        HttpResponse.json({
          users: fixtures.adminUsers,
          next_cursor: "users-page-2",
        }),
      ),
    );

    renderAdmin("/app/admin/users");
    expect(await screen.findByTestId("admin-users-page")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId(`pond-count-${adminClientUser.id}`)).toHaveTextContent("—");
    });
    expect(screen.getByTestId("admin-more-results")).toHaveTextContent(
      /Hay más resultados en el servidor/,
    );
  });

  it("renders every audit event the backend returns, including reactivate_user", async () => {
    renderAdmin("/app/admin/audit");
    expect(await screen.findByTestId("admin-audit-page")).toBeInTheDocument();
    expect(screen.getByTestId(`audit-row-${fixtures.adminAuditEvents[0].id}`)).toHaveTextContent(
      "suspend_user",
    );
    expect(screen.getByTestId(`audit-row-${fixtures.adminAuditEvents[4].id}`)).toHaveTextContent(
      "reactivate_user",
    );
    const firstRow = screen.getByTestId(`audit-row-${fixtures.adminAuditEvents[0].id}`);
    expect(firstRow.closest("ul")?.className ?? "").toContain("font-mono");
    expect(firstRow).toHaveTextContent("responsable");
    expect(firstRow).toHaveTextContent("objetivo");
  });

  it("shows admin_only forbidden state for non-admins", async () => {
    renderAdmin("/app/admin/users", false);
    expect(await screen.findByTestId("admin-forbidden")).toBeInTheDocument();
    expect(screen.getByText("Esta pantalla es solo para administradores.")).toBeInTheDocument();
    expect(screen.getByText("admin_only")).toBeInTheDocument();
  });
});
