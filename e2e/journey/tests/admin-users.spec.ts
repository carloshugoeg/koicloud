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

test("keeps focus on Cargar más while the next page loads", async ({ page }) => {
  const account = seed();
  let releaseNext: () => void = () => {};
  const gate = new Promise<void>((resolve) => {
    releaseNext = resolve;
  });
  await page.route("**/api/v1/admin/users**", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.has("cursor")) {
      await gate;
    }
    await route.continue();
  });

  try {
    await login(page, account);
    await page.getByRole("button", { name: "Cargar más" }).click();
    const busy = page.getByRole("button", { name: "Cargando…" });
    await expect(busy).toBeVisible();
    await expect(busy).toBeFocused();
    await expect(busy).toBeEnabled();
    await expect(busy).toHaveAttribute("aria-busy", "true");
  } finally {
    releaseNext();
  }
});

test("shows an inline error and retries the next page without dropping loaded rows", async ({ page }) => {
  const account = seed();
  let failCursor = true;
  await page.route("**/api/v1/admin/users**", async (route) => {
    const url = new URL(route.request().url());
    if (url.searchParams.has("cursor") && failCursor) {
      await route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ code: "internal_error", message: "internal_error" }),
      });
      return;
    }
    await route.continue();
  });

  await login(page, account);
  await expect(userRow(page, account.suspend)).toBeVisible();
  await page.getByRole("button", { name: "Cargar más" }).click();

  const alert = page.getByTestId("admin-users-page").getByRole("alert");
  await expect(alert).toContainText("No pudimos cargar más usuarios.");
  await expect(alert.getByRole("button", { name: "Reintentar" })).toBeVisible();
  await expect(userRow(page, account.suspend)).toBeVisible();
  await expect(userRow(page, account.oldest)).toHaveCount(0);

  failCursor = false;
  await alert.getByRole("button", { name: "Reintentar" }).click();
  await expect(userRow(page, account.oldest)).toBeVisible();
  await expect(userRow(page, account.suspend)).toBeVisible();
});

test("names the search as a filter over loaded users and hints when more pages remain", async ({ page }) => {
  const account = seed();
  await login(page, account);

  await expect(page.getByRole("textbox", { name: /buscar/i })).toHaveAttribute(
    "placeholder",
    "Filtrar usuarios cargados",
  );
  await expect(page.getByText("Cargá más para buscar en el resto")).toBeVisible();

  await page.getByRole("textbox", { name: /buscar/i }).fill("zzz-no-existe");
  await expect(page.getByTestId("admin-users-empty")).toHaveText("No hay usuarios con ese filtro.");
  await expect(page.getByText("Cargá más para buscar en el resto")).toBeVisible();

  await page.getByRole("textbox", { name: /buscar/i }).fill("");
  await page.getByRole("button", { name: "Cargar más" }).click();
  await expect(userRow(page, account.oldest)).toBeVisible();
  await expect(page.getByText("Cargá más para buscar en el resto")).toHaveCount(0);
});

test("says there are no users yet when the list is empty and no filter is set", async ({ page }) => {
  const account = seed();
  await page.route("**/api/v1/admin/users**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ users: [], next_cursor: null }),
    });
  });

  await login(page, account);
  await expect(page.getByTestId("admin-users-empty")).toHaveText("No hay usuarios.");
  await expect(page.getByText("No hay usuarios con ese filtro.")).toHaveCount(0);
  await expect(page.getByText("Cargá más para buscar en el resto")).toHaveCount(0);
  await expect(page.getByRole("textbox", { name: /buscar/i })).toHaveAttribute(
    "placeholder",
    "Filtrar usuarios cargados",
  );
});
