import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type APIResponse, type Page } from "@playwright/test";

const suiteRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const shotsDir = path.join(suiteRoot, "artifacts");
const cursorShotsDir = "/opt/cursor/artifacts/preview-login";

const VIEWPORTS = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
] as const;

const WRONG_LOGIN = {
  email: "nobody-preview-gate@koicloud.invalid",
  password: "wrong-password",
} as const;

type ErrorBody = {
  code?: string;
};

function requireGateAdmin(): { email: string; password: string } {
  const email = process.env.KOI_GATE_ADMIN_EMAIL?.trim() ?? "";
  const password = process.env.KOI_GATE_ADMIN_PASSWORD ?? "";
  if (email.length === 0 || password.length === 0) {
    throw new Error(
      "Set KOI_GATE_ADMIN_EMAIL and KOI_GATE_ADMIN_PASSWORD to run the preview login success case. Do not commit those values. The wrong-password case does not need them.",
    );
  }
  return { email, password };
}

async function readJsonBody(response: APIResponse): Promise<unknown> {
  const contentType = response.headers()["content-type"] ?? "";
  expect(contentType).toContain("application/json");
  const text = await response.text();
  expect(text.trimStart().startsWith("<")).toBe(false);
  return JSON.parse(text) as unknown;
}

function originOf(response: APIResponse): string {
  return new URL(response.url()).origin;
}

async function expectNoAxeViolations(page: Page): Promise<void> {
  const results = await new AxeBuilder({ page }).analyze();
  const lines = results.violations.map((violation) => {
    const target = violation.nodes[0]?.target.join(" ") ?? "";
    return `${violation.id} (${violation.impact ?? "unknown"}) ${violation.help} ${target}`;
  });
  expect(lines, lines.join("\n")).toEqual([]);
}

async function shootApp(page: Page): Promise<void> {
  fs.mkdirSync(shotsDir, { recursive: true });
  fs.mkdirSync(cursorShotsDir, { recursive: true });
  for (const viewport of VIEWPORTS) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await expect(page.getByRole("heading", { name: "Ponds", level: 1 })).toBeVisible();
    const file = `after-login-${viewport.width}.png`;
    const image = await page.screenshot({ fullPage: true });
    fs.writeFileSync(path.join(shotsDir, file), image);
    fs.writeFileSync(path.join(cursorShotsDir, file), image);
    await expectNoAxeViolations(page);
  }
}

test("wrong password returns 401 invalid_credentials JSON", async ({ request, baseURL }) => {
  const response = await request.post("/api/v1/auth/login", {
    data: WRONG_LOGIN,
    headers: { accept: "application/json" },
  });

  expect(
    response.status(),
    "POST /api/v1/auth/login must return API JSON, not the SPA 405 HTML fallback",
  ).toBe(401);
  expect(originOf(response)).toBe(new URL(baseURL ?? "").origin);

  const body = (await readJsonBody(response)) as ErrorBody;
  expect(body.code).toBe("invalid_credentials");
});

test("Escape keeps focus on a control in the login form", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  await expect(page.getByLabel("Correo")).toBeVisible();
  await expect(page.getByLabel("Contraseña")).toBeVisible();

  await page.getByLabel("Contraseña").focus();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Mostrar" })).toBeFocused();

  await page.keyboard.press("Escape");
  const focused = page.locator("form").locator(":focus");
  await expect(focused).toHaveCount(1);
  await expect(focused).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
});

for (const viewport of VIEWPORTS) {
  test(`login page has no axe violations at ${viewport.width}`, async ({ page }) => {
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Iniciar sesión" })).toBeVisible();
    await expectNoAxeViolations(page);
  });
}

test("gate admin login returns 200 and lands on /app", async ({ page, request, baseURL }) => {
  const admin = requireGateAdmin();
  const response = await request.post("/api/v1/auth/login", {
    data: admin,
    headers: { accept: "application/json" },
  });

  expect(
    response.status(),
    "POST /api/v1/auth/login must return API JSON, not the SPA 405 HTML fallback",
  ).toBe(200);
  expect(originOf(response)).toBe(new URL(baseURL ?? "").origin);

  const body = (await readJsonBody(response)) as { access_token?: unknown };
  if (typeof body.access_token !== "string" || body.access_token.length === 0) {
    throw new Error("Login HTTP 200 JSON did not include an access_token string.");
  }

  await page.goto("/login");
  await page.getByLabel("Correo").fill(admin.email);
  await page.getByLabel("Contraseña").fill(admin.password);

  const uiLogin = page.waitForResponse((candidate) => {
    return candidate.request().method() === "POST" && candidate.url().includes("/api/v1/auth/login");
  });
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  const uiResponse = await uiLogin;

  expect(uiResponse.status()).toBe(200);
  expect(uiResponse.headers()["content-type"] ?? "").toContain("application/json");
  expect(originOf(uiResponse)).toBe(new URL(baseURL ?? "").origin);

  await expect(page).toHaveURL(/\/app$/);
  await expect(page.getByRole("heading", { name: "Ponds", level: 1 })).toBeVisible();
  await shootApp(page);
});
