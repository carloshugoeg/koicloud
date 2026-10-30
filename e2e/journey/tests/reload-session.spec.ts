import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Route } from "@playwright/test";

const root = path.dirname(fileURLToPath(import.meta.url));
const shotsDir = path.resolve(root, "../artifacts");
const prShotsDir = "/opt/cursor/artifacts";

const user = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "demo@koicloud.dev",
  full_name: "Operador Demo",
  role: "client",
  status: "active",
  email_verified: true,
  nit: "0614-220999-101-3",
  created_at: "2026-09-22T20:00:00Z",
};

const pond = {
  id: "66666666-6666-6666-6666-666666666666",
  name: "inventario-demo",
  engine_version: "16",
  plan_id: "micro",
  node_id: "node-sv-01",
  host_port: 15007,
  user_id: user.id,
  size_bytes: 124901,
  healthy: true,
  created_at: "2026-09-22T20:00:00Z",
  last_restore_at: null,
  desired_state: "running",
  observed_state: "running",
  last_error: null,
};

const REFRESH_COOKIE = "koi_refresh=refresh_e2e; Path=/api/v1; HttpOnly; SameSite=Lax";

function json(route: Route, status: number, body: unknown, extraHeaders?: Record<string, string>) {
  return route.fulfill({
    status,
    contentType: "application/json",
    headers: extraHeaders,
    body: JSON.stringify(body),
  });
}

async function installApi(page: Page) {
  const hits = { refresh: 0, logout: 0 };
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const { pathname } = url;
    const method = req.method();
    const cookie = req.headers().cookie ?? "";

    if (method === "POST" && pathname.endsWith("/auth/login")) {
      return json(route, 200, { access_token: "access_e2e", refresh_token: "refresh_e2e", user }, {
        "set-cookie": REFRESH_COOKIE,
      });
    }
    if (method === "POST" && pathname.endsWith("/auth/refresh")) {
      hits.refresh += 1;
      if (!cookie.includes("koi_refresh=refresh_e2e") && !cookie.includes("koi_refresh=refresh_rotated")) {
        return json(route, 401, { code: "token_invalid", message: "no cookie", request_id: "req" });
      }
      const rotated = cookie.includes("koi_refresh=refresh_rotated");
      return json(
        route,
        200,
        {
          access_token: rotated ? "access_rotated_again" : "access_restored",
          refresh_token: rotated ? "refresh_rotated_again" : "refresh_rotated",
        },
        {
          "set-cookie": rotated
            ? "koi_refresh=refresh_rotated_again; Path=/api/v1; HttpOnly; SameSite=Lax"
            : "koi_refresh=refresh_rotated; Path=/api/v1; HttpOnly; SameSite=Lax",
        },
      );
    }
    if (method === "POST" && pathname.endsWith("/auth/logout")) {
      hits.logout += 1;
      return route.fulfill({
        status: 204,
        headers: {
          "set-cookie": "koi_refresh=; Path=/api/v1; Max-Age=0; HttpOnly; SameSite=Lax",
        },
      });
    }
    if (method === "GET" && pathname.endsWith("/me")) {
      const auth = req.headers().authorization ?? "";
      if (!auth.startsWith("Bearer access_")) {
        return json(route, 401, { code: "unauthorized", message: "no", request_id: "req" });
      }
      return json(route, 200, { user, ponds_count: 1, subscription: null });
    }
    if (method === "GET" && pathname.endsWith("/plans")) {
      return json(route, 200, { plans: [] });
    }
    if (method === "GET" && pathname.endsWith("/usage")) {
      return json(route, 200, {
        month: "2026-10",
        ponds: [],
        total_instance_hours: 0,
        total_storage_gb_hours: 0,
      });
    }
    if (method === "GET" && pathname.endsWith("/ponds")) {
      const auth = req.headers().authorization ?? "";
      if (!auth.startsWith("Bearer access_")) {
        return json(route, 401, { code: "unauthorized", message: "no", request_id: "req" });
      }
      return json(route, 200, { ponds: [pond], next_cursor: null });
    }
    return json(route, 404, { code: "not_found", message: pathname, request_id: "req" });
  });
  return hits;
}

async function login(page: Page) {
  await page.goto("/login?next=/app/ponds");
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/app\/ponds/);
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toBeVisible();
  await page.context().addCookies([
    {
      name: "koi_refresh",
      value: "refresh_e2e",
      url: "http://127.0.0.1:5173/api/v1/auth/refresh",
      httpOnly: true,
      sameSite: "Lax",
    },
  ]);
}

async function shoot(page: Page, stem: string) {
  fs.mkdirSync(shotsDir, { recursive: true });
  fs.mkdirSync(prShotsDir, { recursive: true });
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    const file = `${stem}-${width}.png`;
    const buf = await page.screenshot({ fullPage: true });
    fs.writeFileSync(path.join(shotsDir, file), buf);
    fs.writeFileSync(path.join(prShotsDir, file), buf);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

test("journey: reload keeps session", async ({ page }) => {
  const hits = await installApi(page);
  await login(page);
  await page.reload();
  await expect(page).toHaveURL(/\/app\/ponds/);
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toBeVisible();
  await expect(page.getByText("inventario-demo")).toBeVisible();
  expect(hits.refresh).toBeGreaterThan(0);
  await shoot(page, "reload-keeps-session");
});

test("journey: logout returns to login", async ({ page }) => {
  const hits = await installApi(page);
  await login(page);
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  expect(hits.logout).toBe(1);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toHaveCount(0);
});
