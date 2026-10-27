import { expect, test, type Page } from "@playwright/test";
import { loadGateCreds, secretValues, type GateCreds } from "./support/creds";
import { capture, installApiProxy, recordFlow, resetSession } from "./support/proxy";
import { errorNote } from "./support/redact";
import {
  api,
  clickNav,
  deletePond,
  ensureProPlan,
  login,
  purgePonds,
  stopPond,
  triggerBackup,
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
  // Preview QueryClient staleTime is 30s; stop/delete UI needs a refetch after that.
  test.setTimeout(180_000);
  const creds = loadGateCreds();
  const hidden = secrets(creds);
  const failures: string[] = [];
  await login(page, creds.user);
  await expect(page).toHaveURL(/\/app/);
  // Plans checkout may leave sandbox (1 pond). Restore pro and clear leftovers.
  await ensureProPlan(page);
  await purgePonds(page);

  const pondName = `gate${Date.now().toString(36).slice(-6)}`;
  let pondId = "";

  await check(page, failures, "pond create", "pond-create", hidden, async () => {
    await clickNav(page, "Crear pond");
    await page.getByTestId("create-pond-name").fill(pondName);
    await expect(page.getByText("nombre válido")).toBeVisible();
    const navigated = page.waitForURL(/\/app\/ponds\/[0-9a-f-]{36}/i, { timeout: 20_000 });
    await page.getByTestId("create-pond-submit").click();
    try {
      await navigated;
    } catch {
      const error = page.getByTestId("create-pond-error");
      if ((await error.count()) > 0) {
        throw new Error((await error.innerText()).replace(/\s+/g, " ").slice(0, 180));
      }
      throw new Error("create did not open the pond");
    }
    pondId = new URL(page.url()).pathname.split("/").pop() ?? "";
    await expect(page.getByRole("heading", { name: pondName })).toBeVisible();
    return `created ${pondName}`;
  });

  await check(page, failures, "pond start (→ running)", "pond-start", hidden, async () => {
    await expect(page.getByTestId("pond-status-badge")).toContainText("En línea", {
      timeout: 30_000,
    });
    return "badge En línea";
  });

  await check(page, failures, "SQL console", "sql-console", hidden, async () => {
    await page.getByRole("link", { name: "Consola" }).click();
    await expect(page.getByTestId("sql-console")).toBeVisible();
    await page.getByTestId("sql-run").click();
    await expect(page.getByTestId("sql-results")).toBeVisible();
    await expect(page.getByTestId("sql-results-meta")).toContainText("filas");
    return "SELECT 1 rendered a result table";
  });

  await check(page, failures, "pond backup", "pond-backup", hidden, async () => {
    const status = await triggerBackup(page, pondId);
    if (status !== 200 && status !== 202) {
      throw new Error(`backup HTTP ${status}`);
    }
    await page.getByRole("link", { name: "Respaldos" }).click();
    await expect(page.getByTestId("backups-page")).toBeVisible();
    await expect(page.getByTestId("backups-empty")).toHaveCount(0);
    return `backup list visible after HTTP ${status}`;
  });

  await check(page, failures, "pond stop (sim)", "pond-stop", hidden, async () => {
    await page.getByRole("link", { name: "Resumen" }).click();
    await expect(page.getByTestId("pond-status-badge")).toContainText("En línea");
    await stopPond(page, pondId);
    const fetched = await api(page, "GET", `/api/v1/ponds/${pondId}`);
    const state =
      (fetched.json as { pond?: { observed_state?: unknown } } | null)?.pond?.observed_state ??
      "missing";
    if (state !== "stopped") {
      throw new Error(`GET pond state ${String(state)}`);
    }
    // Full reload clears the 30s React Query cache (refetchOnWindowFocus is off).
    resetSession();
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    await page.getByRole("link", { name: "Abrir" }).click();
    await expect(page.getByTestId("pond-status-badge")).toContainText("Detenido");
    return "badge Detenido";
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
    await deletePond(page, pondId);
    const listed = await api(page, "GET", "/api/v1/ponds");
    const ponds = (listed.json as { ponds?: Array<{ id?: unknown }> } | null)?.ponds;
    if (!Array.isArray(ponds)) {
      throw new Error("sim list ponds missing after delete");
    }
    if (ponds.some((row) => row && row.id === pondId)) {
      throw new Error("sim list still contains the deleted pond id");
    }
    resetSession();
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    await expect(page.locator(`tr[data-pond-id="${pondId}"]`)).toHaveCount(0);
    await expect(page.getByRole("cell", { name: pondName, exact: true })).toHaveCount(0);
    return "pond left the list";
  });

  expect(failures, failures.join(", ")).toEqual([]);
});

test("agent access", async ({ page }) => {
  const creds = loadGateCreds();
  await run(page, "agent-access UI", "agent-access", secrets(creds), async () => {
    await login(page, creds.user);
    await expect(page).toHaveURL(/\/app/);
    await clickNav(page, "Acceso agente");
    await expect(page.getByTestId("agent-access")).toBeVisible();
    await expect(page.getByTestId("agent-slug")).not.toBeEmpty();
    await expect(page.getByTestId("agent-url")).toContainText(/mcp/i);
    await expect(page.getByTestId("agent-enabled")).toContainText(/habilitado|deshabilitado/);
    await expect(page.getByTestId("agent-password-band")).toHaveCount(0);
    return "slug and URL visible, password sealed";
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
  let shot1440 = false;
  try {
    const shots = await capture(page, slug);
    shot375 = shots.shot375;
    shot1440 = shots.shot1440;
  } catch {
    shot375 = false;
    shot1440 = false;
  }
  recordFlow({
    flow,
    result: "fail",
    note: errorNote(error, hidden),
    shot375,
    shot1440,
  });
}
