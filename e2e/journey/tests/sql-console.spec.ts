import fs from "node:fs";
import { expect, test } from "../fixtures";
import { pondIdPath } from "../sql-global-setup";

const query = "SELECT n FROM probe";

test("one Ejecutar click returns the pond row and records history", async ({ page }) => {
  const pondId = fs.readFileSync(pondIdPath, "utf8").trim();
  const posts: string[] = [];
  page.on("request", (request) => {
    if (request.method() !== "POST") {
      return;
    }
    const pathname = new URL(request.url()).pathname;
    if (/\/api\/v1\/ponds\/[^/]+\/sql$/.test(pathname)) {
      posts.push(request.postData() ?? "");
    }
  });

  await page.goto(`/login?next=${encodeURIComponent(`/app/ponds/${pondId}/consola`)}`);
  await page.getByLabel("Correo").fill("demo@koicloud.dev");
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page.getByTestId("sql-console")).toBeVisible();

  const editor = page.getByTestId("sql-editor").getByRole("textbox");
  await editor.click();
  await page.keyboard.press("Control+A");
  await page.keyboard.type(query);
  await expect(editor).toHaveText(query);

  await page.getByRole("button", { name: "Ejecutar" }).click();

  const results = page.getByTestId("sql-results");
  await expect(results).toBeVisible();
  await expect(results.getByRole("cell", { name: "42", exact: true })).toBeVisible();
  await expect(page.getByTestId("sql-history")).toContainText(query);
  expect(posts).toHaveLength(1);
  expect(posts[0]).toContain(query);
});
