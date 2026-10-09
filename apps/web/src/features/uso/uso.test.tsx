import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

function renderUso(entry = "/app/uso?month=2026-09") {
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

describe("W2-09 Uso del mes e historial de facturas", () => {
  it("changes month, updates the usage request state, and shows empty months", async () => {
    const user = userEvent.setup();
    const router = renderUso("/app/uso?month=2026-09");

    expect(await screen.findByRole("heading", { name: "Septiembre 2026" })).toBeInTheDocument();
    expect(await screen.findByTestId("kpi-instance-hours")).toHaveTextContent("172.5");
    expect(screen.getAllByText("inventario-demo").length).toBeGreaterThan(0);
    expect(await screen.findByText("KOI-202609-0001")).toBeInTheDocument();
    expect(screen.getByText("Subtotal")).toBeInTheDocument();
    expect(screen.getByText("IVA 12 %")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Mes"), "2026-08");

    await waitFor(() => {
      expect(router.state.location.search).toBe("?month=2026-08");
    });
    expect(await screen.findByRole("heading", { name: "Agosto 2026" })).toBeInTheDocument();
    expect(screen.getByText("Sin uso en Agosto 2026")).toBeInTheDocument();
    expect(screen.getByText(/No hay factura emitida/i)).toBeInTheDocument();
  });

  it("downloads the invoice PDF blob from the backend endpoint", async () => {
    const user = userEvent.setup();
    const createObjectURL = vi.fn(() => "blob:invoice-pdf");
    const revokeObjectURL = vi.fn();
    const click = vi.fn();

    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeObjectURL,
    });

    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, "createElement").mockImplementation((tagName: string) => {
      const element = originalCreateElement(tagName);
      if (tagName === "a") {
        Object.defineProperty(element, "click", { value: click });
      }
      return element;
    });

    let sawPdf = false;
    server.use(
      http.get("*/api/v1/invoices/:invoiceId/pdf", () => {
        sawPdf = true;
        const pdfBytes = new TextEncoder().encode("%PDF-1.4\n%test\n");
        return new HttpResponse(pdfBytes, {
          status: 200,
          headers: { "Content-Type": "application/pdf" },
        });
      }),
    );

    renderUso("/app/uso?month=2026-09");
    expect(await screen.findByText("KOI-202609-0001")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Descargar factura PDF" }));

    await waitFor(() => {
      expect(sawPdf).toBe(true);
      expect(createObjectURL).toHaveBeenCalled();
      expect(click).toHaveBeenCalled();
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:invoice-pdf");
    });
  });

  it("keeps KPI numbers tied to the usage fixture without free-form totals", async () => {
    renderUso("/app/uso?month=2026-09");

    expect(await screen.findByTestId("kpi-instance-hours")).toHaveTextContent("172.5");
    expect(screen.getByTestId("kpi-storage-gb-hours")).toHaveTextContent("43.6");
    expect(screen.getByText("$5.00")).toBeInTheDocument();
    expect(screen.getAllByText(fixtures.usage.ponds[1].pond_name).length).toBeGreaterThan(0);
  });
});
