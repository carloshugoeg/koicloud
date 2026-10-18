import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { ROTATED_AGENT_PASSWORD } from "@/mocks/handlers";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

function renderAgentAccess(entry = "/app/acceso-agente") {
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

describe("W2-11 Acceso agente", () => {
  it("shows slug, url, enabled, and rotated_at without a password", async () => {
    renderAgentAccess();

    expect(await screen.findByTestId("agent-slug")).toHaveTextContent(fixtures.agentAccess.slug);
    expect(screen.getByTestId("agent-url")).toHaveTextContent(fixtures.agentAccess.url);
    expect(screen.getByTestId("agent-enabled")).toHaveTextContent("habilitado");
    expect(screen.getByTestId("agent-rotated-at")).toHaveTextContent("2026");
    expect(screen.getByTestId("agent-password-hidden")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-password")).not.toBeInTheDocument();
    expect(screen.queryByText(ROTATED_AGENT_PASSWORD)).not.toBeInTheDocument();
  });

  it("rotates once, copies the password, then hides it for good", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    renderAgentAccess();
    await screen.findByTestId("agent-slug");

    await user.click(screen.getByTestId("rotate-agent-password"));
    expect(await screen.findByTestId("agent-password")).toHaveTextContent(ROTATED_AGENT_PASSWORD);
    expect(screen.getByTestId("agent-password-band")).toBeInTheDocument();

    await user.click(screen.getByTestId("copy-agent-password"));
    await waitFor(() => {
      expect(writeText).toHaveBeenCalledWith(ROTATED_AGENT_PASSWORD);
    });

    await user.click(screen.getByTestId("hide-agent-password"));
    expect(screen.queryByText(ROTATED_AGENT_PASSWORD)).not.toBeInTheDocument();
    expect(screen.getByTestId("agent-password-hidden")).toBeInTheDocument();
    expect(screen.queryByTestId("agent-password")).not.toBeInTheDocument();
  });

  it("renders Claude Code, Cursor, and Genérico snippets in mono", async () => {
    const user = userEvent.setup();
    renderAgentAccess();
    await screen.findByTestId("agent-slug");

    expect(screen.getByRole("tab", { name: "Claude Code" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("agent-snippet")).toHaveTextContent("claude mcp add");
    expect(screen.getByTestId("agent-snippet").className).toContain("font-mono");

    await user.click(screen.getByRole("tab", { name: "Cursor" }));
    expect(screen.getByTestId("agent-snippet")).toHaveTextContent("mcpServers");

    await user.click(screen.getByRole("tab", { name: "Genérico" }));
    expect(screen.getByTestId("agent-snippet")).toHaveTextContent("X-KOI-Agent-Password");
    expect(screen.getByTestId("agent-snippet")).toHaveTextContent("<password>");
  });

  it("toggles enabled and shows agent_disabled by code", async () => {
    const user = userEvent.setup();
    renderAgentAccess();
    await screen.findByTestId("agent-slug");

    await user.click(screen.getByTestId("toggle-agent-access"));
    expect(await screen.findByTestId("agent-enabled")).toHaveTextContent("deshabilitado");
    expect(screen.getByTestId("agent-disabled-note")).toHaveTextContent(
      "El acceso del agente está desactivado.",
    );

    server.use(
      http.post("*/api/v1/agent-access/toggle", () =>
        HttpResponse.json(
          { code: "agent_disabled", message: "raw", request_id: "req_agent" },
          { status: 403 },
        ),
      ),
    );

    await user.click(screen.getByTestId("toggle-agent-access"));
    expect(await screen.findByTestId("agent-disabled-note")).toHaveTextContent("agent_disabled");
    expect(screen.queryByText(/traceback|stack/i)).not.toBeInTheDocument();
  });

  it("redirects the English alias to /app/acceso-agente", async () => {
    const router = renderAgentAccess("/app/agent-access");
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/app/acceso-agente");
    });
    expect(await screen.findByTestId("agent-slug")).toBeInTheDocument();
  });
});
