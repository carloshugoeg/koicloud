import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Page, Request } from "@playwright/test";

const STORE_MEDIA =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/e2e-verify";

const FORWARD = new Set([
  "authorization",
  "content-type",
  "accept",
  "accept-language",
  "mcp-session-id",
  "mcp-protocol-version",
  "x-koi-surface",
  "x-koi-confirm-token",
  "x-koi-refresh-retry",
]);

type StashedSession = { accessToken: string; refreshToken: string };

let session: StashedSession | null = null;
let lastPondGetState = "";

export function lastPondGetStateSeen(): string {
  return lastPondGetState;
}

export function resetSession(): void {
  session = null;
}

export function currentAccessToken(): string | null {
  return session?.accessToken ?? null;
}

export function previewRoot(): string {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
}

export function artifactsDir(): string {
  return path.join(previewRoot(), "artifacts");
}

export function publicPreviewOrigin(): string {
  const fromEnv = (process.env.KOI_PUBLIC_BASE_URL || process.env.PLAYWRIGHT_BASE_URL || "").trim();
  if (fromEnv) return fromEnv.replace(/\/$/, "");
  return "https://koicloud-web-git-w1-e2e-preview-verify-hugos-projects-3379fa36.vercel.app";
}

export function assertPreviewHost(href: string): void {
  const host = new URL(href).hostname;
  if (host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0") {
    throw new Error(`refused localhost capture host=${host}`);
  }
  if (!host.endsWith(".vercel.app")) {
    throw new Error(`refused non-preview host=${host}`);
  }
}

function rewriteAgentUrls(pathname: string, bytes: Buffer): Buffer {
  if (
    !pathname.endsWith("/agent-access") &&
    !pathname.endsWith("/agent-access/rotate")
  ) {
    return bytes;
  }
  try {
    const body = JSON.parse(bytes.toString("utf8")) as Record<string, unknown>;
    const preview = publicPreviewOrigin();
    if (typeof body.url === "string") {
      body.url = `${preview}/mcp`;
    }
    return Buffer.from(JSON.stringify(body), "utf8");
  } catch {
    return bytes;
  }
}

export async function installApiProxy(page: Page): Promise<void> {
  const sim = (process.env.KOI_SIM_BASE_URL ?? "http://127.0.0.1:18080").replace(/\/$/, "");
  await page.route(/\/api\/v1(?:\/|\?|$)|\/mcp(?:\/|\?|$)/, async (route) => {
    const request = route.request();
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: cors(request) });
      return;
    }
    const url = new URL(request.url());
    const headers = new Headers();
    for (const [key, value] of Object.entries(request.headers())) {
      if (FORWARD.has(key.toLowerCase())) headers.set(key, value);
    }
    if (
      !headers.has("authorization") &&
      session?.accessToken &&
      !url.pathname.endsWith("/auth/login") &&
      !url.pathname.endsWith("/auth/register") &&
      !url.pathname.includes("/mcp")
    ) {
      headers.set("authorization", `Bearer ${session.accessToken}`);
    }
    const raw = request.postDataBuffer();
    const init: RequestInit = {
      method: request.method(),
      headers,
      redirect: "manual",
    };
    if (raw && request.method() !== "GET" && request.method() !== "HEAD") {
      init.body = new Uint8Array(raw);
    }
    let response: Response;
    try {
      response = await fetch(sim + url.pathname + url.search, init);
    } catch {
      await route.fulfill({
        status: 502,
        contentType: "application/json",
        body: JSON.stringify({ code: "internal_error", message: "sim unreachable" }),
        headers: cors(request),
      });
      return;
    }
    let bytes = Buffer.from(await response.arrayBuffer());
    bytes = rewriteAgentUrls(url.pathname, bytes);
    rememberSession(url.pathname, response.status, bytes);
    rememberPondGet(request.method(), url.pathname, bytes);
    const out: Record<string, string> = {
      ...cors(request),
      "cache-control": "no-store",
    };
    const contentType = response.headers.get("content-type");
    if (contentType) out["content-type"] = contentType;
    const mcpSession = response.headers.get("mcp-session-id");
    if (mcpSession) out["mcp-session-id"] = mcpSession;
    await route.fulfill({ status: response.status, body: bytes, headers: out });
  });
}

function rememberPondGet(method: string, pathname: string, bytes: Buffer): void {
  if (method !== "GET" || !/\/api\/v1\/ponds\/[^/]+$/.test(pathname)) return;
  try {
    const body = JSON.parse(bytes.toString("utf8")) as { pond?: { observed_state?: unknown } };
    if (typeof body.pond?.observed_state === "string") {
      lastPondGetState = body.pond.observed_state;
    }
  } catch {
    lastPondGetState = "";
  }
}

function rememberSession(pathname: string, status: number, bytes: Buffer): void {
  if (status !== 200) return;
  if (!pathname.endsWith("/auth/login") && !pathname.endsWith("/auth/refresh")) return;
  try {
    const body = JSON.parse(bytes.toString("utf8")) as {
      access_token?: unknown;
      refresh_token?: unknown;
    };
    if (typeof body.access_token !== "string") return;
    session = {
      accessToken: body.access_token,
      refreshToken: typeof body.refresh_token === "string" ? body.refresh_token : "",
    };
  } catch {
    session = null;
  }
}

function cors(request: Request): Record<string, string> {
  const origin = request.headers().origin ?? "*";
  const requested = request.headers()["access-control-request-headers"] ?? "*";
  return {
    "access-control-allow-origin": origin,
    "access-control-allow-headers": requested,
    "access-control-allow-methods": "GET,POST,PUT,PATCH,DELETE,OPTIONS",
    "access-control-allow-credentials": "true",
  };
}

const VIEWPORTS = [
  { tag: "375", width: 375, height: 812 },
  { tag: "768", width: 768, height: 1024 },
  { tag: "1440", width: 1440, height: 900 },
] as const;

function ensureWritableDir(dir: string): boolean {
  try {
    fs.mkdirSync(dir, { recursive: true });
    fs.accessSync(dir, fs.constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

function resolveMediaDir(): string | null {
  const fromEnv = process.env.KOI_E2E_MEDIA_DIR;
  if (fromEnv && fromEnv.trim()) {
    return ensureWritableDir(fromEnv) ? fromEnv : null;
  }
  return ensureWritableDir(STORE_MEDIA) ? STORE_MEDIA : null;
}

export async function capture(
  page: Page,
  slug: string,
): Promise<{ shot375: boolean; shot768: boolean; shot1440: boolean }> {
  const href = page.url();
  assertPreviewHost(href);
  // Stamp the preview origin into the shot so reviewers see the Vercel host, not loopback.
  await page.evaluate((shown) => {
    let el = document.getElementById("e2e-preview-host");
    if (!el) {
      el = document.createElement("div");
      el.id = "e2e-preview-host";
      el.setAttribute("data-testid", "e2e-preview-host");
      el.setAttribute("role", "note");
      Object.assign(el.style, {
        position: "fixed",
        left: "0",
        right: "0",
        bottom: "0",
        zIndex: "2147483647",
        padding: "6px 10px",
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
        fontSize: "12px",
        lineHeight: "16px",
        background: "rgba(13, 51, 79, 0.92)",
        color: "#F4F1EA",
        pointerEvents: "none",
      });
      document.body.appendChild(el);
    }
    el.textContent = shown;
  }, href);

  const artifacts = artifactsDir();
  const media = resolveMediaDir();
  fs.mkdirSync(artifacts, { recursive: true });
  const flags = { shot375: false, shot768: false, shot1440: false };
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const file = `${slug}-${viewport.tag}.png`;
    const local = path.join(artifacts, file);
    await page.screenshot({ path: local, fullPage: true });
    if (media) {
      fs.copyFileSync(local, path.join(media, file));
    }
    if (viewport.tag === "375") flags.shot375 = true;
    if (viewport.tag === "768") flags.shot768 = true;
    if (viewport.tag === "1440") flags.shot1440 = true;
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  return flags;
}

export type FlowRow = {
  flow: string;
  result: "pass" | "fail";
  note: string;
  shot375: boolean;
  shot768: boolean;
  shot1440: boolean;
};

export function recordFlow(row: FlowRow): void {
  const file = path.join(artifactsDir(), "ui-results.json");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const current = fs.existsSync(file)
    ? (JSON.parse(fs.readFileSync(file, "utf8")) as FlowRow[])
    : [];
  const next = current.filter((item) => item.flow !== row.flow);
  next.push(row);
  fs.writeFileSync(file, JSON.stringify(next, null, 2));
}
