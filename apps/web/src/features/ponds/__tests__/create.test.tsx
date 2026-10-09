import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const NEW_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });
}

function renderCreate() {
  seedSession();
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: 0 },
    },
  });
  const router = createMemoryRouter(appRoutes, { initialEntries: ["/app/ponds/new"] });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

describe("W2-05 Crear pond", () => {
  it("validates the name live and echoes it in mono", async () => {
    const user = userEvent.setup();
    renderCreate();

    const input = await screen.findByTestId("create-pond-name");
    await user.type(input, "AB");
    expect(screen.getByTestId("create-pond-echo")).toHaveTextContent("AB");
    expect(screen.getByTestId("create-pond-issues")).toHaveTextContent(
      "Solo minúsculas, números y guiones.",
    );
    expect(screen.getByTestId("create-pond-submit")).toBeDisabled();

    await user.clear(input);
    await user.type(input, "inventario-mvp");
    expect(screen.getByTestId("create-pond-echo")).toHaveClass("font-mono");
    expect(screen.getByTestId("create-pond-echo")).toHaveTextContent("inventario-mvp");
    expect(screen.getByText("● nombre válido")).toBeInTheDocument();
    expect(screen.queryByText("● disponible")).not.toBeInTheDocument();
    expect(screen.queryByTestId("create-pond-issues")).not.toBeInTheDocument();
    expect(screen.getByTestId("create-pond-submit")).toBeEnabled();
  });

  it("submits a valid name and opens the detail in provisioning", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/ponds", async ({ request }) => {
        const body = (await request.json()) as { name?: string };
        expect(body.name).toBe("inventario-mvp");
        return HttpResponse.json(
          {
            pond: {
              ...fixtures.pond,
              id: NEW_ID,
              name: "inventario-mvp",
              observed_state: "provisioning",
            },
            job: { id: "job_create_new", type: "create_pond", status: "queued" },
          },
          { status: 202 },
        );
      }),
      http.get(`*/api/v1/ponds/${NEW_ID}`, () =>
        HttpResponse.json({
          pond: {
            ...fixtures.pond,
            id: NEW_ID,
            name: "inventario-mvp",
            observed_state: "provisioning",
          },
        }),
      ),
    );

    renderCreate();
    const input = await screen.findByTestId("create-pond-name");
    await user.type(input, "inventario-mvp");
    await user.click(screen.getByTestId("create-pond-submit"));

    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();
    expect(screen.getByTestId("pond-status-badge")).toHaveTextContent("Aprovisionando…");
  });

  it("shows the catalog message for pond_name_taken", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/ponds", () =>
        HttpResponse.json(
          { code: "pond_name_taken", message: "taken", request_id: "req_create" },
          { status: 409 },
        ),
      ),
    );

    renderCreate();
    await user.type(await screen.findByTestId("create-pond-name"), "inventario-mvp");
    await user.click(screen.getByTestId("create-pond-submit"));

    expect(await screen.findByTestId("create-pond-error")).toHaveTextContent(
      "Ese nombre de pond ya está en uso.",
    );
  });

  it("sends plan_required to the plans catalog instead of trapping the user", async () => {
    const user = userEvent.setup();
    server.use(
      http.post("*/api/v1/ponds", () =>
        HttpResponse.json(
          { code: "plan_required", message: "need plan", request_id: "req_plan" },
          { status: 409 },
        ),
      ),
    );

    renderCreate();
    await user.type(await screen.findByTestId("create-pond-name"), "inventario-mvp");
    await user.click(screen.getByTestId("create-pond-submit"));

    const error = await screen.findByTestId("create-pond-error");
    expect(error).toHaveTextContent("Necesitás una suscripción activa para continuar.");
    expect(screen.getByRole("link", { name: "Ver planes" })).toHaveAttribute("href", "/app/plans");
  });
});
