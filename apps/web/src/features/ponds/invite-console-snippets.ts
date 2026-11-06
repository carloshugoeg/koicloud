/** Paste shapes mirrored from apps/api/app/mcp/console_snippets.py (S3 / #204). */

export const INVITE_CONSOLE_CLIENTS = [
  { id: "claude_code", label: "Claude Code" },
  { id: "cursor_cli", label: "Cursor CLI" },
  { id: "codex_cli", label: "Codex CLI" },
] as const;

export type InviteConsoleClientId = (typeof INVITE_CONSOLE_CLIENTS)[number]["id"];

const BASIC_PLACEHOLDER = "Basic <base64(slug:password)>";

function basicAuthorization(slug: string, password: string) {
  const bytes = new TextEncoder().encode(`${slug}:${password}`);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return `Basic ${btoa(binary)}`;
}

export function buildInviteConsoleSnippet(
  clientId: InviteConsoleClientId,
  access: { url: string; slug: string; password: string | null },
) {
  const basic = access.password
    ? basicAuthorization(access.slug, access.password)
    : BASIC_PLACEHOLDER;

  if (clientId === "claude_code") {
    return (
      `claude mcp add koicloud --transport http ${access.url} ` +
      `--header "Authorization: ${basic}"`
    );
  }

  if (clientId === "cursor_cli") {
    return JSON.stringify(
      {
        mcpServers: {
          koicloud: {
            url: access.url,
            headers: { Authorization: basic },
          },
        },
      },
      null,
      2,
    );
  }

  return [
    "[mcp_servers.koicloud]",
    `url = "${access.url}"`,
    "",
    "[mcp_servers.koicloud.http_headers]",
    `Authorization = "${basic}"`,
    "",
  ].join("\n");
}
