import { describe, expect, it } from "vitest";
import {
  buildInviteConsoleSnippet,
  INVITE_CONSOLE_CLIENTS,
} from "@/features/ponds/invite-console-snippets";

const INVITE_URL = "https://koicloud.local/mcp";
const INVITE_SLUG = "pond-demo-token";
const INVITE_PASSWORD = "one-time-password";

describe("W1-208 invite console snippets (S3 registry shapes)", () => {
  it("exposes Claude Code, Cursor CLI, and Codex CLI only", () => {
    expect(INVITE_CONSOLE_CLIENTS.map((c) => c.id)).toEqual([
      "claude_code",
      "cursor_cli",
      "codex_cli",
    ]);
    expect(INVITE_CONSOLE_CLIENTS.map((c) => c.label)).toEqual([
      "Claude Code",
      "Cursor CLI",
      "Codex CLI",
    ]);
  });

  it("buildInviteConsoleSnippet matches console_snippets.py paste shapes", () => {
    const claude = buildInviteConsoleSnippet("claude_code", {
      url: INVITE_URL,
      slug: INVITE_SLUG,
      password: INVITE_PASSWORD,
    });
    expect(claude).toContain(`claude mcp add koicloud --transport http ${INVITE_URL}`);
    expect(claude).toMatch(/--header "Authorization: Basic /);

    const cursor = buildInviteConsoleSnippet("cursor_cli", {
      url: INVITE_URL,
      slug: INVITE_SLUG,
      password: INVITE_PASSWORD,
    });
    const cursorJson = JSON.parse(cursor) as {
      mcpServers: { koicloud: { url: string; headers: { Authorization: string } } };
    };
    expect(cursorJson.mcpServers.koicloud.url).toBe(INVITE_URL);
    expect(cursorJson.mcpServers.koicloud.headers.Authorization).toMatch(/^Basic /);

    const codex = buildInviteConsoleSnippet("codex_cli", {
      url: INVITE_URL,
      slug: INVITE_SLUG,
      password: INVITE_PASSWORD,
    });
    expect(codex).toContain("[mcp_servers.koicloud]");
    expect(codex).toContain(`url = "${INVITE_URL}"`);
    expect(codex).toContain("[mcp_servers.koicloud.http_headers]");
    expect(codex).toMatch(/Authorization = "Basic /);
  });

  it("uses a placeholder Authorization when password is hidden on revisit", () => {
    const snippet = buildInviteConsoleSnippet("claude_code", {
      url: INVITE_URL,
      slug: INVITE_SLUG,
      password: null,
    });
    expect(snippet).toContain("Basic <base64(slug:password)>");
    expect(snippet).not.toContain(INVITE_PASSWORD);
  });
});
