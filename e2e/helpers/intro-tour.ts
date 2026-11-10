import type { Page } from "@playwright/test";

/** Matches `apps/web/src/features/onboarding/intro-tour-storage.ts`. */
export const INTRO_TOUR_STORAGE_PREFIX = "koicloud:intro-tour-v1:";

/** Demo / stub client used by MSW and most journey stubs. */
export const DEMO_USER_ID = "11111111-1111-1111-1111-111111111111";

/** Admin stub in admin-users-focus.spec.ts. */
export const ADMIN_FOCUS_USER_ID = "22222222-2222-2222-2222-222222222222";

/** Admin account from `tests.admin_users_probe` (`UUID(int=PAGE_COUNT)`). */
export const ADMIN_PAGES_USER_ID = "00000000-0000-0000-0000-000000000033";

export function introTourStorageKey(userId: string) {
  return `${INTRO_TOUR_STORAGE_PREFIX}${userId}`;
}

/**
 * Seed the intro tour as already seen so existing e2e flows are not blocked by
 * the fixed inset overlay. Covers known stub IDs plus any user returned by
 * `/auth/login` or `/me` (real API seeds use random UUIDs).
 */
export async function installIntroTourSeenSeed(
  page: Page,
  extraUserIds: string[] = [],
) {
  const userIds = Array.from(
    new Set([DEMO_USER_ID, ADMIN_FOCUS_USER_ID, ADMIN_PAGES_USER_ID, ...extraUserIds]),
  );

  await page.addInitScript((ids: string[]) => {
    const PREFIX = "koicloud:intro-tour-v1:";

    function mark(userId: string) {
      window.localStorage.setItem(`${PREFIX}${userId}`, "done");
    }

    for (const id of ids) {
      mark(id);
    }

    function markFromPayload(payload: unknown) {
      if (!payload || typeof payload !== "object") {
        return;
      }
      const user = (payload as { user?: { id?: unknown } }).user;
      if (user && typeof user.id === "string" && user.id.length > 0) {
        mark(user.id);
      }
    }

    const originalFetch = window.fetch.bind(window);
    window.fetch = async (...args: Parameters<typeof fetch>) => {
      const response = await originalFetch(...args);
      try {
        const input = args[0];
        const url =
          typeof input === "string"
            ? input
            : input instanceof Request
              ? input.url
              : String(input);
        const pathname = new URL(url, window.location.origin).pathname;
        if (pathname.endsWith("/auth/login") || pathname.endsWith("/me")) {
          markFromPayload(await response.clone().json());
        }
      } catch {
        // Non-JSON or aborted — leave storage unchanged.
      }
      return response;
    };
  }, userIds);
}

/**
 * Clear the seen flag once on the app origin. Call before login in first-time
 * tour specs — do not use addInitScript here, or a later reload would clear
 * the flag the app just wrote.
 */
export async function clearIntroTourSeen(page: Page, userId: string) {
  const key = introTourStorageKey(userId);
  await page.goto("/");
  await page.evaluate((storageKey) => {
    window.localStorage.removeItem(storageKey);
  }, key);
}
