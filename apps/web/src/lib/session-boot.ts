import { useAuthStore, type AuthSession } from "@/lib/auth-store";

const STORAGE_KEY = "koicloud.session";

function isAuthSession(value: unknown): value is AuthSession {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Partial<AuthSession>;
  return (
    typeof candidate.accessToken === "string" &&
    typeof candidate.refreshToken === "string" &&
    typeof candidate.user === "object" &&
    candidate.user !== null
  );
}

/** Restore session from sessionStorage without editing auth-store.ts. */
export function restoreSessionFromStorage(): void {
  if (useAuthStore.getState().session) {
    return;
  }

  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const parsed: unknown = JSON.parse(raw);
    if (isAuthSession(parsed)) {
      useAuthStore.getState().setSession(parsed);
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

/** Keep sessionStorage in sync with the in-memory auth store. */
export function subscribeSessionPersistence(): () => void {
  return useAuthStore.subscribe((state) => {
    if (state.session) {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state.session));
    } else {
      sessionStorage.removeItem(STORAGE_KEY);
    }
  });
}
