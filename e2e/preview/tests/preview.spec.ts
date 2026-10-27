import { expect, test, type Page } from "@playwright/test";
import { loadGateCreds, secretValues, type GateCreds } from "./support/creds";
import {
  capture,
  installApiProxy,
  publicPreviewOrigin,
  recordFlow,
} from "./support/proxy";
import { errorNote } from "./support/redact";
import {
  api,
  clickNav,
  ensureProPlan,
  login,
  purgePonds,
  resetSession,
} from "./support/session";

test.beforeEach(async ({ page }) => {
  resetSession();
  await installApiProxy(page);
});

test("auth login", async ({ page }) => {
  const creds = loadGateCreds();
  await run(page, "auth login", "auth-login", secrets(creds), async () => {
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    await expect(
      page.getByRole("heading", { name: /Tus ponds|Todavía no tenés ponds/ }),
    ).toBeVisible();
    return "session reached /app";
  });
});

test("auth register", async ({ page }) => {
  const creds = loadGateCreds();
  const password = `Gate${Date.now().toString(36)}`;
  const email = `gate-reg-${Date.now().toString(36)}@koicloud.test`;
  await run(page, "auth register", "auth-register", [...secrets(creds), password], async () => {
    await page.goto("/register");
    await page.getByLabel("Nombre completo").fill("Gate Register");
    await page.getByLabel("Correo").fill(email);
    await page.getByLabel("Contraseña").fill(password);
    await page.getByRole("button", { name: "Crear cuenta" }).click();
    await expect(page.getByRole("heading", { name: "Revisa tu correo" })).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();
    return "verification notice shown";
  });
});

test("auth error", async ({ page }) => {
  const creds = loadGateCreds();
  await run(page, "auth error", "auth-error", secrets(creds), async () => {
    await page.goto("/login");
    await page.getByLabel("Correo").fill(creds.user.email);
    await page.getByLabel("Contraseña").fill("not-the-gate-password");
    await page.getByRole("button", { name: "Iniciar sesión" }).click();
    await expect(page.getByRole("alert")).toContainText("Correo o contraseña incorrectos.");
    await expect(page).toHaveURL(/\/login/);
    return "invalid credentials stay on /login";
  });
});

test("plans checkout", async ({ page }) => {
  const creds = loadGateCreds();
  await run(page, "plans / simulated checkout", "plans-checkout", secrets(creds), async () => {
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    await clickNav(page, "Planes");
    await expect(page.getByRole("heading", { name: "Planes disponibles" })).toBeVisible();
    await page.getByTestId("plan-card-sandbox").getByRole("button").click();
    await expect(page.getByRole("dialog")).toContainText("Pago simulado");
    await page.getByLabel("Número de tarjeta simulada").fill("4242424242424242");
    await page.getByLabel("Expiración").fill("12/30");
    await page.getByLabel("CVC").fill("123");
    await page.getByRole("button", { name: "Confirmar contratación" }).click();
    const created = page.getByRole("heading", { name: "Nuevo pond" });
    const problem = page.getByRole("alert");
    await expect(created.or(problem)).toBeVisible();
    if (await problem.isVisible()) {
      throw new Error(await problem.innerText());
    }
    return "sandbox checkout opened the create dialog";
  });
});

test("pond lifecycle", async ({ page }) => {
  // Preview QueryClient staleTime is 30s; delete UI needs a refetch after that.
  // Start/stop UI deferred (wave B1). Preview create drains jobs → running.
  test.setTimeout(180_000);
  const creds = loadGateCreds();
  const hidden = secrets(creds);
  const failures: string[] = [];
  await login(page, creds.user);
  await expect(page).toHaveURL(/\/app/);
  // Plans checkout may leave sandbox (1 pond). Restore pro and clear leftovers
  // (including ponds left by the MCP suite that runs before this file).
  await ensureProPlan(page);
  await purgePonds(page);
  // Auth is in-memory (zustand) — a full reload would dump the session to /login.
  // Re-login to clear the React Query ponds cache without losing the SPA session.
  await login(page, creds.user);
  await expect(page).toHaveURL(/\/app/);

  const pondNameBase = `gate${Date.now().toString(36).slice(-6)}`;
  let pondName = pondNameBase;
  let pondId = "";

  await check(page, failures, "pond create", "pond-create", hidden, async () => {
    let lastError = "create did not open the pond";
    for (let attempt = 0; attempt < 3; attempt += 1) {
      const name = attempt === 0 ? pondNameBase : `${pondNameBase}${attempt}`;
      await clickNav(page, "Crear pond");
      await expect(page.getByTestId("create-pond-veil")).toBeVisible();
      await page.getByTestId("create-pond-name").fill(name);
      await expect(page.getByText("nombre válido")).toBeVisible();
      const navigated = page.waitForURL(/\/app\/ponds\/[0-9a-f-]{36}/i, { timeout: 45_000 });
      await page.getByTestId("create-pond-submit").click();
      try {
        await navigated;
        pondId = new URL(page.url()).pathname.split("/").pop() ?? "";
        pondName = name;
        await expect(page.getByRole("heading", { name })).toBeVisible();
        // Preview mock drains CREATE_POND inline — no VPS / start control.
        await expect(page.getByTestId("pond-status-badge")).toContainText("En línea", {
          timeout: 45_000,
        });
        const fetched = await api(page, "GET", `/api/v1/ponds/${pondId}`);
        const state =
          (fetched.json as { pond?: { observed_state?: unknown } } | null)?.pond?.observed_state;
        if (state !== "running") {
          throw new Error(`GET pond state ${String(state)} (want running)`);
        }
        await expect(page.getByTestId("pond-detail-actions")).toBeVisible();
        await expect(page.getByRole("button", { name: /Detener|Iniciar/i })).toHaveCount(0);
        return `created ${name} running (preview drain)`;
      } catch (error) {
        const errBox = page.getByTestId("create-pond-error");
        if ((await errBox.count()) > 0) {
          lastError = (await errBox.innerText()).replace(/\s+/g, " ").slice(0, 180);
          if (/internal_error|Algo salió mal/i.test(lastError) && attempt < 2) {
            await page.goto("/app");
            await page.waitForTimeout(1_000 * (attempt + 1));
            continue;
          }
          throw new Error(lastError);
        }
        if (error instanceof Error && /internal_error|Algo salió mal/i.test(error.message) && attempt < 2) {
          await page.goto("/app");
          await page.waitForTimeout(1_000 * (attempt + 1));
          continue;
        }
        throw error;
      }
    }
    throw new Error(lastError);
  });

  await check(page, failures, "SQL console", "sql-console", hidden, async () => {
    await page.getByRole("link", { name: "Consola" }).click();
    await expect(page.getByTestId("sql-console")).toBeVisible();
    // CodeMirror exposes a textbox with the same aria-label — use testid only.
    await expect(page.getByTestId("sql-editor")).toBeVisible();
    await page.getByTestId("sql-run").click();
    await expect(page.getByTestId("sql-results")).toBeVisible();
    await expect(page.getByTestId("sql-results-meta")).toContainText("filas");
    return "SELECT 1 rendered a result table";
  });

  await check(page, failures, "pond backup", "pond-backup", hidden, async () => {
    await page.getByRole("link", { name: "Resumen" }).click();
    await expect(page.getByTestId("pond-detail")).toBeVisible();
    await page.getByTestId("trigger-backup").click();
    const dialog = page.getByTestId("backup-confirm-dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByTestId("backup-confirm-button").click();
    await expect(page.getByTestId("backup-queued")).toBeVisible({ timeout: 30_000 });
    await page.getByRole("link", { name: "Respaldos" }).click();
    await expect(page.getByTestId("backups-page")).toBeVisible();
    await expect(page.getByTestId("backups-empty")).toHaveCount(0);
    return "backup confirm dialog → list visible";
  });

  await check(page, failures, "pond restore", "pond-restore", hidden, async () => {
    await expect(page.getByTestId("backups-page")).toBeVisible();
    const restoreBtn = page.getByTestId("open-restore").first();
    await expect(restoreBtn).toBeVisible();
    await restoreBtn.click();
    const dialog = page.getByTestId("restore-dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByTestId("restore-confirm-input").fill(pondName);
    await dialog.getByTestId("restore-confirm-button").click();
    await expect(page.getByTestId("restore-queued").or(page.getByTestId("pond-status-badge"))).toBeVisible({
      timeout: 30_000,
    });
    await page.getByRole("link", { name: "Resumen" }).click();
    await expect(page.getByTestId("pond-status-badge")).toContainText(/En línea|Restaurando/, {
      timeout: 30_000,
    });
    await expect(page.getByTestId("pond-status-badge")).toContainText("En línea", {
      timeout: 45_000,
    });
    return "restore confirm dialog → running";
  });

  await check(page, failures, "pond limits / errors", "pond-limits", hidden, async () => {
    await clickNav(page, "Crear pond");
    await page.getByTestId("create-pond-name").fill("A");
    await expect(page.getByTestId("create-pond-issues")).toContainText("Mínimo 3 caracteres.");
    await expect(page.getByTestId("create-pond-submit")).toBeDisabled();
    await page.getByTestId("create-pond-name").fill(pondName);
    await expect(page.getByTestId("create-pond-submit")).toBeEnabled();
    await page.getByTestId("create-pond-submit").click();
    const error = page.getByTestId("create-pond-error");
    const opened = page.waitForURL(/\/app\/ponds\/[0-9a-f-]{36}/i, { timeout: 8_000 }).then(
      () => "opened" as const,
      () => "stayed" as const,
    );
    const outcome = await Promise.race([
      error.waitFor({ state: "visible", timeout: 8_000 }).then(() => "error" as const),
      opened,
    ]);
    if (outcome !== "error") {
      throw new Error(`duplicate submit ${outcome}`);
    }
    await expect(error).toContainText(/ya está en uso|máximo de ponds/);
    return "duplicate name or quota rejected";
  });

  await check(page, failures, "pond delete", "pond-delete", hidden, async () => {
    await page.getByRole("link", { name: "Cancelar" }).click();
    await expect(page).toHaveURL(/\/app\/ponds\/?$/);
    await page.locator(`tr[data-pond-id="${pondId}"]`).getByRole("link", { name: "Abrir" }).click();
    await expect(page.getByTestId("pond-detail")).toBeVisible();
    await page.getByTestId("open-delete-pond").click();
    const dialog = page.getByTestId("delete-pond-dialog");
    await expect(dialog).toBeVisible();
    await dialog.getByTestId("delete-confirm-input").fill(pondName);
    await dialog.getByTestId("delete-confirm-button").click();
    await expect(page).toHaveURL(/\/app\/ponds\/?$/, { timeout: 45_000 });
    const listed = await api(page, "GET", "/api/v1/ponds");
    const ponds = (listed.json as { ponds?: Array<{ id?: unknown }> } | null)?.ponds;
    if (!Array.isArray(ponds)) {
      throw new Error("list ponds missing after delete");
    }
    if (ponds.some((row) => row && row.id === pondId)) {
      throw new Error("list still contains the deleted pond id");
    }
    resetSession();
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    await expect(page.locator(`tr[data-pond-id="${pondId}"]`)).toHaveCount(0);
    await expect(page.getByRole("cell", { name: pondName, exact: true })).toHaveCount(0);
    return "delete confirm dialog → pond left the list";
  });

  expect(failures, failures.join(", ")).toEqual([]);
});

test("agent access", async ({ page }) => {
  const creds = loadGateCreds();
  await run(page, "agent-access UI", "agent-access", secrets(creds), async () => {
    const previewHost = new URL(publicPreviewOrigin()).host;
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    expect(page.url()).toContain(".vercel.app");
    await clickNav(page, "Acceso agente");
    await expect(page.getByTestId("agent-access")).toBeVisible();
    await expect(page.getByTestId("agent-slug")).not.toBeEmpty();
    await expect(page.getByTestId("agent-url")).toContainText(/mcp/i);
    await expect(page.getByTestId("agent-url")).toContainText(previewHost);
    await expect(page.getByTestId("agent-url")).not.toContainText("127.0.0.1");
    await expect(page.getByTestId("agent-url")).not.toContainText("localhost");
    await expect(page.getByTestId("agent-enabled")).toContainText(/habilitado|deshabilitado/);
    await expect(page.getByTestId("agent-password-band")).toHaveCount(0);
    return `slug and preview MCP URL on ${previewHost}, password sealed`;
  });
});

test("admin suspend", async ({ page }) => {
  const creds = loadGateCreds();
  await run(page, "admin suspend", "admin-suspend", secrets(creds), async () => {
    await login(page, creds.admin);
    await expect(page).toHaveURL(/\/app/);
    await clickNav(page, "Usuarios");
    const loaded = page.getByTestId("admin-users-page");
    const errored = page.getByTestId("admin-users-error");
    await expect(loaded.or(errored)).toBeVisible();
    if (await errored.isVisible()) {
      throw new Error((await errored.innerText()).replace(/\s+/g, " ").slice(0, 180));
    }
    const row = page.locator("tr", { hasText: creds.user.email });
    await row.getByRole("button", { name: "Suspender" }).click();
    await page.getByTestId("suspend-confirm-email").fill(creds.user.email);
    await page.getByTestId("suspend-motivo").fill("preview e2e");
    await page.getByTestId("suspend-submit").click();
    await expect(page.getByTestId("suspend-dialog")).toHaveCount(0);
    await expect(row).toContainText("suspendido");
    // Leave the gate user active so later local re-runs can still log in.
    await row.getByRole("button", { name: "Reactivar" }).click();
    await page.getByTestId("reactivate-submit").click();
    await expect(page.getByTestId("reactivate-dialog")).toHaveCount(0);
    await expect(row).toContainText("activo");
    return "gate user suspended then reactivated";
  });
});

function secrets(creds: GateCreds): string[] {
  return secretValues(creds);
}

async function run(
  page: Page,
  flow: string,
  slug: string,
  hidden: string[],
  body: () => Promise<string>,
): Promise<void> {
  try {
    const note = await body();
    const shots = await capture(page, slug);
    recordFlow({ flow, result: "pass", note, ...shots });
  } catch (error) {
    await recordFailure(page, flow, slug, hidden, error);
    throw error;
  }
}

async function check(
  page: Page,
  failures: string[],
  flow: string,
  slug: string,
  hidden: string[],
  body: () => Promise<string>,
): Promise<void> {
  try {
    const note = await body();
    const shots = await capture(page, slug);
    recordFlow({ flow, result: "pass", note, ...shots });
  } catch (error) {
    failures.push(flow);
    await recordFailure(page, flow, slug, hidden, error);
  }
}

async function recordFailure(
  page: Page,
  flow: string,
  slug: string,
  hidden: string[],
  error: unknown,
): Promise<void> {
  let shot375 = false;
  let shot768 = false;
  let shot1440 = false;
  try {
    const shots = await capture(page, slug);
    shot375 = shots.shot375;
    shot768 = shots.shot768;
    shot1440 = shots.shot1440;
  } catch {
    shot375 = false;
    shot768 = false;
    shot1440 = false;
  }
  recordFlow({
    flow,
    result: "fail",
    note: errorNote(error, hidden),
    shot375,
    shot768,
    shot1440,
  });
}
