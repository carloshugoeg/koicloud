import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type Page, type Route } from "../fixtures";

const root = path.dirname(fileURLToPath(import.meta.url));
const shotsDir = path.resolve(root, "../artifacts/shots");

const POND_ID = "66666666-6666-6666-6666-666666666666";
const BACKUP_ID = "99999999-9999-9999-9999-999999999999";
const JOB_ID = "88888888-8888-8888-8888-888888888888";
const POND_NAME = "demo-pond";

const user = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "demo@koicloud.dev",
  full_name: "Operador Demo",
  role: "client",
  status: "active",
  email_verified: true,
  onboarded: true,
  nit: "0614-220999-101-3",
  created_at: "2026-09-22T20:00:00Z",
};

const pond = {
  id: POND_ID,
  name: POND_NAME,
  engine_version: "16",
  plan_id: "micro",
  node_id: "node-sv-01",
  host_port: 15007,
  user_id: user.id,
  size_bytes: 124901,
  healthy: true,
  created_at: "2026-09-22T20:00:00Z",
  desired_state: "running",
  observed_state: "running",
  last_restore_at: null as string | null,
  last_error: null as string | null,
};

const backup = {
  id: BACKUP_ID,
  pond_id: POND_ID,
  kind: "on_demand",
  status: "succeeded",
  storage_path: "/tmp/koicloud/backups/demo-pond.sql",
  size_bytes: 128,
  sha256: "ab".repeat(32),
  created_at: "2026-10-01T15:00:00Z",
  completed_at: "2026-10-01T15:01:00Z",
  expires_at: "2026-10-08T15:00:00Z",
};

function job(status: string, lastError: string | null = null) {
  return {
    id: JOB_ID,
    type: "restore_pond",
    pond_id: POND_ID,
    node_id: "node-sv-01",
    status,
    attempts: status === "queued" ? 0 : 1,
    created_at: "2026-10-02T12:00:00Z",
    claimed_at: status === "queued" ? null : "2026-10-02T12:00:02Z",
    completed_at: status === "succeeded" || status === "failed" ? "2026-10-02T12:00:05Z" : null,
    last_error: lastError,
  };
}

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

async function installApi(
  page: Page,
  onJob: (reads: number) => { status: number; body: unknown } = (reads) => ({
    status: 200,
    body: { job: job(reads < 2 ? "queued" : "succeeded") },
  }),
) {
  let jobReads = 0;
  await page.route("**/api/v1/**", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    const { pathname } = url;
    const method = req.method();

    if (method === "POST" && pathname.endsWith("/auth/refresh")) {
      return json(route, 401, { code: "token_invalid", message: "no session", request_id: "req" });
    }
    if (method === "POST" && pathname.endsWith("/auth/login")) {
      return json(route, 200, { access_token: "access_e2e", refresh_token: "refresh_e2e", user });
    }
    if (method === "GET" && pathname.endsWith("/me")) {
      return json(route, 200, { user });
    }
    if (method === "GET" && pathname.endsWith("/plans")) {
      return json(route, 200, { plans: [] });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}/backups`)) {
      return json(route, 200, { backups: [backup], next_cursor: null });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}/jobs/${JOB_ID}`)) {
      jobReads += 1;
      const result = onJob(jobReads);
      return json(route, result.status, result.body);
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}`)) {
      return json(route, 200, { pond });
    }
    if (method === "GET" && pathname.endsWith("/ponds")) {
      return json(route, 200, { ponds: [pond], next_cursor: null });
    }
    if (method === "POST" && pathname.endsWith(`/ponds/${POND_ID}/restore`)) {
      return json(route, 202, { job: job("queued") });
    }
    return json(route, 404, { code: "not_found", message: pathname, request_id: "req" });
  });
  return {
    jobReads: () => jobReads,
  };
}

test("restore job read error offers retry", async ({ page }) => {
  const api = await installApi(page, () => ({
    status: 500,
    body: { code: "internal_error", message: "boom", request_id: "req" },
  }));

  await page.goto("/login?next=" + encodeURIComponent(`/app/ponds/${POND_ID}/backups`));
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByTestId("backups-page")).toBeVisible();

  await page.getByRole("button", { name: "Restaurar…" }).click();
  await page.getByTestId("restore-confirm-input").fill(POND_NAME);
  await page.getByTestId("restore-confirm-button").click();

  await expect(page.getByTestId("restore-job-error")).toContainText(
    "No pudimos leer el estado de la restauración.",
  );
  await expect(page.getByRole("button", { name: "Reintentar" })).toBeVisible();
  await expect(page.getByTestId("restore-job-status")).toHaveCount(0);

  const readsAtError = api.jobReads();
  await page.waitForTimeout(1500);
  expect(api.jobReads()).toBe(readsAtError);

  const outDir = path.resolve("/opt/cursor/artifacts/restore-job-error");
  fs.mkdirSync(outDir, { recursive: true });
  fs.mkdirSync(shotsDir, { recursive: true });
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);
    const file = `restore-error-${width}.png`;
    await page.screenshot({ path: path.join(outDir, file), fullPage: true });
    await page.screenshot({ path: path.join(shotsDir, file), fullPage: true });
  }
});

test("restore job status reaches succeeded", async ({ page }) => {
  await installApi(page);
  await page.goto("/login?next=" + encodeURIComponent(`/app/ponds/${POND_ID}/backups`));
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByTestId("backups-page")).toBeVisible();

  await page.getByRole("button", { name: "Restaurar…" }).click();
  await page.getByTestId("restore-confirm-input").fill(POND_NAME);
  await page.getByTestId("restore-confirm-button").click();

  const status = page.getByTestId("restore-job-status");
  await expect(status).toHaveText("queued");
  await expect(status).toHaveText("succeeded", { timeout: 15_000 });
  await expect(page.getByText(JOB_ID)).toBeVisible();

  fs.mkdirSync(shotsDir, { recursive: true });
  for (const width of [375, 768, 1440] as const) {
    await page.setViewportSize({ width, height: width === 375 ? 812 : 900 });
    const box = await page.locator("body").boundingBox();
    expect(box?.width).toBeLessThanOrEqual(width);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    expect(overflow).toBe(false);
    await page.screenshot({
      path: path.join(shotsDir, `restore-succeeded-${width}.png`),
      fullPage: true,
    });
  }
});
