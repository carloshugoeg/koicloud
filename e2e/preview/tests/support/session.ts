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
  // Hosted preview can return a one-shot internal_error on cold start; retry once.
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await page.goto("/login");
    await page.getByRole("heading", { name: "Iniciar sesión" }).waitFor();
    await page.getByLabel("Correo").fill(account.email);
    await page.getByLabel("Contraseña").fill(account.password);
    await page.getByRole("button", { name: "Iniciar sesión" }).click();
    try {
      await page.waitForURL(/\/app(?:\/|$)/, { timeout: 45_000 });
      break;
    } catch {
      const alert = page.getByRole("alert");
      const text = (await alert.isVisible()) ? await alert.innerText() : "";
      if (!/internal_error|Algo salió mal/i.test(text) || attempt === 2) {
        break;
      }
      await page.waitForTimeout(800 * (attempt + 1));
    }
  }
  // Lazily mint a helper token for api() after the SPA session is up.
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

export async function triggerBackup(page: Page, pondId: string): Promise<number> {
  const response = await api(page, "POST", `/api/v1/ponds/${pondId}/backups`);
  return response.status;
}

export async function deletePond(page: Page, pondId: string): Promise<number> {
  if (!pondId) {
    throw new Error("deletePond requires a pond id");
  }
  const first = await api(page, "DELETE", `/api/v1/ponds/${pondId}`);
  // Web surface executes immediately (no propose→confirm). Preview mock drains to deleted.
  if (first.status === 200 || first.status === 202) {
    const state = pondState(first.json);
    if (state === "deleted" || state === "deleting") {
      return first.status;
    }
    throw new Error(
      `delete HTTP ${first.status} without deleted/deleting (state=${String(state)})`,
    );
  }
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
  const confirmedState = pondState(confirmed.json);
  if (confirmedState !== "deleted" && confirmedState !== "deleting") {
    throw new Error(
      `confirm delete state=${String(confirmedState)} (HTTP ${confirmed.status})`,
    );
  }
  return confirmed.status;
}

export async function ensureProPlan(page: Page): Promise<void> {
  // Seed already puts gate-user on pro. Plans checkout may leave sandbox —
  // one subscribe to pro supersedes ACTIVE rows via confirm_payment.
  // Do not double-POST: rapid invoice allocation can 500 on preview.
  const me0 = await api(page, "GET", "/api/v1/me");
  const plan0 = (me0.json as { subscription?: { plan_id?: unknown } } | null)?.subscription
    ?.plan_id;
  if (plan0 !== "pro") {
    let lastStatus = 0;
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const token = await mintAccessToken(page);
      lastStatus = await page.evaluate(
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
      if (lastStatus < 400) break;
      // Cold-start / invoice race — brief backoff then retry.
      await page.waitForTimeout(800 * (attempt + 1));
    }
    if (lastStatus >= 400) {
      throw new Error(`ensureProPlan HTTP ${lastStatus}`);
    }
  }
  const me = await api(page, "GET", "/api/v1/me");
  const plan = (me.json as { subscription?: { plan_id?: unknown } } | null)?.subscription
    ?.plan_id;
  if (plan !== "pro") {
    throw new Error(`ensureProPlan me.plan_id=${String(plan)}`);
  }
}

export async function purgePonds(page: Page): Promise<void> {
  // MCP suite (and prior runs) can leave ponds; drain delete is async on the
  // response shape, so re-list until empty instead of a single pass.
  for (let round = 0; round < 6; round += 1) {
    const listed = await api(page, "GET", "/api/v1/ponds");
    if (listed.status >= 400 || !listed.json || typeof listed.json !== "object") {
      throw new Error(`list ponds HTTP ${listed.status}`);
    }
    const ponds = (listed.json as { ponds?: unknown }).ponds;
    if (!Array.isArray(ponds) || ponds.length === 0) return;
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
  const leftover = await api(page, "GET", "/api/v1/ponds");
  const still = (leftover.json as { ponds?: unknown } | null)?.ponds;
  if (Array.isArray(still) && still.length > 0) {
    throw new Error(`purge left ${still.length} ponds`);
  }
}
