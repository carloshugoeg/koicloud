import { render, screen } from "@testing-library/react";
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

    // Valores dinámicos en tarjetas (desde GET /plans via formatPrice, 4 dp)
    expect(screen.getAllByText("USD 0.0000").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("USD 5.0000").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("USD 0.0200").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Recomendado")).toBeInTheDocument();
    expect(screen.getByText("USD 0.0200 / hora")).toBeInTheDocument();

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

    // Solo precio de catálogo — sin subtotal/IVA/total del cliente (CCR #151)
    expect(screen.getByTestId("checkout-catalog-price")).toBeInTheDocument();
    expect(screen.getAllByText("USD 5.0000").length).toBeGreaterThanOrEqual(1);
    expect(screen.queryByText("USD 4.4643")).not.toBeInTheDocument();
    expect(screen.queryByText("USD 0.5357")).not.toBeInTheDocument();
    expect(screen.queryByTestId("checkout-invoice-from-api")).not.toBeInTheDocument();
  });

  it("shows the same Pro unit_price from GET /plans on cards and checkout", async () => {
    const user = userEvent.setup();
    renderPlansRoute("/app/planes");

    const pro = fixtures.plans.find((p) => p.id === "pro")!;
    const expected = `USD ${Number(pro.unit_price).toFixed(4)}`;
    expect(await screen.findByTestId("plan-card-pro")).toHaveTextContent(expected);
    expect(screen.getByText(`${expected} / hora`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Elegir plan Pro" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(expected);
    expect(dialog).toHaveTextContent("/ hora");
  });

  it("submits checkout and shows InvoiceOut totals from the API (no client math)", async () => {
    const user = userEvent.setup();
    renderPlansRoute("/app/planes");

    const chooseMicroBtn = await screen.findByRole("button", { name: "Elegir plan Micro" });
    await user.click(chooseMicroBtn);

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.queryByText(/IVA \(12%\)/i)).not.toBeInTheDocument();

    await user.type(screen.getByLabelText("NIT (opcional)"), "0614-220999-101-3");
    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242 4242 4242 4242");
    await user.type(screen.getByLabelText("Expiración"), "12/28");
    await user.type(screen.getByLabelText("CVC"), "123");

    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    const invoicePanel = await screen.findByTestId("checkout-invoice-from-api");
    const expectedTotal = `USD ${Number(fixtures.subscriptionResponse.invoice.total_usd).toFixed(4)}`;
    expect(invoicePanel).toBeInTheDocument();
    expect(screen.getByTestId("checkout-invoice-total")).toHaveTextContent(expectedTotal);
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
    renderPlansRoute("/app/planes");

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

    expect(await screen.findByTestId("checkout-invoice-from-api")).toBeInTheDocument();
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
