export const SNIPPET_CLIENTS = [
  { id: "claude", label: "Claude Code" },
  { id: "cursor", label: "Cursor" },
  { id: "generic", label: "Genérico" },
] as const;

export type SnippetClientId = (typeof SNIPPET_CLIENTS)[number]["id"];

const PLACEHOLDER = "<password>";

export function buildAgentSnippet(
  client: SnippetClientId,
  access: { url: string; slug: string; password: string | null },
) {
  const secret = access.password ?? PLACEHOLDER;
  const basic = `Basic ${access.slug}:${secret}`;

  if (client === "claude") {
    return [
      `claude mcp add koicloud --transport http ${access.url}`,
      `# Authorization: ${basic}`,
      `# X-KOI-Agent-Password: ${secret}`,
    ].join("\n");
  }

  if (client === "cursor") {
    return JSON.stringify(
      {
        mcpServers: {
          koicloud: {
            url: access.url,
            headers: {
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
