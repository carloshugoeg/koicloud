import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Route } from "@playwright/test";

const root = path.dirname(fileURLToPath(import.meta.url));
const shotsDir = path.resolve(root, "../artifacts/shots");
const mediaDir =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/gate-130-r6";

const POND_ID = "66666666-6666-6666-6666-666666666666";

type PondPhase = {
  desired_state: "running" | "stopped";
  observed_state: "running" | "stopped" | "failed";
  last_error?: string | null;
};

type FailKind = "none" | "stop" | "start" | "create";

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

function jobBody(type: string, idSuffix: string) {
  return {
    id: `77777777-7777-7777-7777-7777777777${idSuffix}`,
    type,
    status: "queued",
    attempts: 0,
    created_at: "2026-10-27T00:00:00Z",
    node_id: "node-sv-01",
    pond_id: POND_ID,
    claimed_at: null,
    completed_at: null,
    last_error: null,
  };
}

async function installApi(
  page: Page,
  getPhase: () => PondPhase,
  setPhase: (p: PondPhase) => void,
  getFail: () => FailKind,
  setFail: (f: FailKind) => void,
) {
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
      setFail("none");
      return json(route, 202, {
        pond: { ...basePond, desired_state: "stopped", observed_state: "running", healthy: true },
        job: jobBody("stop_pond", "01"),
      });
    }
    if (method === "POST" && pathname.endsWith(`/ponds/${POND_ID}/start`)) {
      const phase = getPhase();
      if (phase.observed_state !== "stopped") {
        return json(route, 409, { code: "pond_busy", message: "busy", request_id: "req" });
      }
      setPhase({ desired_state: "running", observed_state: "stopped" });
      setFail("none");
      return json(route, 202, {
        pond: { ...basePond, desired_state: "running", observed_state: "stopped", healthy: false },
        job: jobBody("start_pond", "02"),
      });
    }
    if (method === "POST" && pathname.endsWith(`/ponds/${POND_ID}/retry`)) {
      const fail = getFail();
      if (fail === "stop") {
        setPhase({ desired_state: "stopped", observed_state: "running", last_error: null });
        return json(route, 202, { job: jobBody("stop_pond", "03") });
      }
      // start | create → starting (never En cola / pending)
      setPhase({ desired_state: "running", observed_state: "stopped", last_error: null });
      const type = fail === "create" ? "create_pond" : "start_pond";
      return json(route, 202, { job: jobBody(type, "04") });
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

async function awaitBadge(page: Page, pattern: RegExp) {
  await expect(page.getByTestId("pond-status-badge")).toHaveText(pattern, { timeout: 20_000 });
}

async function shoot(page: Page, stem: string) {
  fs.mkdirSync(shotsDir, { recursive: true });
  try {
    fs.mkdirSync(mediaDir, { recursive: true });
  } catch {
    // CI runners lack the agent store mount; local gate copies still land under artifacts/.
  }
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    const file = `${stem}-${width}.png`;
    const buf = await page.screenshot({ fullPage: true });
    fs.writeFileSync(path.join(shotsDir, file), buf);
    try {
      fs.writeFileSync(path.join(mediaDir, file), buf);
    } catch {
      /* optional store path */
    }
  }
  await page.setViewportSize({ width: 1440, height: 900 });
}

function harness(initial: PondPhase, fail: FailKind = "none") {
  let phase = initial;
  let lastFail = fail;
  return {
    getPhase: () => phase,
    setPhase: (p: PondPhase) => {
      phase = p;
    },
    getFail: () => lastFail,
    setFail: (f: FailKind) => {
      lastFail = f;
    },
    mutatePhase: (p: PondPhase) => {
      phase = p;
    },
    mutateFail: (f: FailKind) => {
      lastFail = f;
    },
  };
}

test.describe("CCR #131 pond lifecycle — 9 transitions", () => {
  test("1 PostStop: running → stopping (Deteniendo…)", async ({ page }) => {
    const h = harness({ desired_state: "running", observed_state: "running" });
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /En línea/);
    await page.getByTestId("pond-stop").click();
    await awaitBadge(page, /Deteniendo/);
    await expect(page.getByText("En cola")).toHaveCount(0);
  });

  test("2 StopOk: stopping → stopped (Detenido)", async ({ page }) => {
    const h = harness({ desired_state: "stopped", observed_state: "running" });
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Deteniendo/);
    h.mutatePhase({ desired_state: "stopped", observed_state: "stopped" });
    await awaitBadge(page, /Detenido/);
  });

  test("3 StopFailed: stopping → error (Con fallas)", async ({ page }) => {
    const h = harness({ desired_state: "stopped", observed_state: "running" });
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Deteniendo/);
    h.mutatePhase({ desired_state: "stopped", observed_state: "failed", last_error: "stop boom" });
    h.mutateFail("stop");
    await awaitBadge(page, /Con fallas/);
  });

  test("4 PostStart: stopped → starting (Iniciando…)", async ({ page }) => {
    const h = harness({ desired_state: "stopped", observed_state: "stopped" });
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Detenido/);
    await page.getByTestId("pond-start").click();
    await awaitBadge(page, /Iniciando/);
    await expect(page.getByText("En cola")).toHaveCount(0);
  });

  test("5 StartOk: starting → running (En línea)", async ({ page }) => {
    const h = harness({ desired_state: "running", observed_state: "stopped" });
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Iniciando/);
    h.mutatePhase({ desired_state: "running", observed_state: "running" });
    await awaitBadge(page, /En línea/);
  });

  test("6 StartFailed: starting → error (Con fallas)", async ({ page }) => {
    const h = harness({ desired_state: "running", observed_state: "stopped" });
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Iniciando/);
    h.mutatePhase({ desired_state: "running", observed_state: "failed", last_error: "start boom" });
    h.mutateFail("start");
    await awaitBadge(page, /Con fallas/);
  });

  test("7 CreateFailed: starting → error (create → Con fallas)", async ({ page }) => {
    const h = harness({ desired_state: "running", observed_state: "stopped" }, "create");
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Iniciando/);
    h.mutatePhase({ desired_state: "running", observed_state: "failed", last_error: "create boom" });
    h.mutateFail("create");
    await awaitBadge(page, /Con fallas/);
    await expect(page.getByText("En cola")).toHaveCount(0);
  });

  test("8 RetryStop: error → stopping → stopped (Detenido)", async ({ page }) => {
    const h = harness(
      { desired_state: "stopped", observed_state: "failed", last_error: "stop boom" },
      "stop",
    );
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Con fallas/);
    await page.getByTestId("pond-retry").click();
    await awaitBadge(page, /Deteniendo/);
    await expect(page.getByText("En cola")).toHaveCount(0);
    h.mutatePhase({ desired_state: "stopped", observed_state: "stopped" });
    await awaitBadge(page, /Detenido/);
    await shoot(page, "retry-stop-detenido");
  });

  test("9 RetryStart[create]: error → starting → running (Iniciando… → En línea)", async ({
    page,
  }) => {
    const h = harness(
      { desired_state: "running", observed_state: "failed", last_error: "create boom" },
      "create",
    );
    await installApi(page, h.getPhase, h.setPhase, h.getFail, h.setFail);
    await loginToPond(page);
    await awaitBadge(page, /Con fallas/);
    await page.getByTestId("pond-retry").click();
    await awaitBadge(page, /Iniciando/);
    await expect(page.getByText("En cola")).toHaveCount(0);
    h.mutatePhase({ desired_state: "running", observed_state: "running" });
    await awaitBadge(page, /En línea/);
    await shoot(page, "retry-create-en-linea");
  });
});
