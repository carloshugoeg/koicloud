import fs from "node:fs";

export type Account = { email: string; password: string };
export type McpAccount = { slug: string; password: string };
export type GateCreds = { admin: Account; user: Account; mcp: McpAccount };

const STORE_CREDS =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/gate-access/credentials.json";

export function credentialsPath(): string {
  return process.env.KOI_GATE_CREDENTIALS_OUT ?? STORE_CREDS;
}

export function loadGateCreds(): GateCreds {
  const file = credentialsPath();
  let payload: unknown;
  try {
    payload = JSON.parse(fs.readFileSync(file, "utf8")) as unknown;
  } catch {
    throw new Error("gate credentials file is missing or unreadable");
  }
  const creds = parseCreds(payload);
  if (!creds) {
    throw new Error("gate credentials file is missing admin, user, or mcp fields");
  }
  return creds;
}

export function secretValues(payload: unknown): string[] {
  const found: string[] = [];
  walk(payload, found);
  return found;
}

function parseCreds(payload: unknown): GateCreds | null {
  if (!payload || typeof payload !== "object") return null;
  const root = payload as Record<string, unknown>;
  const users = asRecord(root.users) ?? root;
  const admin =
    account(users.admin) ??
    account(users["gate-admin"]) ??
    account(root.admin) ??
    accountByRole(root, "admin");
  const user =
    account(users.user) ??
    account(users.client) ??
    account(users["gate-user"]) ??
    account(root.user) ??
    account(root.client) ??
    accountByRole(root, "client");
  const mcp = mcpAccount(root.mcp) ?? mcpAccount(root.agent) ?? mcpFromFlat(root);
  if (!admin || !user || !mcp) return null;
  return { admin, user, mcp };
}

function account(value: unknown): Account | null {
  const rec = asRecord(value);
  if (!rec) return null;
  const email = asString(rec.email);
  const password = asString(rec.password);
  if (!email || !password) return null;
  return { email, password };
}

function mcpAccount(value: unknown): McpAccount | null {
  const rec = asRecord(value);
  if (!rec) return null;
  const slug = asString(rec.slug);
  const password = asString(rec.password) ?? asString(rec.agent_password);
  if (!slug || !password) return null;
  return { slug, password };
}

function mcpFromFlat(root: Record<string, unknown>): McpAccount | null {
  const slug = asString(root.mcp_slug) ?? asString(root.slug);
  const password = asString(root.mcp_password) ?? asString(root.agent_password);
  if (!slug || !password) return null;
  return { slug, password };
}

function accountByRole(root: Record<string, unknown>, role: string): Account | null {
  const list = root.accounts ?? root.users;
  if (!Array.isArray(list)) return null;
  for (const item of list) {
    const rec = asRecord(item);
    if (!rec) continue;
    if (asString(rec.role) === role) {
      const found = account(rec);
      if (found) return found;
    }
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}

function walk(node: unknown, found: string[]): void {
  if (!node || typeof node !== "object") return;
  if (Array.isArray(node)) {
    for (const item of node) walk(item, found);
    return;
  }
  for (const [key, value] of Object.entries(node)) {
    if (
      ["password", "token", "access_token", "refresh_token", "secret", "authorization"].includes(
        key.toLowerCase(),
      ) &&
      typeof value === "string" &&
      value.length >= 4
    ) {
      found.push(value);
    } else {
      walk(value, found);
    }
  }
}
