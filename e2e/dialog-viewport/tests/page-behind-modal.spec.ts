import { expect, test, type Page } from "@playwright/test";
import { installApi, login } from "../support/api";

async function goto(page: Page, href: string) {
  await page.evaluate((next) => {
    const url = new URL(next, window.location.origin);
    const state = window.history.state;
    window.history.pushState(state, "", `${url.pathname}${url.search}${url.hash}`);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, href);
  const pathname = new URL(href, "http://127.0.0.1").pathname;
  const escaped = pathname.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  await expect(page).toHaveURL(new RegExp(`${escaped}(?:\\?|$)`));
}

test("page behind restore modal stays visible @ 768", async ({ page }) => {
  await installApi(page);
  await login(page, "client");
  await page.setViewportSize({ width: 768, height: 1024 });
  await goto(page, "/app/ponds/66666666-6666-6666-6666-666666666666/backups");

  const opener = page.getByRole("button", { name: "Restaurar…", exact: true });
  await expect(opener).toHaveCount(1);
  await opener.click();

  const dialog = page.getByRole("dialog", { name: /Restaurar respaldo/i });
  await expect(dialog).toBeVisible();

  // CSS locators: getByRole would miss #root under aria-hidden (intentional a11y).
  await expect(page.locator('[data-testid="backups-page"]')).toBeVisible();
  await expect(page.locator("h2", { hasText: "inventario-demo" })).toBeVisible();
  await expect(page.locator('button[data-testid="backup-now"]')).toBeVisible();
});
