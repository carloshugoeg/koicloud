import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const NIT_ERROR = "El NIT no es válido. Usá los dígitos y el dígito verificador, o CF.";
const CARD_ERROR = "El número de tarjeta no es válido.";
const EXPIRY_ERROR = "La expiración debe ser MM/AA y no estar vencida.";
const CVV_ERROR = "El CVV debe tener 3 dígitos, o 4 si es American Express.";
const DECLINE_ERROR = "El pago simulado fue rechazado. Revisá la tarjeta.";

function renderEntry(entry: string) {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
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

async function openCheckout() {
  const user = userEvent.setup();
  renderEntry("/app/uso");
  await user.click(await screen.findByRole("button", { name: "Cambiar de plan" }));
  await user.click(await screen.findByRole("button", { name: "Elegir plan Micro" }));
  expect(await screen.findByRole("dialog")).toBeInTheDocument();
  return user;
}

async function fillCard(user: ReturnType<typeof userEvent.setup>, number: string, expiry: string, cvc: string) {
  await user.type(screen.getByLabelText("Número de tarjeta simulada"), number);
  await user.type(screen.getByLabelText("Expiración"), expiry);
  await user.type(screen.getByLabelText("CVC"), cvc);
}

describe("Uso y facturación", () => {
  it("redirects the old plan and billing routes to one screen", async () => {
    for (const entry of ["/app/plans", "/app/planes", "/app/billing", "/app/usage"]) {
      cleanup();
      const router = renderEntry(entry);
      expect(await screen.findByRole("heading", { name: "Uso y facturación" })).toBeInTheDocument();
      expect(router.state.location.pathname).toBe("/app/uso");
    }
  });

  it("opens plans from Tu plan actual", async () => {
    const user = userEvent.setup();
    renderEntry("/app/uso");

    expect(await screen.findByRole("heading", { name: "Tu plan actual" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Planes" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Cambiar de plan" }));
    expect(await screen.findByRole("button", { name: "Elegir plan Micro" })).toBeInTheDocument();
  });

  it("blocks an invalid NIT before posting", async () => {
    let posts = 0;
    server.use(
      http.post("*/api/v1/subscriptions", () => {
        posts += 1;
        return HttpResponse.json({ code: "nit_invalid", message: NIT_ERROR }, { status: 422 });
      }),
    );
    const user = await openCheckout();
    await user.type(screen.getByLabelText("NIT (opcional)"), "0614-220999-101-3");
    await fillCard(user, "4242424242424242", "12/30", "123");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    expect(await screen.findByText(NIT_ERROR)).toBeInTheDocument();
    expect(posts).toBe(0);
  });

  it("blocks a card that fails Luhn, a past expiry, and a short CVV", async () => {
    let posts = 0;
    server.use(
      http.post("*/api/v1/subscriptions", () => {
        posts += 1;
        return HttpResponse.json({}, { status: 202 });
      }),
    );
    const user = await openCheckout();
    await fillCard(user, "4242424242424241", "12/30", "123");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));
    expect(await screen.findByText(CARD_ERROR)).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Número de tarjeta simulada"));
    await user.clear(screen.getByLabelText("Expiración"));
    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242424242424242");
    await user.type(screen.getByLabelText("Expiración"), "01/20");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));
    expect(await screen.findByText(EXPIRY_ERROR)).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Expiración"));
    await user.clear(screen.getByLabelText("CVC"));
    await user.type(screen.getByLabelText("Expiración"), "12/30");
    await user.type(screen.getByLabelText("CVC"), "12");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));
    expect(await screen.findByText(CVV_ERROR)).toBeInTheDocument();
    expect(posts).toBe(0);
  });

  it("requires 4 CVV digits for American Express", async () => {
    const user = await openCheckout();
    await fillCard(user, "378282246310005", "12/30", "123");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));
    expect(await screen.findByText(CVV_ERROR)).toBeInTheDocument();
  });

  it("shows the payment decline and does not show a successful invoice", async () => {
    server.use(
      http.post("*/api/v1/subscriptions", () => {
        return HttpResponse.json(
          { code: "payment_declined", message: DECLINE_ERROR, request_id: "req_decline" },
          { status: 422 },
        );
      }),
    );
    const user = await openCheckout();
    await user.type(screen.getByLabelText("NIT (opcional)"), "CF");
    await fillCard(user, "4242424242424242", "12/30", "123");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(DECLINE_ERROR);
    expect(screen.queryByTestId("checkout-invoice-from-api")).not.toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Tu plan actual" })).toBeInTheDocument();
    });
  });
});
