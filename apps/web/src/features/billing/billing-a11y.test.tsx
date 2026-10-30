import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser } from "@/mocks/fixtures";

const NIT_ERROR = "El NIT no es válido. Usá los dígitos y el dígito verificador, o CF.";
const CARD_ERROR = "El número de tarjeta no es válido.";
const EXPIRY_ERROR = "La expiración debe ser MM/AA y no estar vencida.";
const CVV_ERROR = "El CVV debe tener 3 dígitos, o 4 si es American Express.";

function renderUso() {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/uso"] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

async function openCheckout(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Cambiar de plan" }));
  await user.click(await screen.findByRole("button", { name: "Elegir plan Micro" }));
  expect(await screen.findByRole("dialog")).toBeInTheDocument();
}

function expectErrorLinked(label: string, message: string) {
  const input = screen.getByLabelText(label);
  const error = screen.getByText(message);
  expect(error.id).not.toBe("");
  expect(input.getAttribute("aria-describedby")?.split(/\s+/)).toContain(error.id);
  expect(input).toHaveAttribute("aria-invalid", "true");
}

describe("billing form errors", () => {
  it("links each checkout error to its input", async () => {
    const user = userEvent.setup();
    renderUso();
    await openCheckout(user);

    await user.type(screen.getByLabelText("NIT (opcional)"), "0614-220999-101-3");
    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242424242424241");
    await user.type(screen.getByLabelText("Expiración"), "01/20");
    await user.type(screen.getByLabelText("CVC"), "12");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    expectErrorLinked("NIT (opcional)", NIT_ERROR);
    expectErrorLinked("Número de tarjeta simulada", CARD_ERROR);
    expectErrorLinked("Expiración", EXPIRY_ERROR);
    expectErrorLinked("CVC", CVV_ERROR);
  });

  it("moves focus to the first invalid field", async () => {
    const user = userEvent.setup();
    renderUso();
    await openCheckout(user);

    await user.type(screen.getByLabelText("NIT (opcional)"), "0614-220999-101-3");
    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242424242424241");
    await user.type(screen.getByLabelText("Expiración"), "01/20");
    await user.type(screen.getByLabelText("CVC"), "12");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    expect(screen.getByLabelText("NIT (opcional)")).toHaveFocus();
  });

  it("moves focus to the card when the NIT is blank and the card is invalid", async () => {
    const user = userEvent.setup();
    renderUso();
    await openCheckout(user);

    await user.type(screen.getByLabelText("Número de tarjeta simulada"), "4242424242424241");
    await user.type(screen.getByLabelText("Expiración"), "12/30");
    await user.type(screen.getByLabelText("CVC"), "123");
    await user.click(screen.getByRole("button", { name: "Confirmar contratación" }));

    expect(screen.getByLabelText("Número de tarjeta simulada")).toHaveFocus();
    expect(screen.getByLabelText("NIT (opcional)")).not.toHaveFocus();
  });

  it("reflects whether the plan picker is open", async () => {
    const user = userEvent.setup();
    renderUso();

    const changePlan = await screen.findByRole("button", { name: "Cambiar de plan" });
    expect(changePlan).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Elegir plan Micro" })).not.toBeInTheDocument();

    await user.click(changePlan);

    expect(changePlan).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByRole("button", { name: "Elegir plan Micro" })).toBeInTheDocument();
  });

  it("closes the plan picker so aria-expanded returns to false", async () => {
    const user = userEvent.setup();
    renderUso();

    const changePlan = await screen.findByRole("button", { name: "Cambiar de plan" });
    expect(changePlan).toHaveAttribute("aria-expanded", "false");

    await user.click(changePlan);
    expect(changePlan).toHaveAttribute("aria-expanded", "true");
    expect(await screen.findByRole("button", { name: "Elegir plan Micro" })).toBeInTheDocument();

    await user.click(changePlan);
    expect(changePlan).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Elegir plan Micro" })).not.toBeInTheDocument();

    await user.click(changePlan);
    expect(changePlan).toHaveAttribute("aria-expanded", "true");
    await user.keyboard("{Escape}");
    expect(changePlan).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("button", { name: "Elegir plan Micro" })).not.toBeInTheDocument();
  });
});
