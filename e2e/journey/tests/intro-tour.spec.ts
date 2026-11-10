import { expect, test, type Page, type Route } from "../fixtures";
import {
  DEMO_USER_ID,
  clearIntroTourSeen,
  introTourStorageKey,
} from "../../helpers/intro-tour";

test.use({ seedIntroTourDone: false });

const user = {
  id: DEMO_USER_ID,
  email: "demo@koicloud.dev",
  full_name: "Operador Demo",
  role: "client",
  status: "active",
  email_verified: true,
  onboarded: true,
  nit: "0614-220999-101-3",
  created_at: "2026-09-22T20:00:00Z",
};

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const { pathname } = new URL(req.url());
    const method = req.method();

    if (method === "POST" && pathname.endsWith("/auth/login")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: {
          "set-cookie": "koi_refresh=refresh_e2e; Path=/api/v1; HttpOnly; SameSite=Lax",
        },
        body: JSON.stringify({
          access_token: "access_e2e",
          refresh_token: "refresh_e2e",
          user,
        }),
      });
    }
    if (method === "POST" && pathname.endsWith("/auth/refresh")) {
      const cookie = req.headers().cookie ?? "";
      if (!cookie.includes("koi_refresh=")) {
        return json(route, 401, { code: "token_invalid", message: "no cookie", request_id: "req" });
      }
      return json(route, 200, {
        access_token: "access_restored",
        refresh_token: "refresh_rotated",
      });
    }
    if (method === "GET" && pathname.endsWith("/me")) {
      return json(route, 200, { user, ponds_count: 0, subscription: null });
    }
    if (method === "GET" && pathname.endsWith("/plans")) {
      return json(route, 200, { plans: [] });
    }
    if (method === "GET" && pathname.endsWith("/usage")) {
      return json(route, 200, {
        month: "2026-10",
        days: [],
        totals: { compute_hours: 0, storage_gb_days: 0 },
      });
    }
    if (method === "GET" && pathname.endsWith("/ponds")) {
      return json(route, 200, { ponds: [], next_cursor: null });
    }
    return json(route, 404, { code: "not_found", message: pathname, request_id: "req" });
  });
}

test("first-time user sees the intro tour and can dismiss it", async ({ page }) => {
  await installApi(page);
  await clearIntroTourSeen(page, DEMO_USER_ID);

  await page.goto("/login?next=/app/ponds");
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();

  const tour = page.getByTestId("intro-tour");
  await expect(tour).toBeVisible();
  await expect(tour.getByTestId("intro-tour-cards")).toBeVisible();

  await tour.getByRole("button", { name: "Omitir" }).click();
  await expect(tour).toHaveCount(0);
  await expect(page.getByTestId("ponds-empty")).toBeVisible();
  await expect
    .poll(() => page.evaluate((key) => localStorage.getItem(key), introTourStorageKey(DEMO_USER_ID)))
    .toBe("done");
});
