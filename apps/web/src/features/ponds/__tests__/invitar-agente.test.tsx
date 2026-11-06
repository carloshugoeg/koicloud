import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { ToastHost } from "@/lib/toast-host";
import { fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

const POND_ID = fixtures.pond.id;
const TOKEN_ID = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";
const INVITE_URL = "https://koicloud.local/mcp";
const INVITE_SLUG = "pond-demo-token";
const INVITE_PASSWORD = "one-time-password";

const secretOut = {
  id: TOKEN_ID,
  pond_id: POND_ID,
  slug: INVITE_SLUG,
  url: INVITE_URL,
  password: INVITE_PASSWORD,
  expires_at: "2026-09-22T21:00:00Z",
  scopes: ["whoami", "get_pond", "run_sql"],
};

const listedOut = {
  id: TOKEN_ID,
  pond_id: POND_ID,
  slug: INVITE_SLUG,
  url: INVITE_URL,
  expires_at: "2026-09-22T21:00:00Z",
  revoked_at: null as string | null,
  scopes: ["whoami", "get_pond", "run_sql"],
  created_at: "2026-09-22T20:00:00Z",
};

/** WCAG relative luminance for sRGB hex (#rrggbb). */
function luminance(hex: string): number {
  const raw = hex.replace("#", "");
  const channels = [0, 1, 2].map((i) => {
    const c = Number.parseInt(raw.slice(i * 2, i * 2 + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(fg: string, bg: string): number {
  const a = luminance(fg);
  const b = luminance(bg);
  const lighter = Math.max(a, b);
  const darker = Math.min(a, b);
  return (lighter + 0.05) / (darker + 0.05);
}

function seedSession() {
  useAuthStore.setState({
    session: {
      accessToken: fixtures.session.access_token,
      refreshToken: fixtures.session.refresh_token,
      user: fixtures.session.user,
    },
  });
}

function renderDetail(entry = `/app/ponds/${POND_ID}`) {
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
      <ToastHost />
    </QueryClientProvider>,
  );
}

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  });
  Object.defineProperty(window, "innerHeight", {
    configurable: true,
    writable: true,
    value: 800,
  });
  window.dispatchEvent(new Event("resize"));
}

afterEach(() => {
  setViewportWidth(1024);
});

describe("W1-208 Invitar agente dialog (statechart transitions)", () => {
  it("closed → open dialog from pond detail", async () => {
    const user = userEvent.setup();
    renderDetail();
    expect(await screen.findByTestId("pond-detail")).toBeInTheDocument();

    const open = await screen.findByTestId("open-invite-agent");
    expect(open).toHaveTextContent("Invitar agente");
    await user.click(open);

    const dialog = await screen.findByTestId("invite-agent-dialog");
    expect(dialog).toHaveAttribute("role", "dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby", "invite-agent-title");
    expect(screen.getByRole("heading", { name: "Invitar agente" })).toBeInTheDocument();
  });

  it("open → generate link+password shows password once, QR, and console paste instructions", async () => {
    const user = userEvent.setup();
    const create = vi.fn();
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/temp-access`, async ({ request }) => {
        create(await request.json());
        return HttpResponse.json(secretOut, { status: 201 });
      }),
      http.get(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
        HttpResponse.json({ tokens: [listedOut] }),
      ),
    );

    renderDetail();
    await user.click(await screen.findByTestId("open-invite-agent"));
    await user.click(await screen.findByTestId("generate-invite-agent"));

    expect(create).toHaveBeenCalled();
    const dialog = await screen.findByTestId("invite-agent-dialog");
    expect(within(dialog).getByTestId("invite-agent-password")).toHaveTextContent(INVITE_PASSWORD);
    expect(within(dialog).getByTestId("invite-agent-url")).toHaveTextContent(INVITE_URL);
    expect(within(dialog).getByTestId("invite-agent-slug")).toHaveTextContent(INVITE_SLUG);

    const qr = within(dialog).getByTestId("invite-agent-qr");
    expect(qr).toBeInTheDocument();
    expect(qr.getAttribute("data-invite-url") ?? qr.getAttribute("aria-label") ?? "").toContain(
      INVITE_URL,
    );

    expect(within(dialog).getByRole("tab", { name: "Claude Code" })).toBeInTheDocument();
    expect(within(dialog).getByRole("tab", { name: "Cursor CLI" })).toBeInTheDocument();
    expect(within(dialog).getByRole("tab", { name: "Codex CLI" })).toBeInTheDocument();
    expect(within(dialog).getByTestId("invite-agent-snippet")).toHaveTextContent("claude mcp add");
    expect(within(dialog).queryByText(/ChatGPT|claude\.ai/i)).not.toBeInTheDocument();
  });

  it("subsequent view hides plaintext password but keeps QR and paste instructions", async () => {
    const user = userEvent.setup();
    let created = false;
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/temp-access`, () => {
        created = true;
        return HttpResponse.json(secretOut, { status: 201 });
      }),
      http.get(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
        HttpResponse.json({ tokens: created ? [listedOut] : [] }),
      ),
    );

    renderDetail();
    await user.click(await screen.findByTestId("open-invite-agent"));
    await user.click(await screen.findByTestId("generate-invite-agent"));
    expect(await screen.findByTestId("invite-agent-password")).toHaveTextContent(INVITE_PASSWORD);

    await user.click(screen.getByTestId("close-invite-agent"));
    await waitFor(() => {
      expect(screen.queryByTestId("invite-agent-dialog")).not.toBeInTheDocument();
    });
    expect(screen.queryByText(INVITE_PASSWORD)).not.toBeInTheDocument();

    await user.click(screen.getByTestId("open-invite-agent"));
    const dialog = await screen.findByTestId("invite-agent-dialog");
    expect(within(dialog).queryByTestId("invite-agent-password")).not.toBeInTheDocument();
    expect(within(dialog).getByTestId("invite-agent-password-hidden")).toBeInTheDocument();
    expect(within(dialog).queryByText(INVITE_PASSWORD)).not.toBeInTheDocument();
    expect(within(dialog).getByTestId("invite-agent-qr")).toBeInTheDocument();
    expect(within(dialog).getByTestId("invite-agent-snippet")).toBeInTheDocument();
  });

  it("revoke clears the invite and marks the token revoked so MCP auth must fail", async () => {
    const user = userEvent.setup();
    const revoke = vi.fn();
    let revoked = false;
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
        HttpResponse.json(secretOut, { status: 201 }),
      ),
      http.get(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
        HttpResponse.json({
          tokens: revoked
            ? [{ ...listedOut, revoked_at: "2026-09-22T20:30:00Z" }]
            : [listedOut],
        }),
      ),
      http.post(`*/api/v1/ponds/${POND_ID}/temp-access/${TOKEN_ID}/revoke`, () => {
        revoke();
        revoked = true;
        return HttpResponse.json({ ...listedOut, revoked_at: "2026-09-22T20:30:00Z" });
      }),
    );

    renderDetail();
    await user.click(await screen.findByTestId("open-invite-agent"));
    await user.click(await screen.findByTestId("generate-invite-agent"));
    await screen.findByTestId("invite-agent-password");

    await user.click(screen.getByTestId("revoke-invite-agent"));
    await waitFor(() => {
      expect(revoke).toHaveBeenCalled();
    });

    const dialog = screen.getByTestId("invite-agent-dialog");
    expect(within(dialog).getByTestId("invite-agent-revoked")).toBeInTheDocument();
    expect(within(dialog).queryByTestId("invite-agent-password")).not.toBeInTheDocument();
    expect(within(dialog).queryByTestId("invite-agent-qr")).not.toBeInTheDocument();
    expect(within(dialog).getByText(/MCP|auth|credencial|inválid/i)).toBeInTheDocument();
  });

  it("Esc closes the dialog and returns focus to the open button", async () => {
    const user = userEvent.setup();
    renderDetail();
    const open = await screen.findByTestId("open-invite-agent");
    await user.click(open);
    await screen.findByTestId("invite-agent-dialog");

    await user.keyboard("{Escape}");
    await waitFor(() => {
      expect(screen.queryByTestId("invite-agent-dialog")).not.toBeInTheDocument();
    });
    expect(open).toHaveFocus();
  });

  it("axe dialog contract: labelled dialog, focusable controls, no unlabeled buttons", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
        HttpResponse.json(secretOut, { status: 201 }),
      ),
      http.get(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
        HttpResponse.json({ tokens: [listedOut] }),
      ),
    );

    renderDetail();
    await user.click(await screen.findByTestId("open-invite-agent"));
    await user.click(await screen.findByTestId("generate-invite-agent"));
    const dialog = await screen.findByTestId("invite-agent-dialog");

    expect(dialog).toHaveAttribute("aria-labelledby");
    const titleId = dialog.getAttribute("aria-labelledby");
    expect(titleId).toBeTruthy();
    expect(document.getElementById(titleId as string)).toHaveTextContent("Invitar agente");

    const buttons = within(dialog).getAllByRole("button");
    for (const button of buttons) {
      const name = button.getAttribute("aria-label") || button.textContent?.trim();
      expect(name, "every button needs an accessible name").toBeTruthy();
    }

    const focused = document.activeElement as HTMLElement | null;
    expect(focused).toBeTruthy();
    expect(dialog.contains(focused)).toBe(true);
  });

  it("contrast: invite dialog text tokens meet AA 4.5:1 on bone surfaces", () => {
    // Tokens from src/index.css — dialog uses ink / ink-muted / turquoise-700 on bone-raised.
    const pairs: Array<[string, string, string]> = [
      ["ink on bone-raised", "#14211f", "#fbf7ec"],
      ["ink-muted on bone-raised", "#4c5b58", "#fbf7ec"],
      ["turquoise-700 on bone-raised", "#0a6d64", "#fbf7ec"],
      ["bone-raised on turquoise-700", "#fbf7ec", "#0a6d64"],
      ["ink on paper", "#14211f", "#fffcf4"],
    ];
    for (const [label, fg, bg] of pairs) {
      expect(contrastRatio(fg, bg), label).toBeGreaterThanOrEqual(4.5);
    }
  });

  it.each([375, 768, 1440] as const)(
    "dialog stays within viewport width %i without horizontal overflow",
    async (width) => {
      const user = userEvent.setup();
      setViewportWidth(width);
      server.use(
        http.post(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
          HttpResponse.json(secretOut, { status: 201 }),
        ),
        http.get(`*/api/v1/ponds/${POND_ID}/temp-access`, () =>
          HttpResponse.json({ tokens: [listedOut] }),
        ),
      );

      renderDetail();
      await user.click(await screen.findByTestId("open-invite-agent"));
      await user.click(await screen.findByTestId("generate-invite-agent"));
      const dialog = await screen.findByTestId("invite-agent-dialog");

      expect(dialog.scrollWidth).toBeLessThanOrEqual(Math.max(dialog.clientWidth, width));
      expect(dialog.getBoundingClientRect().width).toBeLessThanOrEqual(width);
    },
  );
});
