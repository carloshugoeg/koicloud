import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page, type Route } from "@playwright/test";

const shotsDir = "/opt/cursor/artifacts";
const widths = [375, 768, 1440] as const;

type StubUser = {
  id: string;
  email: string;
  full_name: string;
  role: "client";
  status: "active";
  email_verified: true;
  created_at: string;
  active_subscription_plan: string;
};

function user(n: number): StubUser {
  return {
    id: `00000000-0000-4000-8000-${n.toString(16).padStart(12, "0")}`,
    email: `user${n}@koicloud.test`,
    full_name: `Usuario ${n}`,
    role: "client",
    status: "active",
    email_verified: true,
    created_at: "2026-11-01T12:00:00Z",
    active_subscription_plan: "micro",
  };
}

const roster = Array.from({ length: 120 }, (_, index) => user(index + 1));

function pageFor(cursor: string | null) {
  if (cursor == null) {
    return { users: roster.slice(0, 50), next_cursor: "c1" };
  }
  if (cursor === "c1") {
    return { users: roster.slice(50, 100), next_cursor: "c2" };
  }
  return { users: roster.slice(100), next_cursor: null };
}

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function stubSession(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    const pathname = url.pathname;
    if (route.request().method() === "POST" && pathname.endsWith("/auth/refresh")) {
      await json(route, {
        access_token: "access_admin_token",
        refresh_token: "refresh_admin_token",
      });
      return;
    }
    if (pathname.endsWith("/me")) {
      await json(route, {
        user: {
          id: "22222222-2222-2222-2222-222222222222",
          email: "admin@koicloud.test",
          full_name: "Admin Demo",
          role: "admin",
          status: "active",
          email_verified: true,
          onboarded: true,
          nit: null,
          created_at: "2026-09-01T12:00:00Z",
        },
        ponds_count: 0,
        subscription: null,
      });
      return;
    }
    if (pathname.endsWith("/admin/ponds")) {
      await json(route, { ponds: [], next_cursor: null });
      return;
    }
    if (pathname.endsWith("/admin/users")) {
      await json(route, pageFor(url.searchParams.get("cursor")));
      return;
    }
    await json(route, { code: "internal_error", message: "unstubbed" }, 500);
  });
}

function row(page: Page, n: number) {
  const id = `00000000-0000-4000-8000-${n.toString(16).padStart(12, "0")}`;
  return page.getByTestId(`admin-user-row-${id}`);
}

async function openUsers(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  await page.goto("/app/admin/users");
  await expect(page.getByTestId("admin-users-page")).toBeVisible();
  await expect(row(page, 1)).toContainText("Usuario 1");
}

async function expectRowFocused(page: Page, n: number) {
  const id = `admin-user-row-00000000-0000-4000-8000-${n.toString(16).padStart(12, "0")}`;
  const target = row(page, n);
  await expect(target).toContainText(`Usuario ${n}`);
  await expect
    .poll(
      () =>
        page.evaluate((rowId) => {
          const active = document.activeElement;
          const rowEl = document.querySelector(`[data-testid="${rowId}"]`);
          if (active && rowEl && (active === rowEl || rowEl.contains(active))) {
            return rowId;
          }
          return active === document.body ? "BODY" : (active?.tagName ?? "NONE");
        }, id),
      { timeout: 2000 },
    )
    .toBe(id);
}

test("moves focus to the first new row when the last page loads", async ({ page }) => {
  const releases: Array<() => void> = [];
  await stubSession(page);
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/admin/users") && url.searchParams.get("cursor") === "c2") {
      await new Promise<void>((resolve) => {
        releases.push(resolve);
      });
    }
    await route.fallback();
  });

  for (const width of widths) {
    await test.step(`${width}px`, async () => {
      await openUsers(page, width);
      await page.getByRole("button", { name: "Cargar más" }).click();
      await expect(row(page, 51)).toContainText("Usuario 51");
      await expect(page.getByRole("button", { name: "Cargar más" })).toBeFocused();

      const before = releases.length;
      await page.getByRole("button", { name: "Cargar más" }).click();
      const busy = page.getByRole("button", { name: "Cargando…" });
      await expect(busy).toBeFocused();
      releases[before]?.();

      await expect(row(page, 101)).toContainText("Usuario 101");
      await expect(page.getByRole("button", { name: "Cargar más" })).toHaveCount(0);
      await expectRowFocused(page, 101);

      fs.mkdirSync(shotsDir, { recursive: true });
      await page.screenshot({
        path: path.join(shotsDir, `admin-users-focus-last-${width}.png`),
        fullPage: true,
      });
    });
  }
});

test("moves focus to the first new row after Reintentar loads the page", async ({ page }) => {
  let failCursor = true;
  await stubSession(page);
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (
      url.pathname.endsWith("/admin/users") &&
      url.searchParams.get("cursor") != null &&
      failCursor
    ) {
      await json(route, { code: "internal_error", message: "internal_error" }, 500);
      return;
    }
    await route.fallback();
  });

  for (const width of widths) {
    await test.step(`${width}px`, async () => {
      failCursor = true;
      await openUsers(page, width);
      await page.getByRole("button", { name: "Cargar más" }).click();

      const alert = page.getByTestId("admin-users-page").getByRole("alert");
      await expect(alert).toContainText("No pudimos cargar más usuarios.");
      await expect(row(page, 1)).toContainText("Usuario 1");
      await expect(row(page, 51)).toHaveCount(0);
      await expect(page.getByRole("button", { name: "Cargar más" })).toBeFocused();

      failCursor = false;
      await alert.getByRole("button", { name: "Reintentar" }).click();
      await expect(row(page, 51)).toContainText("Usuario 51");
      await expect(alert).toHaveCount(0);
      await expectRowFocused(page, 51);
    });
  }
});
