export const SNIPPET_CLIENTS = [
  { id: "claude", label: "Claude Code" },
  { id: "cursor", label: "Cursor" },
  { id: "generic", label: "Genérico" },
] as const;

export type SnippetClientId = (typeof SNIPPET_CLIENTS)[number]["id"];

const PASSWORD_PLACEHOLDER = "<password>";
const BASIC_PLACEHOLDER = "Basic <base64(slug:password)>";

function basicAuthorization(slug: string, password: string) {
  const bytes = new TextEncoder().encode(`${slug}:${password}`);
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return `Basic ${btoa(binary)}`;
}

export function buildAgentSnippet(
  client: SnippetClientId,
  access: { url: string; slug: string; password: string | null },
) {
  const secret = access.password ?? PASSWORD_PLACEHOLDER;
  const basic = access.password ? basicAuthorization(access.slug, access.password) : BASIC_PLACEHOLDER;

  if (client === "claude") {
    return `claude mcp add koicloud --transport http ${access.url} --header "Authorization: ${basic}"`;
  }

  if (client === "cursor") {
    return JSON.stringify(
      {
        mcpServers: {
          koicloud: {
            url: access.url,
            headers: {
              Authorization: basic,
              "X-KOI-Agent-Password": secret,
            },
          },
        },
      },
      null,
      2,
    );
  }

  return [`URL ${access.url}`, `Authorization: ${basic}`, `X-KOI-Agent-Password: ${secret}`].join(
    "\n",
  );
}
