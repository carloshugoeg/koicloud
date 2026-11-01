import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { fixtures } from "@/mocks/fixtures";

const POND_ID = fixtures.pond.id;
const TAB_LABELS = ["Resumen", "Respaldos", "Consola"];

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });
}

function renderPond(entry: string) {
  seedSession();
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: 0 },
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

async function expectFixedTabs(active: string) {
  const nav = await screen.findByRole("navigation", { name: "Secciones del pond" });
  const tabs = within(nav).getAllByRole("link");
  expect(tabs.map((tab) => tab.textContent)).toEqual(TAB_LABELS);
  for (const tab of tabs) {
    expect(tab.className).toMatch(/hover:/);
    expect(tab.className).toMatch(/focus-visible:shadow-focus/);
    tab.focus();
    expect(tab).toHaveFocus();
  }
  expect(within(nav).getByRole("link", { current: "page" })).toHaveTextContent(active);
}

describe("pond tabs", () => {
  it("journey: pond tabs fixed order (resumen)", async () => {
    const user = userEvent.setup();
    renderPond(`/app/ponds/${POND_ID}`);

    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    await expectFixedTabs("Resumen");

    await user.click(screen.getByRole("link", { name: "Respaldos" }));
    expect(await screen.findByTestId("backups-page")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "Resumen" }));
    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    await expectFixedTabs("Resumen");
  });

  it("journey: pond tabs fixed order (respaldos)", async () => {
    renderPond(`/app/ponds/${POND_ID}/backups`);

    expect(await screen.findByTestId("backups-page")).toBeInTheDocument();
    await expectFixedTabs("Respaldos");
  });
});
