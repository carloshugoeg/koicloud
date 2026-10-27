import type { Page, Request } from "@playwright/test";

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

/**
 * Legacy: Playwright page.route forwards preview /api/v1 + /mcp to a loopback sim.
 * Prefer KOI_HOSTED_SIM=1 (default) so the preview Vercel function is the backend.
 */
export async function installLoopbackForwarder(page: Page): Promise<void> {
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
    const bytes = Buffer.from(await response.arrayBuffer());
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
