import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const shotsDir = "/opt/cursor/artifacts";
const logoutFailKey = "koi-mock-logout-fails";

function isRefresh(response: { url: () => string; request: () => { method: () => string } }) {
  return response.request().method() === "POST" && response.url().includes("/api/v1/auth/refresh");
}

async function login(page: Page) {
  await page.goto("/login?next=/app/ponds");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toBeVisible();
  await expect(page).toHaveURL(/\/app\/ponds/);
}

async function shootPonds(page: Page) {
  fs.mkdirSync(shotsDir, { recursive: true });
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await expect(page.getByRole("heading", { name: "Tus ponds" })).toBeVisible();
    await page.screenshot({
      path: path.join(shotsDir, `ponds-after-reload-${width}.png`),
      fullPage: true,
    });
  }
}

test("journey: msw reload keeps session", async ({ page }) => {
  await login(page);
  const refresh = page.waitForResponse(isRefresh);
  await page.reload();
  const status = (await refresh).status();
  await expect(page).toHaveURL(/\/app\/ponds/);
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toBeVisible();
  await expect(page.getByText("inventario-demo")).toBeVisible();
  expect(status).toBe(200);
  await shootPonds(page);
});

test("journey: msw deep link keeps session", async ({ page }) => {
  await login(page);
  const next = await page.context().newPage();
  const refresh = next.waitForResponse(isRefresh);
  await next.goto("/app/uso");
  const status = (await refresh).status();
  await expect(next).toHaveURL(/\/app\/uso/);
  await expect(next.getByRole("heading", { name: "Uso del mes" })).toBeVisible();
  await expect(next.getByRole("heading", { name: "Iniciar sesión" })).toHaveCount(0);
  expect(status).toBe(200);
});

test("journey: msw logout failure still returns to login", async ({ page }) => {
  await login(page);
  await page.evaluate((key) => {
    sessionStorage.setItem(key, "1");
  }, logoutFailKey);
  const logout = page.waitForResponse(
    (response) => response.request().method() === "POST" && response.url().includes("/api/v1/auth/logout"),
  );
  await page.getByRole("button", { name: "Cerrar sesión" }).click();
  const status = (await logout).status();
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toHaveCount(0);
  expect(status).toBe(500);

  await page.reload();
  await expect(page).toHaveURL(/\/login/);
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Tus ponds" })).toHaveCount(0);

  fs.mkdirSync(shotsDir, { recursive: true });
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Tus ponds" })).toHaveCount(0);
    await page.screenshot({
      path: path.join(shotsDir, `logout-fail-reload-${width}.png`),
      fullPage: true,
    });
  }

  for (const width of [375, 768, 1440] as const) {
    const next = await page.context().newPage();
    try {
      await next.setViewportSize({ width, height: width === 375 ? 812 : 900 });
      await next.goto("/app/uso");
      await expect(next).toHaveURL(/\/login/);
      await expect(next.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
      await expect(next.getByRole("heading", { name: "Uso del mes" })).toHaveCount(0);
    } finally {
      await next.close();
    }
  }
});
