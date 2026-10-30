import createClient from "openapi-fetch";
import type { components, paths } from "@/api/schema";
import type { AuthSession } from "@/lib/auth-store";
import { useAuthStore } from "@/lib/auth-store";

const RETRY_HEADER = "x-koi-refresh-retry";

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

type ApiProblem = components["schemas"]["ErrorResponse"];
type RefreshResponse = components["schemas"]["TokenPairResponse"];
type MeResponse = components["schemas"]["MeResponse"];

let refreshInflight: Promise<RefreshResponse | null> | null = null;

function resolveApiUrl(path: string) {
  const base = apiBaseUrl.trim();
  if (!base) {
    return new URL(path, window.location.origin).toString();
  }

  return new URL(path, base).toString();
}

async function readProblem(response: Response): Promise<ApiProblem | null> {
  try {
    const payload = (await response.clone().json()) as unknown;
    if (
      typeof payload === "object" &&
      payload !== null &&
      typeof (payload as { code?: unknown }).code === "string" &&
      typeof (payload as { message?: unknown }).message === "string"
    ) {
      return payload as ApiProblem;
    }
  } catch {
    return null;
  }

  return null;
}

async function requestRefresh(refreshToken: string | null) {
  const response = await fetch(resolveApiUrl("/api/v1/auth/refresh"), {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(refreshToken ? { refresh_token: refreshToken } : {}),
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as RefreshResponse;
}

function refreshTokens(refreshToken: string | null) {
  if (refreshInflight) {
    return refreshInflight;
  }

  refreshInflight = requestRefresh(refreshToken).finally(() => {
    refreshInflight = null;
  });
  return refreshInflight;
}

export async function restoreSession(): Promise<AuthSession | null> {
  const refreshed = await refreshTokens(null);
  if (!refreshed) {
    return null;
  }

  const me = await fetch(resolveApiUrl("/api/v1/me"), {
    credentials: "include",
    headers: {
      Authorization: `Bearer ${refreshed.access_token}`,
    },
  });
  if (!me.ok) {
    return null;
  }

  const profile = (await me.json()) as MeResponse;
  return {
    accessToken: refreshed.access_token,
    refreshToken: refreshed.refresh_token,
    user: profile.user,
  };
}

function mergeRequestHeaders(input: RequestInfo | URL, init: RequestInit = {}): Headers {
  // openapi-fetch often passes a Request as `input` with headers/body already set.
  // Building Headers only from init drops Request Content-Type and breaks FastAPI JSON bodies.
  const headers = new Headers(input instanceof Request ? input.headers : undefined);
  if (init.headers) {
    new Headers(init.headers).forEach((value, key) => {
      headers.set(key, value);
    });
  }
  return headers;
}

function requestHasJsonBody(input: RequestInfo | URL, init: RequestInit = {}): boolean {
  if (init.body instanceof FormData) return false;
  if (init.body !== undefined && init.body !== null) return true;
  if (!(input instanceof Request)) return false;
  if (input.body === null || input.bodyUsed) return false;
  const method = (init.method ?? input.method).toUpperCase();
  return method !== "GET" && method !== "HEAD";
}

const fetchWithRefresh: typeof fetch = async (input, init = {}) => {
  const headers = mergeRequestHeaders(input, init);
  const session = useAuthStore.getState().session;

  if (session?.accessToken) {
    headers.set("Authorization", `Bearer ${session.accessToken}`);
  }

  if (!headers.has("Content-Type") && requestHasJsonBody(input, init)) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(input, {
    ...init,
    headers,
    credentials: init.credentials ?? "include",
  });

  if (headers.get(RETRY_HEADER) === "1" || response.status !== 401) {
    return response;
  }

  const problem = await readProblem(response);
  if (problem?.code !== "token_expired") {
    return response;
  }

  const sessionNow = useAuthStore.getState().session;
  if (!sessionNow) {
    return response;
  }
  const refreshed = await refreshTokens(sessionNow.refreshToken ? sessionNow.refreshToken : null);
  if (!refreshed) {
    useAuthStore.getState().clearSession();
    return response;
  }

  useAuthStore.getState().updateTokens({
    accessToken: refreshed.access_token,
    refreshToken: refreshed.refresh_token,
  });

  const retryHeaders = mergeRequestHeaders(input, init);
  retryHeaders.set(RETRY_HEADER, "1");
  retryHeaders.set("Authorization", `Bearer ${refreshed.access_token}`);

  if (!retryHeaders.has("Content-Type") && requestHasJsonBody(input, init)) {
    retryHeaders.set("Content-Type", "application/json");
  }

  return fetch(input, {
    ...init,
    headers: retryHeaders,
    credentials: init.credentials ?? "include",
  });
};

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  fetch: fetchWithRefresh,
});
