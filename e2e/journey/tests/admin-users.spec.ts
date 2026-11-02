import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { seedPath } from "../admin-users-global-setup";

const shotsDir = "/opt/cursor/artifacts";

type Seed = {
  email: string;
  password: string;
  oldest: string;
  suspend: string;
};

function seed(): Seed {
  return JSON.parse(fs.readFileSync(seedPath, "utf8")) as Seed;
}

async function login(page: Page, account: Seed) {
  await page.goto(`/login?next=${encodeURIComponent("/app/admin/users")}`);
  await page.getByLabel("Correo").fill(account.email);
  await page.getByLabel("Contraseña").fill(account.password);
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByTestId("admin-users-page")).toBeVisible();
}

function userRow(page: Page, email: string) {
  return page.locator("[data-testid^='admin-user-row-']", { hasText: email });
}

test("admin users list pages and suspend survives reload", async ({ page }) => {
  const account = seed();
  await login(page, account);

  await expect(userRow(page, account.suspend)).toBeVisible();
  await expect(userRow(page, account.oldest)).toHaveCount(0);

  fs.mkdirSync(shotsDir, { recursive: true });
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expect(page.getByTestId("admin-users-page")).toBeVisible();
    await page.screenshot({
      path: path.join(shotsDir, `admin-users-${width}.png`),
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 1440, height: 900 });

  await page.getByRole("button", { name: "Cargar más" }).click();
  await expect(userRow(page, account.oldest)).toBeVisible();
  await expect(userRow(page, account.suspend)).toBeVisible();
  await expect(page.getByRole("button", { name: "Cargar más" })).toHaveCount(0);

  await page.getByRole("textbox", { name: /buscar/i }).fill("suspend-me");
  await expect(userRow(page, account.suspend)).toBeVisible();
  await expect(userRow(page, account.oldest)).toHaveCount(0);
  await page.getByRole("textbox", { name: /buscar/i }).fill("");
  await expect(userRow(page, account.oldest)).toBeVisible();

  const row = userRow(page, account.suspend);
  await row.getByRole("button", { name: "Suspender" }).click();
  await page.getByTestId("suspend-confirm-email").fill(account.suspend);
  await page.getByTestId("suspend-submit").click();
  await expect(row.getByText("suspendido")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("admin-users-page")).toBeVisible();
  const suspended = userRow(page, account.suspend);
  await expect(suspended.getByText("suspendido")).toBeVisible();

  await suspended.getByRole("button", { name: "Reactivar" }).click();
  await page.getByTestId("reactivate-submit").click();
  await expect(suspended.getByText("activo")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("admin-users-page")).toBeVisible();
  await expect(userRow(page, account.suspend).getByText("activo")).toBeVisible();
});
