import fs from "node:fs";
import path from "node:path";
import { expect, test, type Page, type Route } from "@playwright/test";

const shotsDir = "/opt/cursor/artifacts";
const widths = [375, 768, 1440] as const;

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

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

const plans = [
  {
    active: true,
    billing_model: "monthly",
    currency: "USD",
    description: "Pruebas internas (10 min)",
    id: "sandbox",
    max_ponds: 1,
    max_storage_gb: 1,
    name: "Sandbox",
    postpaid: false,
    price_monthly_usd: 0,
    unit_price: 0,
    validity_minutes: 10,
  },
  {
    active: true,
    billing_model: "monthly",
    currency: "USD",
    description: "1 pond, 1 GB, backups 7 días",
    id: "micro",
    max_ponds: 1,
    max_storage_gb: 1,
    name: "Micro",
    postpaid: false,
    price_monthly_usd: 5,
    unit_price: 5,
    validity_minutes: 43_200,
  },
  {
    active: true,
    billing_model: "hourly",
    currency: "USD",
    description: "Hasta 10 ponds, post-pago por uso",
    id: "pro",
    max_ponds: 10,
    max_storage_gb: 20,
    name: "Pro",
    postpaid: true,
    price_monthly_usd: 0,
    unit_price: 0.02,
    validity_minutes: 43_200,
  },
];

const subscribed = {
  subscription: {
    id: "22222222-2222-2222-2222-222222222222",
    user_id: user.id,
    plan_id: "micro",
    status: "active",
    current_period_start: "2026-09-22T20:00:00Z",
    current_period_end: "2026-10-22T20:00:00Z",
    cancel_at_period_end: false,
  },
  invoice: {
    id: "33333333-3333-3333-3333-333333333333",
    user_id: user.id,
    subscription_id: "22222222-2222-2222-2222-222222222222",
    number: "KOI-202609-0001",
    status: "paid",
    subtotal_usd: 4.4643,
    iva_usd: 0.5357,
    total_usd: 5,
    issued_at: "2026-09-22T20:00:00Z",
    pdf_path: "/var/lib/koicloud/invoices/KOI-202609-0001.pdf",
    nit: "1000002-K",
  },
  payment: {
    id: "55555555-5555-5555-5555-555555555555",
    invoice_id: "33333333-3333-3333-3333-333333333333",
    amount_usd: 5,
    status: "succeeded",
    method: "simulated",
    processed_at: "2026-09-22T20:00:00Z",
  },
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
      return json(route, 200, { plans, next_cursor: null });
    }
    if (method === "GET" && pathname.endsWith("/subscriptions")) {
      return json(route, 200, { subscriptions: [], next_cursor: null });
    }
    if (method === "POST" && pathname.endsWith("/subscriptions")) {
      return json(route, 202, subscribed);
    }
    if (method === "GET" && pathname.endsWith("/usage")) {
      return json(route, 200, {
        month: "2026-11",
        ponds: [],
        total_instance_hours: 0,
        total_storage_gb_hours: 0,
      });
    }
    if (method === "GET" && pathname.endsWith("/invoices")) {
      return json(route, 200, { invoices: [], next_cursor: null });
    }
    if (method === "GET" && pathname.endsWith("/ponds")) {
      return json(route, 200, { ponds: [], next_cursor: null });
    }
    return json(route, 404, { code: "not_found", message: pathname, request_id: "req" });
  });
}

async function openUso(page: Page, width: number) {
  await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
  await page.goto("/login?next=/app/uso");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/app\/uso/, { timeout: 10_000 });
  await expect(page.getByRole("button", { name: "Cambiar de plan" })).toBeVisible();
}

async function openCheckout(page: Page) {
  await page.getByRole("button", { name: "Cambiar de plan" }).click();
  await page.getByRole("button", { name: "Elegir plan Micro" }).click();
  await expect(page.getByRole("heading", { name: "Contratar plan Micro" })).toBeVisible();
  await expect(page.getByRole("dialog")).toBeVisible();
}

async function openInvoice(page: Page) {
  await openCheckout(page);
  await page.getByLabel("NIT (opcional)").fill("1000002-K");
  await page.getByLabel("Número de tarjeta simulada").fill("4242 4242 4242 4242");
  await page.getByLabel("Expiración").fill("12/30");
  await page.getByLabel("CVC").fill("123");
  await page.getByRole("button", { name: "Confirmar contratación" }).click();
  await expect(page.getByTestId("checkout-invoice-from-api")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Factura KOI-202609-0001" })).toBeVisible();
}

function shoot(page: Page, name: string) {
  fs.mkdirSync(shotsDir, { recursive: true });
  return page.screenshot({ path: path.join(shotsDir, name), fullPage: true });
}

async function tabStops(page: Page): Promise<string[]> {
  return page.evaluate((selector) => {
    const dialog = document.querySelector("[role='dialog']");
    if (!dialog) return [];
    return Array.from(dialog.querySelectorAll<HTMLElement>(selector))
      .filter((el) => !el.hasAttribute("disabled") && el.tabIndex !== -1)
      .map((el) =>
        [
          el.tagName,
          el.id,
          el.getAttribute("aria-label") ?? "",
          (el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 80),
        ].join("|"),
      );
  }, FOCUSABLE);
}

async function focusFirstStop(page: Page) {
  await page.evaluate((selector) => {
    const dialog = document.querySelector("[role='dialog']");
    dialog?.querySelector<HTMLElement>(selector)?.focus();
  }, FOCUSABLE);
}

async function activeStop(page: Page): Promise<{ inside: boolean; signature: string }> {
  return page.evaluate(() => {
    const dialog = document.querySelector("[role='dialog']");
    const el = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const signature = el
      ? [
          el.tagName,
          el.id,
          el.getAttribute("aria-label") ?? "",
          (el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 80),
        ].join("|")
      : "";
    return { inside: Boolean(dialog && el && dialog.contains(el)), signature };
  });
}

async function expectCycle(page: Page, key: "Tab" | "Shift+Tab") {
  const stops = await tabStops(page);
  expect(stops.length).toBeGreaterThan(0);
  await focusFirstStop(page);
  const forward = [...stops.slice(1), stops[0]];
  const expected = key === "Tab" ? forward : [...stops].reverse();
  for (const want of expected) {
    await page.keyboard.press(key);
    const active = await activeStop(page);
    expect(active.inside, `${key} left the dialog. Active: ${active.signature}`).toBe(true);
    expect(active.signature).toBe(want);
  }
}

for (const width of widths) {
  test(`checkout dialog cycles Tab and Shift+Tab at ${width}`, async ({ page }) => {
    await installApi(page);
    await openUso(page, width);
    await openCheckout(page);
    await shoot(page, `checkout-dialog-${width}.png`);
    await expectCycle(page, "Tab");
    await expectCycle(page, "Shift+Tab");
    await expect(page.getByRole("button", { name: "Cambiar de plan" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  test(`invoice dialog cycles Tab and Shift+Tab at ${width}`, async ({ page }) => {
    await installApi(page);
    await openUso(page, width);
    await openInvoice(page);
    await shoot(page, `invoice-dialog-${width}.png`);
    await expectCycle(page, "Tab");
    await expectCycle(page, "Shift+Tab");
    await expect(page.getByRole("dialog")).toBeVisible();
    await expect(page.getByRole("button", { name: "Cambiar de plan" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });
}

test("escape closes only the checkout dialog and returns focus to Elegir plan", async ({ page }) => {
  await installApi(page);
  await openUso(page, 1440);
  await openCheckout(page);
  const choose = page.getByRole("button", { name: "Elegir plan Micro" });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Contratar plan Micro" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Cambiar de plan" })).toHaveAttribute(
    "aria-expanded",
    "true",
  );
  await expect(choose).toBeVisible();
  await expect(choose).toBeFocused();
});
