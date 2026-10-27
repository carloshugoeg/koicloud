import { expect, type Page } from "@playwright/test";
import { loadGateCreds, type Account } from "./creds";
import {
  currentAccessToken,
  publicPreviewOrigin,
  resetSession as resetProxySession,
} from "./proxy";

type Stash = { accessToken: string; refreshToken: string };
let apiSession: Stash | null = null;

export function resetSession(): void {
  resetProxySession();
  apiSession = null;
}

export async function clickNav(page: Page, label: string): Promise<void> {
  const link = page.getByRole("link", { name: label, exact: true }).first();
  const menu = page.getByTestId("nav-menu-button");
  await expect(link.or(menu)).toBeVisible();
  if (await menu.isVisible()) {
    await menu.click();
  }
  await link.click();
}

export async function login(page: Page, account: Account): Promise<void> {
  await page.goto("/login");
  await page.getByRole("heading", { name: "Iniciar sesión" }).waitFor();
  await page.getByLabel("Correo").fill(account.email);
  await page.getByLabel("Contraseña").fill(account.password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  // Lazily mint a helper token for api()/stopPond after the SPA session is up.
  // Do not block the UI login path if mint races a cold sim instance.
  try {
    await mintAccessToken(page, account);
  } catch {
    // api() will retry mint when needed.
  }
}

async function mintAccessToken(page: Page, account?: Account): Promise<string> {
  const existing = currentAccessToken() || apiSession?.accessToken;
  if (existing) return existing;
  const user = account ?? loadGateCreds().user;
  const base = publicPreviewOrigin();
  const response = await page.request.post(`${base}/api/v1/auth/login`, {
    data: { email: user.email, password: user.password },
    headers: { accept: "application/json", "content-type": "application/json" },
  });
  if (!response.ok()) {
    throw new Error(`hosted login HTTP ${response.status()}`);
  }
  const body = (await response.json()) as {
    access_token?: unknown;
    refresh_token?: unknown;
  };
  if (typeof body.access_token !== "string" || !body.access_token) {
    throw new Error("hosted login missing access_token");
  }
  apiSession = {
    accessToken: body.access_token,
    refreshToken: typeof body.refresh_token === "string" ? body.refresh_token : "",
  };
  return apiSession.accessToken;
}

export async function api(
  page: Page,
  method: string,
  apiPath: string,
): Promise<{ status: number; json: unknown }> {
  const token = await mintAccessToken(page);
  return page.evaluate(
    async ({ method, apiPath, token }) => {
      const headers: Record<string, string> = {};
      if (token) headers.Authorization = `Bearer ${token}`;
      const response = await fetch(apiPath, { method, headers });
      const text = await response.text();
      let json: unknown = null;
      try {
        json = JSON.parse(text) as unknown;
      } catch {
        json = null;
      }
      return { status: response.status, json };
    },
    { method, apiPath, token },
  );
}

function tokenFrom(json: unknown): string | null {
  if (!json || typeof json !== "object") return null;
  const token = (json as { token?: unknown }).token;
  return typeof token === "string" && token.length > 0 ? token : null;
}

function pondState(json: unknown): string | null {
  if (!json || typeof json !== "object") return null;
  const pond = (json as { pond?: { observed_state?: unknown } }).pond;
  if (!pond || typeof pond !== "object") return null;
  const state = pond.observed_state;
  return typeof state === "string" ? state : null;
}

export async function stopPond(page: Page, pondId: string): Promise<number> {
  if (!pondId) {
    throw new Error("stopPond requires a pond id");
  }
  const response = await api(page, "POST", `/api/v1/ponds/${pondId}/stop`);
  if (response.status >= 400) {
    return response.status;
  }
  if (pondState(response.json) !== "stopped") {
    throw new Error(
      `stop did not return observed_state=stopped (HTTP ${response.status})`,
    );
  }
  return response.status;
}

export async function triggerBackup(page: Page, pondId: string): Promise<number> {
  const response = await api(page, "POST", `/api/v1/ponds/${pondId}/backups`);
  return response.status;
}

export async function deletePond(page: Page, pondId: string): Promise<number> {
  if (!pondId) {
    throw new Error("deletePond requires a pond id");
  }
  const first = await api(page, "DELETE", `/api/v1/ponds/${pondId}`);
  if (first.status !== 409) {
    throw new Error(`delete propose HTTP ${first.status}`);
  }
  const token = tokenFrom(first.json);
  if (!token) {
    throw new Error("delete propose missing confirmation token");
  }
  const confirmed = await api(page, "POST", `/api/v1/confirm/${encodeURIComponent(token)}`);
  if (confirmed.status >= 400) {
    throw new Error(`confirm delete HTTP ${confirmed.status}`);
  }
  if (pondState(confirmed.json) !== "deleted") {
    throw new Error(
      `confirm delete did not return observed_state=deleted (HTTP ${confirmed.status})`,
    );
  }
  return confirmed.status;
}

export async function ensureProPlan(page: Page): Promise<void> {
  const token = await mintAccessToken(page);
  const result = await page.evaluate(
    async (accessToken) => {
      const headers: Record<string, string> = { "content-type": "application/json" };
      if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
      const response = await fetch("/api/v1/subscriptions", {
        method: "POST",
        headers,
        body: JSON.stringify({ plan_id: "pro" }),
      });
      return response.status;
    },
    token,
  );
  if (result >= 400) {
    throw new Error(`ensureProPlan HTTP ${result}`);
  }
}

export async function purgePonds(page: Page): Promise<void> {
  const listed = await api(page, "GET", "/api/v1/ponds");
  if (listed.status >= 400 || !listed.json || typeof listed.json !== "object") {
    throw new Error(`list ponds HTTP ${listed.status}`);
  }
  const ponds = (listed.json as { ponds?: unknown }).ponds;
  if (!Array.isArray(ponds)) return;
  for (const row of ponds) {
    if (!row || typeof row !== "object") continue;
    const id = (row as { id?: unknown }).id;
    if (typeof id !== "string" || !id) continue;
    const status = await deletePond(page, id);
    if (status !== 200 && status !== 202 && status !== 204) {
      throw new Error(`purge delete HTTP ${status}`);
    }
  }
}
