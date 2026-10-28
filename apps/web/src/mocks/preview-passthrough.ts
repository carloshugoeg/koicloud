/**
 * Preview gate walks seed a real admin into the Preview DB while
 * VITE_ENABLE_MOCKS=true still boots MSW for the SPA demo.
 *
 * Any request that carries a Bearer token that is NOT one of the MSW demo
 * fixtures must reach the real Preview API (login JWT, /admin/**, etc.).
 */

/** Access tokens MSW itself issues. Keep in sync with fixtures / handlers. */
export const DEMO_ACCESS_TOKENS = new Set([
  "access_demo_token",
  "access_admin_token",
  "access_refreshed_token",
]);

/** Login emails MSW may answer. Everything else passthroughs to the real API. */
export const DEMO_LOGIN_EMAILS = new Set(["demo@koicloud.dev", "admin@koicloud.dev"]);

export function bearerAccessToken(request: Request): string | null {
  const header = request.headers.get("Authorization") ?? "";
  const match = /^Bearer\s+(\S+)/i.exec(header);
  return match?.[1] ?? null;
}

export function isRealPreviewBearer(request: Request): boolean {
  const token = bearerAccessToken(request);
  return token !== null && !DEMO_ACCESS_TOKENS.has(token);
}

export function isDemoLoginEmail(email: string): boolean {
  return DEMO_LOGIN_EMAILS.has(email.trim().toLowerCase());
}
