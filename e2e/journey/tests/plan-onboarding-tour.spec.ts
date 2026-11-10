import { expect, test, type Page, type Route } from "../fixtures";
import {
  DEMO_USER_ID,
  clearIntroTourSeen,
} from "../../helpers/intro-tour";

test.use({ seedIntroTourDone: false });

const NEW_USER_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

const newUser = {
  id: NEW_USER_ID,
  email: "nuevo@koicloud.dev",
  full_name: "Usuario Nuevo",
  role: "client",
  status: "active",
  email_verified: true,
  onboarded: false,
  nit: null,
  created_at: "2026-11-10T12:00:00Z",
};

const plans = [
  {
    id: "sandbox",
    name: "Sandbox",
    description: "Gratis para probar.",
    currency: "GTQ",
    billing_model: "flat",
    unit_price: 0,
    included_compute_hours: 24,
    included_storage_gb: 1,
    max_ponds: 1,
  },
  {
    id: "micro",
    name: "Micro",
    description: "Para un proyecto chico.",
    currency: "GTQ",
    billing_model: "flat",
    unit_price: 9900,
    included_compute_hours: 720,
    included_storage_gb: 5,
    max_ponds: 2,
  },
  {
    id: "pro",
    name: "Pro",
    description: "Más ponds y almacenamiento.",
    currency: "GTQ",
    billing_model: "flat",
    unit_price: 24900,
    included_compute_hours: 720,
    included_storage_gb: 20,
    max_ponds: 5,
  },
];

function json(route: Route, status: number, body: unknown) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApi(page: Page) {
  let onboarded = false;

  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const { pathname } = new URL(req.url());
    const method = req.method();
    const user = { ...newUser, onboarded };

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
        return json(route, 401, {
          code: "token_invalid",
          message: "no cookie",
          request_id: "req",
        });
      }
      return json(route, 200, {
        access_token: "access_restored",
        refresh_token: "refresh_rotated",
      });
    }
    if (method === "GET" && pathname.endsWith("/me")) {
      return json(route, 200, { user, ponds_count: 0, subscription: null });
    }
    if (method === "POST" && pathname.endsWith("/me/onboarding/complete")) {
      onboarded = true;
      return route.fulfill({ status: 204, body: "" });
    }
    if (method === "GET" && pathname.endsWith("/plans")) {
      return json(route, 200, { plans, next_cursor: null });
    }
    if (method === "GET" && pathname.endsWith("/usage")) {
      return json(route, 200, {
        month: "2026-11",
        days: [],
        totals: { compute_hours: 0, storage_gb_days: 0 },
      });
    }
    if (method === "GET" && pathname.endsWith("/ponds")) {
      return json(route, 200, { ponds: [], next_cursor: null });
    }
    return json(route, 404, {
      code: "not_found",
      message: pathname,
      request_id: "req",
    });
  });
}

test("sandbox plan choice leads into intro cards then coachmarks", async ({ page }) => {
  await installApi(page);
  await clearIntroTourSeen(page, NEW_USER_ID);
  await clearIntroTourSeen(page, DEMO_USER_ID);

  await page.goto("/login");
  await page.getByLabel("Correo").fill(newUser.email);
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();

  await expect(page).toHaveURL(/\/app\/onboarding/);
  await expect(page.getByRole("heading", { name: "¿Cómo quieres empezar?" })).toBeVisible();
  await expect(page.getByTestId("onboarding-pond")).toBeVisible();
  await expect(page.getByTestId("onboarding-pond").locator(".koi, .koi--x2").first()).toBeVisible();

  await page.getByRole("button", { name: "Continuar gratis (modo sandbox)" }).click();

  const tour = page.getByTestId("intro-tour");
  await expect(tour).toBeVisible();
  await expect(tour.getByTestId("intro-tour-cards")).toBeVisible();
  await expect(tour.getByRole("heading", { name: "Bienvenido a KoiCloud" })).toBeVisible();


  await tour.getByRole("button", { name: "Siguiente" }).click();
  await tour.getByRole("button", { name: "Siguiente" }).click();
  await tour.getByRole("button", { name: "Siguiente" }).click();

  const coach = page.getByTestId("intro-tour-coachmark");
  await expect(coach).toBeVisible();
  await expect(coach).toContainText("Aquí ves tus ponds");
  await expect(page.locator('[data-tour-target="ponds"]')).toBeVisible();

  await tour.getByRole("button", { name: "Siguiente" }).click();
  await expect(coach).toContainText("Aquí ves tus planes");
  await expect(page.locator('[data-tour-target="plans"]')).toBeVisible();

  await tour.getByRole("button", { name: "Siguiente" }).click();
  await expect(coach).toContainText("Aquí ves tu cuenta");
  await expect(page.locator('[data-tour-target="account"]')).toBeVisible();

  await tour.getByRole("button", { name: "Listo" }).click();
  await expect(tour).toHaveCount(0);
});
