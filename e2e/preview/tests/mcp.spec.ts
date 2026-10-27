import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { loadGateCreds, secretValues } from "./support/creds";
import { artifactsDir, installApiProxy, publicPreviewOrigin } from "./support/proxy";
import { resetSession } from "./support/session";

type McpRow = { tool: string; result: "pass" | "fail"; note: string };
type RpcPayload = Record<string, unknown>;

const READ_TOOLS = [
  "whoami",
  "list_ponds",
  "get_pond",
  "get_connection",
  "list_subscriptions",
  "list_backups",
] as const;

const MUT_TOOLS = [
  "create_pond",
  "delete_pond",
  "restore_backup",
  "run_sql",
  "confirm_action",
  "cancel_confirmation",
] as const;

test.beforeEach(async ({ page }) => {
  resetSession();
  await installApiProxy(page);
});

test("mcp tools via preview /mcp", async ({ page, baseURL }) => {
  test.setTimeout(180_000);
  const creds = loadGateCreds();
  const hidden = secretValues(creds);
  const preview = (baseURL ?? publicPreviewOrigin()).replace(/\/$/, "");
  expect(preview).toContain(".vercel.app");
  expect(preview).not.toContain("127.0.0.1");

  await page.goto("/");
  expect(page.url()).toContain(".vercel.app");

  const mcpUrl = `${preview}/mcp`;
  const auth = basicAuth(creds.mcp.slug, creds.mcp.password);
  const rows: McpRow[] = [];
  // Unique name per run — a leftover mcp-gate-pond makes confirm_action fail with
  // pond_name_taken after propose still returned a token.
  const pondName = `mcp-gate-${Date.now().toString(36).slice(-6)}`;

  const record = (tool: string, result: "pass" | "fail", note: string) => {
    rows.push({ tool, result, note: redact(note, hidden) });
  };

  const authFail = await browserFetchStatus(page, mcpUrl, {
    method: "POST",
    headers: {
      authorization: basicAuth("not-a-agent", "wrong-password"),
      accept: "application/json",
      "content-type": "application/json",
    },
    body: {
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "gate", version: "0" },
      },
    },
  });
  const authOk = authFail.status === 401 && authFail.body.code === "agent_bad_credentials";
  record(
    "auth failure",
    authOk ? "pass" : "fail",
    authOk
      ? "HTTP 401 agent_bad_credentials"
      : `status=${authFail.status} code=${String(authFail.body.code ?? "")}`,
  );

  // Hosted preview can lag on agent_access Blob after rotate — retry handshake.
  let init: RpcPayload = {};
  let listed: RpcPayload = {};
  let names = new Set<string>();
  for (let attempt = 0; attempt < 6; attempt += 1) {
    init = await rpc(page, mcpUrl, auth, "initialize", {
      protocolVersion: "2024-11-05",
      capabilities: {},
      clientInfo: { name: "gate", version: "0" },
    });
    listed = await rpc(page, mcpUrl, auth, "tools/list", {});
    const tools = Array.isArray((listed.result as { tools?: unknown } | undefined)?.tools)
      ? ((listed.result as { tools: Array<{ name?: string }> }).tools)
      : [];
    names = new Set(tools.map((t) => t.name).filter(Boolean) as string[]);
    if (init.result && names.size > 0) break;
    await page.waitForTimeout(800 * (attempt + 1));
  }
  const needed = [...READ_TOOLS, ...MUT_TOOLS];
  if (init.result && needed.every((name) => names.has(name))) {
    record("reconnect", "pass", `initialize + tools/list (${names.size} tools)`);
  } else {
    record("reconnect", "fail", `init=${Boolean(init.result)} names=${[...names].sort().join(",")}`);
  }

  const call = (tool: string, arguments_: Record<string, unknown> = {}) =>
    rpc(page, mcpUrl, auth, "tools/call", { name: tool, arguments: arguments_ });

  const unknown = await call("no_such_tool");
  const unknownCode = toolCode(unknown);
  record(
    "unknown tool",
    unknownCode === "internal_error" ? "pass" : "fail",
    unknownCode || "missing code",
  );

  const missing = await call("get_pond", {});
  const missingCode = toolCode(missing);
  record(
    "missing args",
    missingCode === "internal_error" ? "pass" : "fail",
    missingCode || "missing code",
  );

  const who = await call("whoami");
  record(
    "whoami",
    (who.result as { email?: string } | undefined)?.email ? "pass" : "fail",
    "whoami email present",
  );

  // Best-effort purge of leftover MCP ponds from prior failed runs (same agent user).
  const prior = await call("list_ponds");
  const priorPonds =
    (prior.result as { ponds?: Array<{ name?: string }> } | undefined)?.ponds ?? [];
  if (Array.isArray(priorPonds)) {
    for (const row of priorPonds) {
      if (typeof row?.name !== "string" || !row.name.startsWith("mcp-gate")) continue;
      const doomed = await call("delete_pond", { name: row.name });
      const doomToken = (doomed.result as { token?: string } | undefined)?.token;
      if (doomToken) await call("confirm_action", { token: doomToken });
    }
  }

  const cancelProbe = await call("create_pond", { name: `${pondName}-cancel` });
  const cancelToken = (cancelProbe.result as { token?: string } | undefined)?.token;
  const cancel = await call("cancel_confirmation", { token: cancelToken || "missing" });
  const cancelOk = (cancel.result as { status?: string } | undefined)?.status === "discarded";
  record("cancel_confirmation", cancelOk ? "pass" : "fail", cancelOk ? "discarded" : "cancel failed");

  const created = await call("create_pond", { name: pondName });
  const token = (created.result as { token?: string } | undefined)?.token;
  record("create_pond", token ? "pass" : "fail", token ? "confirmation_required" : "no token");

  const confirm = await call("confirm_action", { token: token || "missing" });
  const confirmed = (confirm.result as { pond?: unknown; status?: string } | undefined) ?? {};
  const confirmCode = toolCode(confirm);
  const confirmOk = Boolean(confirmed.pond || confirmed.status === "confirmed");
  record(
    "confirm_action",
    confirmOk ? "pass" : "fail",
    confirmOk
      ? "create confirmed"
      : `confirm failed code=${confirmCode || "none"} keys=${Object.keys(confirmed).sort().join(",")}`,
  );

  const ponds = await call("list_ponds");
  record(
    "list_ponds",
    Array.isArray((ponds.result as { ponds?: unknown } | undefined)?.ponds) ? "pass" : "fail",
    "list ok",
  );

  const got = await call("get_pond", { name: pondName });
  record("get_pond", (got.result as { pond?: unknown } | undefined)?.pond ? "pass" : "fail", "get ok");

  const conn = await call("get_connection", { name: pondName });
  const connBody = (conn.result as { uri?: string; connection?: { uri?: string } } | undefined) ?? {};
  const connOk = Boolean(connBody.uri || connBody.connection?.uri);
  record("get_connection", connOk ? "pass" : "fail", connOk ? "uri present" : "missing uri");

  const subs = await call("list_subscriptions");
  record(
    "list_subscriptions",
    "subscriptions" in ((subs.result as object) || {}) ? "pass" : "fail",
    "subs",
  );

  const backups = await call("list_backups", { pond_name: pondName });
  record(
    "list_backups",
    Array.isArray((backups.result as { backups?: unknown } | undefined)?.backups) ? "pass" : "fail",
    "backups list",
  );

  const sql = await call("run_sql", { pond_name: pondName, query: "SELECT 1", mode: "read" });
  const sqlBody = (sql.result as { row_count?: number; rows?: unknown } | undefined) ?? {};
  const sqlOk = sqlBody.row_count === 1 || Array.isArray(sqlBody.rows);
  record("run_sql", sqlOk ? "pass" : "fail", "select 1");

  let pondId: string | undefined;
  const pondsBody = (ponds.result as { ponds?: Array<{ id?: string; name?: string }> } | undefined)?.ponds;
  if (Array.isArray(pondsBody)) {
    pondId = pondsBody.find((row) => row.name === pondName)?.id;
  }
  let backupId: string | undefined;
  if (typeof pondId === "string") {
    const loginJson = await browserFetch(page, `${preview}/api/v1/auth/login`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: { email: creds.user.email, password: creds.user.password },
    });
    const access = (loginJson as { access_token?: string }).access_token;
    if (typeof access === "string") {
      const bakJson = await browserFetch(page, `${preview}/api/v1/ponds/${pondId}/backups`, {
        method: "POST",
        headers: {
          "content-type": "application/json",
          authorization: `Bearer ${access}`,
        },
        body: {},
      });
      backupId = (bakJson as { backup?: { id?: string } }).backup?.id;
    }
  }

  const badRestore = await call("restore_backup", {
    pond_name: pondName,
    backup_id: "00000000-0000-0000-0000-000000000000",
  });
  const badRestoreCode = toolCode(badRestore);
  // Missing backup on an owned pond must surface catalog pond_not_found (not a token).
  record(
    "pond_not_found",
    badRestoreCode === "pond_not_found" ? "pass" : "fail",
    badRestoreCode || "missing code",
  );

  const restore = await call("restore_backup", {
    pond_name: pondName,
    backup_id: backupId || "11111111-1111-1111-1111-111111111111",
  });
  const restoreBody = (restore.result as { token?: string; isError?: unknown; code?: unknown } | undefined) ?? {};
  const restoreCode = toolCode(restore);
  const restoreOk = Boolean(restoreBody.token || restoreCode === "pond_not_found");
  record("restore_backup", restoreOk ? "pass" : "fail", "propose or domain error");
  if (restoreBody.token) {
    await call("cancel_confirmation", { token: restoreBody.token });
  }

  const deleted = await call("delete_pond", { name: pondName });
  const dtoken = (deleted.result as { token?: string } | undefined)?.token;
  record("delete_pond", dtoken ? "pass" : "fail", "confirmation_required");
  if (dtoken) {
    await call("confirm_action", { token: dtoken });
  }

  const out = path.join(artifactsDir(), "mcp-results.json");
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, `${JSON.stringify(rows, null, 2)}\n`);

  const failed = rows.filter((row) => row.result !== "pass");
  expect(failed, failed.map((row) => row.tool).join(", ")).toEqual([]);
});

async function rpc(
  page: Page,
  mcpUrl: string,
  authorization: string,
  method: string,
  params: Record<string, unknown>,
): Promise<RpcPayload> {
  // In-page fetch hits the preview-hosted /mcp (no Playwright route intercept).
  return browserFetch(page, mcpUrl, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      authorization,
      accept: "application/json",
    },
    body: { jsonrpc: "2.0", id: 1, method, params },
  });
}

function toolCode(payload: RpcPayload): string | undefined {
  const result = payload.result as
    | { structuredContent?: { code?: string }; code?: string }
    | undefined;
  if (result && typeof result === "object") {
    if (typeof result.structuredContent?.code === "string") return result.structuredContent.code;
    if (typeof result.code === "string") return result.code;
  }
  // Defensive: catalog code at the JSON-RPC envelope root (should not happen after router fix).
  if (typeof payload.code === "string") return payload.code;
  return undefined;
}

async function browserFetch(
  page: Page,
  url: string,
  init: { method: string; headers: Record<string, string>; body?: unknown },
): Promise<RpcPayload> {
  const wrapped = await browserFetchStatus(page, url, init);
  return wrapped.body;
}

async function browserFetchStatus(
  page: Page,
  url: string,
  init: { method: string; headers: Record<string, string>; body?: unknown },
): Promise<{ status: number; body: RpcPayload }> {
  try {
    return (await page.evaluate(
      async ({ url, method, headers, body }) => {
        const response = await fetch(url, {
          method,
          headers,
          body: body === undefined ? undefined : JSON.stringify(body),
        });
        const text = await response.text();
        let parsed: RpcPayload = {};
        try {
          parsed = text ? (JSON.parse(text) as RpcPayload) : {};
        } catch {
          parsed = { error: { message: `http_${response.status}` }, raw: text.slice(0, 120) };
        }
        return { status: response.status, body: parsed };
      },
      {
        url,
        method: init.method,
        headers: init.headers,
        body: init.body,
      },
    )) as { status: number; body: RpcPayload };
  } catch (error) {
    return { status: 0, body: { error: { message: String(error) } } };
  }
}

function basicAuth(user: string, password: string): string {
  return `Basic ${Buffer.from(`${user}:${password}`, "utf8").toString("base64")}`;
}

function redact(text: string, secrets: string[]): string {
  let cleaned = text;
  for (const secret of secrets) {
    if (secret.length >= 4) cleaned = cleaned.replaceAll(secret, "[redacted]");
  }
  return cleaned;
}
