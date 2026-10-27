import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Page, Response } from "@playwright/test";

const STORE_MEDIA =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/e2e-verify";

type StashedSession = { accessToken: string; refreshToken: string };

let session: StashedSession | null = null;
let lastPondGetState = "";

export function lastPondGetStateSeen(): string {
  return lastPondGetState;
}

export function resetSession(): void {
  session = null;
  lastPondGetState = "";
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

/** True when the preview deployment itself hosts the sim (no page.route). */
export function hostedSimEnabled(): boolean {
  const flag = (process.env.KOI_HOSTED_SIM || "").trim();
  if (flag === "0") return false;
  if (flag === "1") return true;
  // Default on: preview URL is the API origin; local loopback sim is opt-in via KOI_HOSTED_SIM=0.
  return true;
}

/**
 * Attach session/pond observers. When the sim is hosted on the preview origin,
 * do not intercept /api or /mcp — the Vercel function is the real backend.
 */
export async function installApiProxy(page: Page): Promise<void> {
  page.on("response", (response) => {
    void rememberFromResponse(response);
  });
  if (hostedSimEnabled()) {
    return;
  }
  // Legacy loopback path: forward preview /api/v1 + /mcp to KOI_SIM_BASE_URL.
  const { installLoopbackForwarder } = await import("./loopback-forwarder");
  await installLoopbackForwarder(page);
}

async function rememberFromResponse(response: Response): Promise<void> {
  const url = response.url();
  let pathname = "";
  try {
    pathname = new URL(url).pathname;
  } catch {
    return;
  }
  if (response.status() !== 200 && response.request().method() !== "GET") {
    // still try pond GET below when 200
  }
  try {
    if (
      response.status() === 200 &&
      (pathname.endsWith("/auth/login") || pathname.endsWith("/auth/refresh"))
    ) {
      const body = (await response.json()) as {
        access_token?: unknown;
        refresh_token?: unknown;
      };
      if (typeof body.access_token === "string") {
        session = {
          accessToken: body.access_token,
          refreshToken: typeof body.refresh_token === "string" ? body.refresh_token : "",
        };
      }
    }
    if (response.request().method() === "GET" && /\/api\/v1\/ponds\/[^/]+$/.test(pathname)) {
      const body = (await response.json()) as { pond?: { observed_state?: unknown } };
      if (typeof body.pond?.observed_state === "string") {
        lastPondGetState = body.pond.observed_state;
      }
    }
  } catch {
    // Ignore non-JSON or already-consumed bodies.
  }
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
