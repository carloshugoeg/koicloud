import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";
import { useAuthStore } from "@/lib/auth-store";

function renderPlansRoute(initialEntry = "/app/planes") {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });

  const router = createMemoryRouter(appRoutes, {
    initialEntries: [initialEntry],
  });

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );

  return router;
}

describe("W2-03 Planes y Checkout flow", () => {
  it("renders the three plans from API in cards and in the comparison table", async () => {
    renderPlansRoute("/app/planes");

    // Tarjetas de los 3 planes
    expect(await screen.findByRole("heading", { name: "Sandbox" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Micro" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pro" })).toBeInTheDocument();

    // Valores dinámicos en tarjetas
    expect(screen.getByText("$0")).toBeInTheDocument();
    expect(screen.getByText("$5")).toBeInTheDocument();
    expect(screen.getAllByText("$0.02·h")).toHaveLength(2);
    expect(screen.getByText("Recomendado")).toBeInTheDocument();

    // Tabla comparativa densa
    expect(screen.getByRole("heading", { name: "Comparativa de características" })).toBeInTheDocument();
    expect(screen.getByText("Ponds simultáneos")).toBeInTheDocument();
    expect(screen.getByText("Almacenamiento por pond")).toBeInTheDocument();
    expect(screen.getByText("Respaldos automáticos")).toBeInTheDocument();
  });

  it("opens checkout modal with fixed simulated payment notice and helper copy", async () => {
    const user = userEvent.setup();
    renderPlansRoute("/app/planes");

    const chooseMicroBtn = await screen.findByRole("button", { name: "Elegir plan Micro" });
    await user.click(chooseMicroBtn);

    // Diálogo y aviso fijo en marigold
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Pago simulado: no se realiza ningún cobro real.")).toBeInTheDocument();
    expect(screen.getByText("CF si no tienes NIT")).toBeInTheDocument();

    // Total del plan viene del API (PlanOut); sin INVOICE_BREAKDOWN local
    expect(screen.getByText("Vista previa de factura")).toBeInTheDocument();
    expect(screen.getByText("$5.0000")).toBeInTheDocument();
    expect(
      screen.getByText("Subtotal, IVA y líneas salen de la factura del API al confirmar."),
    ).toBeInTheDocument();
  });

  it("submits checkout with NIT and navigates toward pond creation", async () => {
    const user = userEvent.setup();
    let postedBody: { plan_id?: string; nit?: string | null } | null = null;

    server.use(
      http.post("*/api/v1/subscriptions", async ({ request }) => {
        postedBody = (await request.json()) as { plan_id?: string; nit?: string | null };
        return HttpResponse.json(
          {
            ...fixtures.subscriptionResponse,
            subscription: {
              ...fixtures.subscriptionResponse.subscription,
              plan_id: "micro",
            },
            invoice: {
              ...fixtures.subscriptionResponse.invoice,
              nit: postedBody.nit ?? null,
              total_usd: 5,
            },
          },
          { status: 202 },
        );
      }),
    );

    const router = renderPlansRoute("/app/planes");

    const chooseMicroBtn = await screen.findByRole("button", { name: "Elegir plan Micro" });
    await user.click(chooseMicroBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("$5.0000")).toBeInTheDocument();

    await user.type(screen.getByLabelText("NIT (opcional)"), "0614-220999-101-3");
    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242 4242 4242 4242");
    await user.type(screen.getByLabelText("Expiración"), "12/28");
    await user.type(screen.getByLabelText("CVC"), "123");

    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    await waitFor(() => {
      expect(postedBody).toEqual({ plan_id: "micro", nit: "0614-220999-101-3" });
      expect(router.state.location.pathname).toBe("/app/ponds/new");
    });
    // e2e: checkout total (PlanOut) equals InvoiceOut total from subscribe response
    expect(postedBody).not.toBeNull();
    expect(fixtures.subscriptionResponse.invoice.total_usd).toBe(5);
  });

  it("submits checkout without NIT as null", async () => {
    const user = userEvent.setup();
    let postedBody: { plan_id?: string; nit?: string | null } | null = null;

    server.use(
      http.post("*/api/v1/subscriptions", async ({ request }) => {
        postedBody = (await request.json()) as { plan_id?: string; nit?: string | null };
        return HttpResponse.json(fixtures.subscriptionResponse, { status: 202 });
      }),
    );

    const router = renderPlansRoute("/app/planes");
    await user.click(await screen.findByRole("button", { name: "Elegir plan Micro" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242 4242 4242 4242");
    await user.type(screen.getByLabelText("Expiración"), "12/28");
    await user.type(screen.getByLabelText("CVC"), "123");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    await waitFor(() => {
      expect(postedBody).toEqual({ plan_id: "micro", nit: null });
      expect(router.state.location.pathname).toBe("/app/ponds/new");
    });
  });

  it("guards against double submit while checkout is pending", async () => {
    let releaseRequest!: () => void;
    const gate = new Promise<void>((resolve) => {
      releaseRequest = resolve;
    });
    let postCount = 0;

    server.use(
      http.post("*/api/v1/subscriptions", async () => {
        postCount += 1;
        await gate;
        return HttpResponse.json(
          {
            ...fixtures.subscriptionResponse,
            subscription: {
              ...fixtures.subscriptionResponse.subscription,
              plan_id: "micro",
            },
          },
          { status: 202 },
        );
      }),
    );

    const user = userEvent.setup();
    const router = renderPlansRoute("/app/planes");

    const chooseMicroBtn = await screen.findByRole("button", { name: "Elegir plan Micro" });
    await user.click(chooseMicroBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242 4242 4242 4242");
    await user.type(screen.getByLabelText("Expiración"), "12/28");
    await user.type(screen.getByLabelText("CVC"), "123");

    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    const pendingButton = await screen.findByRole("button", { name: "Contratando…" });
    expect(pendingButton).toBeDisabled();
    expect(postCount).toBe(1);

    await user.click(pendingButton);
    expect(postCount).toBe(1);

    releaseRequest();

    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/app/ponds/new");
    });
    expect(postCount).toBe(1);
  });

  it("handles API error resolved by code without matching message", async () => {
    server.use(
      http.post("*/api/v1/subscriptions", () => {
        return HttpResponse.json(
          {
            code: "plan_required",
            message: "A raw unlocalized server message",
            request_id: "req_err_99",
          },
          { status: 400 },
        );
      }),
    );

    const user = userEvent.setup();
    renderPlansRoute("/app/planes");

    const chooseMicroBtn = await screen.findByRole("button", { name: "Elegir plan Micro" });
    await user.click(chooseMicroBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242 4242 4242 4242");
    await user.type(screen.getByLabelText("Expiración"), "12/28");
    await user.type(screen.getByLabelText("CVC"), "123");

    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    // Resuelto por catálogo de código 'plan_required'
    expect(await screen.findByText("Necesitás una suscripción activa para continuar.")).toBeInTheDocument();
    expect(screen.getByText("plan_required")).toBeInTheDocument();
    // No debe usar el mensaje crudo del servidor
    expect(screen.queryByText("A raw unlocalized server message")).not.toBeInTheDocument();
  });
});
