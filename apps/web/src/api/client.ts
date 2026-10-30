import createClient from "openapi-fetch";
import type { components, paths } from "@/api/schema";
import { useAuthStore } from "@/lib/auth-store";

const RETRY_HEADER = "x-koi-refresh-retry";

export const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "";

type ApiProblem = components["schemas"]["ErrorResponse"];
type RefreshResponse = components["schemas"]["TokenPairResponse"];

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

async function refreshTokens(refreshToken: string) {
  const response = await fetch(resolveApiUrl("/api/v1/auth/refresh"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    return null;
  }

  return (await response.json()) as RefreshResponse;
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
  });

  if (headers.get(RETRY_HEADER) === "1" || response.status !== 401) {
    return response;
  }

  const problem = await readProblem(response);
  const requestUrl = response.url;
  if (
    problem?.code === "token_invalid" &&
    session?.accessToken &&
    !requestUrl.includes("/auth/")
  ) {
    useAuthStore.getState().clearSession();
    return response;
  }
  if (problem?.code !== "token_expired") {
    return response;
  }

  const currentRefreshToken = useAuthStore.getState().session?.refreshToken;
  if (!currentRefreshToken) {
    useAuthStore.getState().clearSession();
    return response;
  }

  const refreshed = await refreshTokens(currentRefreshToken);
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
  });
};

export const apiClient = createClient<paths>({
  baseUrl: apiBaseUrl,
  fetch: fetchWithRefresh,
});
