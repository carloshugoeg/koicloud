import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Route } from "@playwright/test";

const root = path.dirname(fileURLToPath(import.meta.url));
const shotsDir = path.resolve(root, "../artifacts/shots");
const mediaDir =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/gate-130-r5";

const POND_ID = "66666666-6666-6666-6666-666666666666";

type PondPhase = {
  desired_state: "running" | "stopped";
  observed_state: "running" | "stopped" | "failed";
  last_error?: string | null;
};

const basePond = {
  id: POND_ID,
  name: "inventario-demo",
  engine_version: "16",
  plan_id: "micro",
  node_id: "node-sv-01",
  host_port: 15007,
  user_id: "11111111-1111-1111-1111-111111111111",
  size_bytes: 124901,
  healthy: true,
  created_at: "2026-09-22T20:00:00Z",
  last_restore_at: null as string | null,
};

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

const connection = {
  host: "127.0.0.1",
  port: 15007,
  username: "koi",
  password: "secret",
  database: "inventario_demo",
  uri: "postgresql://koi:secret@127.0.0.1:15007/inventario_demo",
};

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApi(page: Page, getPhase: () => PondPhase, setPhase: (p: PondPhase) => void) {
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const { pathname } = url;
    const method = req.method();

    if (method === "POST" && pathname.endsWith("/auth/login")) {
      return json(route, 200, { access_token: "access_e2e", refresh_token: "refresh_e2e", user });
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
      const phase = getPhase();
      return json(route, 200, {
        ponds: [{ ...basePond, ...phase, healthy: phase.observed_state === "running" }],
      });
    }
    if (method === "GET" && pathname.includes(`/ponds/${POND_ID}/connection`)) {
      return json(route, 200, { connection });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}`)) {
      const phase = getPhase();
      return json(route, 200, {
        pond: {
          ...basePond,
          ...phase,
          healthy: phase.observed_state === "running",
          last_error: phase.last_error ?? null,
        },
      });
    }
    if (method === "POST" && pathname.endsWith(`/ponds/${POND_ID}/stop`)) {
      setPhase({ desired_state: "stopped", observed_state: "running" });
      return json(route, 202, {
        pond: { ...basePond, desired_state: "stopped", observed_state: "running", healthy: true },
        job: {
          id: "77777777-7777-7777-7777-777777777701",
          type: "stop_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-10-27T00:00:00Z",
          node_id: "node-sv-01",
          pond_id: POND_ID,
          claimed_at: null,
          completed_at: null,
          last_error: null,
        },
      });
    }
    if (method === "POST" && pathname.endsWith(`/ponds/${POND_ID}/start`)) {
      const phase = getPhase();
      if (phase.observed_state !== "stopped") {
        return json(route, 409, { code: "pond_busy", message: "busy", request_id: "req" });
      }
      setPhase({ desired_state: "running", observed_state: "stopped" });
      return json(route, 202, {
        pond: { ...basePond, desired_state: "running", observed_state: "stopped", healthy: false },
        job: {
          id: "77777777-7777-7777-7777-777777777702",
          type: "start_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-10-27T00:00:00Z",
          node_id: "node-sv-01",
          pond_id: POND_ID,
          claimed_at: null,
          completed_at: null,
          last_error: null,
        },
      });
    }
    if (method === "POST" && pathname.endsWith(`/ponds/${POND_ID}/retry`)) {
      const phase = getPhase();
      if (phase.desired_state === "stopped") {
        setPhase({ desired_state: "stopped", observed_state: "running", last_error: null });
        return json(route, 202, {
          job: {
            id: "77777777-7777-7777-7777-777777777703",
            type: "stop_pond",
            status: "queued",
            attempts: 0,
            created_at: "2026-10-27T00:00:00Z",
            node_id: "node-sv-01",
            pond_id: POND_ID,
            claimed_at: null,
            completed_at: null,
            last_error: null,
          },
        });
      }
      setPhase({ desired_state: "running", observed_state: "stopped", last_error: null });
      return json(route, 202, {
        job: {
          id: "77777777-7777-7777-7777-777777777704",
          type: "start_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-10-27T00:00:00Z",
          node_id: "node-sv-01",
          pond_id: POND_ID,
          claimed_at: null,
          completed_at: null,
          last_error: null,
        },
      });
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
  await expect(page.getByTestId("pond-status-badge")).toBeVisible();
}

/** Wait for detail poll (4s) to pick up a new phase. */
async function awaitBadge(page: Page, pattern: RegExp) {
  await expect(page.getByTestId("pond-status-badge")).toHaveText(pattern, { timeout: 20_000 });
}

async function shoot(page: Page, stem: string) {
  fs.mkdirSync(shotsDir, { recursive: true });
  fs.mkdirSync(mediaDir, { recursive: true });
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    const file = `${stem}-${width}.png`;
    const buf = await page.screenshot({ fullPage: true });
    fs.writeFileSync(path.join(shotsDir, file), buf);
    fs.writeFileSync(path.join(mediaDir, file), buf);
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

test.describe("CCR #131 pond lifecycle", () => {
  test("happy path + failure + retry show Iniciando… / Deteniendo…", async ({ page }) => {
    let phase: PondPhase = { desired_state: "running", observed_state: "running" };
    await installApi(
      page,
      () => phase,
      (p) => {
        phase = p;
      },
    );

    await loginToPond(page);
    await awaitBadge(page, /En línea/);
    await expect(page.getByTestId("pond-stop")).toBeEnabled();
    await expect(page.getByTestId("pond-start")).toBeDisabled();

    // running → stopping
    await page.getByTestId("pond-stop").click();
    await awaitBadge(page, /Deteniendo/);
    await expect(page.getByTestId("pond-stop")).toBeDisabled();
    await expect(page.getByTestId("pond-start")).toBeDisabled();

    // stop ok → stopped (poll while in flight)
    phase = { desired_state: "stopped", observed_state: "stopped" };
    await awaitBadge(page, /Detenido/);
    await expect(page.getByTestId("pond-start")).toBeEnabled();

    // stopped → starting
    await page.getByTestId("pond-start").click();
    await awaitBadge(page, /Iniciando/);

    // starting → error
    phase = { desired_state: "running", observed_state: "failed", last_error: "start boom" };
    await awaitBadge(page, /Con fallas/);
    await expect(page.getByTestId("pond-retry")).toBeEnabled();
    await expect(page.getByTestId("pond-start")).toBeDisabled();
    await expect(page.getByTestId("pond-stop")).toBeDisabled();

    // error → starting via /retry (NOT En cola)
    await page.getByTestId("pond-retry").click();
    await awaitBadge(page, /Iniciando/);
    await expect(page.getByText("En cola")).toHaveCount(0);
    await shoot(page, "retry-iniciar");

    // back to running
    phase = { desired_state: "running", observed_state: "running" };
    await awaitBadge(page, /En línea/);

    // stop fail → error → retry → Deteniendo…
    await page.getByTestId("pond-stop").click();
    await awaitBadge(page, /Deteniendo/);
    phase = { desired_state: "stopped", observed_state: "failed", last_error: "stop boom" };
    await awaitBadge(page, /Con fallas/);
    await page.getByTestId("pond-retry").click();
    await awaitBadge(page, /Deteniendo/);
    await expect(page.getByText("En cola")).toHaveCount(0);
    await shoot(page, "retry-detener");
  });
});
