/**
 * E2E-style check (issue #96 amendment): /app/planes and checkout must show the
 * same Pro price that GET /plans returns — not a hard-coded frontend value.
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { formatPrice } from "@/lib/format-price";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";
import { useAuthStore } from "@/lib/auth-store";

const API_ROOT = "*/api/v1";

/** Distinct from any historical hard-code (0.02) so the UI must follow the API. */
const API_PRO_UNIT_PRICE = 0.0875;

function renderPlanes() {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });

  const router = createMemoryRouter(appRoutes, {
    initialEntries: ["/app/planes"],
  });

  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );

  return router;
}

describe("E2E: plans page + checkout mirror GET /plans Pro price", () => {
  it("cards, comparison table and checkout show the Pro unit_price from GET /plans", async () => {
    const plansFromApi = fixtures.plans.map((plan) =>
      plan.id === "pro"
        ? {
            ...plan,
            billing_model: "hourly" as const,
            unit_price: API_PRO_UNIT_PRICE,
            currency: "USD",
            price_monthly_usd: 0,
          }
        : plan,
    );

    let capturedProUnitPrice: number | undefined;
    server.use(
      http.get(`${API_ROOT}/plans`, () => {
        const pro = plansFromApi.find((p) => p.id === "pro");
        capturedProUnitPrice = pro?.unit_price;
        return HttpResponse.json({ plans: plansFromApi, next_cursor: null });
      }),
    );

    const user = userEvent.setup();
    renderPlanes();

    expect(await screen.findByTestId("plan-card-pro")).toBeInTheDocument();
    expect(capturedProUnitPrice).toBe(API_PRO_UNIT_PRICE);

    const expected = formatPrice({
      unit_price: capturedProUnitPrice!,
      currency: "USD",
    });
    expect(expected).toBe("USD 0.0875");

    // Plan card
    expect(screen.getByTestId("plan-card-pro")).toHaveTextContent(expected);
    // Comparison table "Precio base" row
    expect(screen.getByText(`${expected} / hora`)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Elegir plan Pro" }));
    const dialog = await screen.findByRole("dialog");
    expect(dialog).toHaveTextContent(`Precio de catálogo: ${expected}`);
    // Must never show a zero catalog price for Pro when API returns a rate
    expect(dialog).not.toHaveTextContent("USD 0.00");
    expect(screen.getByTestId("plan-card-pro")).not.toHaveTextContent("USD 0.00");
  });
});
