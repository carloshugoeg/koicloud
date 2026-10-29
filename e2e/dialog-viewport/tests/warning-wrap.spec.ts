import { expect, test, type Page } from "@playwright/test";
import { installApi, login, type Role } from "../support/api";

const VIEWPORTS = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
] as const;

type WarningCase = {
  id: "restore" | "suspend";
  role: Role;
  path: string;
  opener: string;
  dialog: RegExp;
  warning: RegExp;
};

const CASES: readonly WarningCase[] = [
  {
    id: "restore",
    role: "client",
    path: "/app/ponds/66666666-6666-6666-6666-666666666666/backups",
    opener: "Restaurar…",
    dialog: /Restaurar respaldo/i,
    warning:
      /Esto borra los datos actuales de inventario-demo y los reemplaza por el respaldo\. No se puede deshacer\./,
  },
  {
    id: "suspend",
    role: "admin",
    path: "/app/admin/users",
    opener: "Suspender",
    dialog: /Suspender a/i,
    warning:
      /La cuenta no podrá iniciar sesión\. Sus ponds siguen corriendo y no se borra ningún dato\./,
  },
];

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

for (const item of CASES) {
  for (const viewport of VIEWPORTS) {
    test(`${item.id} warning wraps fully @ ${viewport.width}`, async ({ page }) => {
      await installApi(page);
      await login(page, item.role);
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      await goto(page, item.path);

      const opener = page.getByRole("button", { name: item.opener, exact: true });
      await expect(opener).toHaveCount(1);
      await opener.click();

      const dialog = page.getByRole("dialog", { name: item.dialog });
      await expect(dialog).toBeVisible();

      const warning = dialog.getByText(item.warning);
      await expect(warning).toBeVisible();
      await expect(warning).toHaveCSS("text-overflow", "clip");
      await expect(warning).not.toHaveCSS("white-space", "nowrap");

      const box = await warning.boundingBox();
      expect(box, "warning bounding box").not.toBeNull();
      const lineHeight = Number.parseFloat(await warning.evaluate((el) => getComputedStyle(el).lineHeight));
      expect(box!.height, "warning wraps past one line").toBeGreaterThan(lineHeight + 1);

      const truncated = await warning.evaluate((el) => {
        const styles = getComputedStyle(el);
        if (styles.textOverflow !== "ellipsis") {
          return false;
        }
        return el.scrollWidth > el.clientWidth + 1;
      });
      expect(truncated, "warning must not clip with an ellipsis").toBe(false);
    });
  }
}
