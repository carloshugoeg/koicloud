import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Route } from "@playwright/test";

const root = path.dirname(fileURLToPath(import.meta.url));
const shotsDir = "/opt/cursor/artifacts/pond-table-explorer";
const suiteShotsDir = path.resolve(root, "../artifacts/pond-table-explorer");

const POND_ID = "66666666-6666-6666-6666-666666666666";
const WIDTHS = [375, 768, 1440] as const;

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
  id: POND_ID,
  name: "inventario-demo",
  engine_version: "16",
  plan_id: "micro",
  node_id: "node-sv-01",
  host_port: 15007,
  user_id: user.id,
  desired_state: "running" as const,
  observed_state: "running" as const,
  healthy: true,
  last_error: null as string | null,
  last_restore_at: null as string | null,
  created_at: "2026-09-22T20:00:00Z",
};

const connection = {
  host: "127.0.0.1",
  port: 15007,
  username: "koi",
  password: "secret",
  database: "inventario_demo",
  uri: "postgresql://koi:secret@127.0.0.1:15007/inventario_demo",
};

const EMPTY_SCHEMA = { tables: [] as const };

const TWO_TABLES = {
  tables: [
    {
      name: "public.orders",
      estimated_rows: 2,
      columns: [
        { name: "id", type: "integer", nullable: false, default: null },
        { name: "label", type: "text", nullable: false, default: "'x'::text" },
      ],
    },
    {
      name: "public.items",
      estimated_rows: 12,
      columns: [
        { name: "sku", type: "text", nullable: false, default: null },
        { name: "qty", type: "integer", nullable: true, default: null },
      ],
    },
  ],
};

type SchemaMode = "empty" | "two" | "error" | "recover";

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApi(page: Page, getMode: () => SchemaMode, schemaHits: { n: number }) {
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const { pathname } = new URL(req.url());
    const method = req.method();

    if (method === "POST" && pathname.endsWith("/auth/login")) {
      return json(route, 200, {
        access_token: "access_e2e",
        refresh_token: "refresh_e2e",
        user,
      });
    }
    if (method === "GET" && pathname.endsWith("/me")) {
      return json(route, 200, { user });
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
      return json(route, 200, { ponds: [pond] });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}/connection`)) {
      return json(route, 200, { connection });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}`)) {
      return json(route, 200, { pond });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}/schema`)) {
      schemaHits.n += 1;
      const mode = getMode();
      if (mode === "empty") return json(route, 200, EMPTY_SCHEMA);
      if (mode === "two") return json(route, 200, TWO_TABLES);
      if (mode === "error") {
        return json(route, 500, {
          code: "internal_error",
          message: "schema boom",
          request_id: "req_schema_err",
        });
      }
      // recover: first error then two tables
      if (schemaHits.n === 1) {
        return json(route, 500, {
          code: "internal_error",
          message: "schema boom",
          request_id: "req_schema_err",
        });
      }
      return json(route, 200, TWO_TABLES);
    }
    return json(route, 404, { code: "not_found", message: pathname, request_id: "req" });
  });
}

async function loginToPond(page: Page) {
  await page.goto(`/login?next=/app/ponds/${POND_ID}`);
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(new RegExp(`/app/ponds/${POND_ID}`));
  await expect(page.getByTestId("pond-detail")).toBeVisible();
}

async function expectNoAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page }).analyze();
  const lines = results.violations.map((violation) => {
    const target = violation.nodes[0]?.target.join(" ") ?? "";
    return `${violation.id} (${violation.impact ?? "unknown"}) ${violation.help} ${target}`;
  });
  expect(lines, lines.join("\n")).toEqual([]);
}

async function shoot(page: Page, stem: string) {
  fs.mkdirSync(shotsDir, { recursive: true });
  fs.mkdirSync(suiteShotsDir, { recursive: true });
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    const file = `${stem}-${width}.png`;
    const buf = await page.screenshot({ fullPage: true });
    fs.writeFileSync(path.join(shotsDir, file), buf);
    fs.writeFileSync(path.join(suiteShotsDir, file), buf);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

test.describe("Pond table explorer (#207)", () => {
  test("idle has no schema GET; Recargar empty then two tables; expand; no polling", async ({
    page,
  }) => {
    let mode: SchemaMode = "empty";
    const schemaHits = { n: 0 };
    await installApi(page, () => mode, schemaHits);
    await loginToPond(page);

    await expect(page.getByTestId("pond-tables")).toBeVisible();
    await expect(page.getByTestId("pond-tables-idle")).toBeVisible();
    await expect(page.getByTestId("pond-tables-reload")).toHaveText("Recargar");
    await expect(page.getByTestId("pond-tables-status")).toHaveAttribute("aria-live", "polite");

    await page.waitForTimeout(5_000);
    expect(schemaHits.n).toBe(0);

    await shoot(page, "empty");
    await expectNoAxeViolations(page);

    await page.getByTestId("pond-tables-reload").click();
    await expect(page.getByTestId("pond-tables-empty")).toHaveText(
      "Esta pond aún no tiene tablas",
    );
    expect(schemaHits.n).toBe(1);

    mode = "two";
    await page.getByTestId("pond-tables-reload").click();
    await expect(page.getByTestId("pond-tables-list")).toBeVisible();
    await expect(page.getByTestId("pond-tables-table").first()).toHaveAttribute(
      "data-table-name",
      "public.orders",
    );
    await expect(page.getByText("public.items")).toBeVisible();

    const orders = page.locator('[data-testid="pond-tables-table"][data-table-name="public.orders"]');
    await orders.getByTestId("pond-tables-expand").click();
    await expect(orders.getByTestId("pond-tables-columns")).toContainText("integer");
    await expect(orders.getByTestId("pond-tables-estimated-rows")).toHaveText("2");

    const afterLoad = schemaHits.n;
    await page.waitForTimeout(5_000);
    expect(schemaHits.n).toBe(afterLoad);

    await shoot(page, "loaded");
    await expectNoAxeViolations(page);
  });

  test("schema error shows Reintentar and recovers", async ({ page }) => {
    let mode: SchemaMode = "recover";
    const schemaHits = { n: 0 };
    await installApi(page, () => mode, schemaHits);
    await loginToPond(page);

    await page.getByTestId("pond-tables-reload").click();
    await expect(page.getByTestId("pond-tables-error")).toBeVisible();
    await shoot(page, "error");
    await expectNoAxeViolations(page);

    await page.getByRole("button", { name: "Reintentar" }).click();
    await expect(page.getByTestId("pond-tables-list")).toBeVisible();
    await expect(page.getByText("public.orders")).toBeVisible();
  });

  test("axe + contrast at 375 / 768 / 1440 after load", async ({ page }) => {
    let mode: SchemaMode = "two";
    const schemaHits = { n: 0 };
    await installApi(page, () => mode, schemaHits);
    await loginToPond(page);
    await page.getByTestId("pond-tables-reload").click();
    await expect(page.getByTestId("pond-tables-list")).toBeVisible();

    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
      await expectNoAxeViolations(page);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
      );
      expect(overflow).toBe(false);
    }
  });
});
