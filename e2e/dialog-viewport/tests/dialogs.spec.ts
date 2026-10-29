import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import { installApi, login, type Role } from "../support/api";

const VIEWPORTS = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
] as const;

type DialogCase = {
  id: string;
  role: Role;
  path: string;
  opener: string | null;
  dialog: RegExp | null;
  focus: "opener" | "app";
  widths: readonly number[];
};

const CASES: readonly DialogCase[] = [
  {
    id: "restore",
    role: "client",
    path: "/app/ponds/66666666-6666-6666-6666-666666666666/backups",
    opener: "Restaurar…",
    dialog: /Restaurar respaldo/i,
    focus: "opener",
    widths: [375, 768, 1440],
  },
  {
    id: "suspend",
    role: "admin",
    path: "/app/admin/users",
    opener: "Suspender",
    dialog: /Suspender a/i,
    focus: "opener",
    widths: [375, 768, 1440],
  },
  {
    id: "reactivate",
    role: "admin",
    path: "/app/admin/users",
    opener: "Reactivar",
    dialog: /Reactivar a/i,
    focus: "opener",
    widths: [375, 768, 1440],
  },
  {
    id: "checkout",
    role: "client",
    path: "/app/plans",
    opener: "Elegir plan Micro",
    dialog: /Contratar plan Micro/,
    focus: "opener",
    widths: [375, 768, 1440],
  },
  {
    id: "confirm",
    role: "client",
    path: "/app/confirm?token=e2econfirm&summary=Detener%20el%20pond&expires_at=FUTURE",
    opener: null,
    dialog: /Tu agente propuso una acción/,
    focus: "app",
    widths: [375, 768, 1440],
  },
  {
    id: "sheet",
    role: "client",
    path: "/app",
    opener: "Abrir menú",
    dialog: /^Navegación$/,
    focus: "opener",
    widths: [375],
  },
  {
    id: "sheet-absent",
    role: "client",
    path: "/app",
    opener: null,
    dialog: null,
    focus: "app",
    widths: [768, 1440],
  },
];

const specDir = path.dirname(fileURLToPath(import.meta.url));
const artifactDir = path.resolve(specDir, "../artifacts");
const evidenceDir = "/opt/cursor/artifacts/dialog-viewport";

function casePath(item: DialogCase): string {
  if (!item.path.includes("FUTURE")) {
    return item.path;
  }
  const expiresAt = new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString();
  return item.path.replace("FUTURE", encodeURIComponent(expiresAt));
}

function viewportFor(width: number) {
  const found = VIEWPORTS.find((item) => item.width === width);
  if (!found) {
    throw new Error(`missing viewport ${width}`);
  }
  return found;
}

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

async function saveOpenDialogShot(page: Page, stem: string) {
  fs.mkdirSync(artifactDir, { recursive: true });
  fs.mkdirSync(evidenceDir, { recursive: true });
  const buffer = await page.screenshot();
  fs.writeFileSync(path.join(artifactDir, `${stem}.png`), buffer);
  fs.writeFileSync(path.join(evidenceDir, `${stem}.png`), buffer);
}

/** Page behind the translucent veil shares viewport cells with wrapped dialog
 *  text, so axe marks color-contrast incomplete (elmPartiallyObscuring) even
 *  when the panel is opaque bone-raised. Keep real violations; ignore only that
 *  obscured-page incomplete (ship review finding 3 on #160). */
function isObscuredPageContrastIncomplete(
  incomplete: Awaited<ReturnType<AxeBuilder["analyze"]>>["incomplete"][number],
): boolean {
  if (incomplete.id !== "color-contrast") {
    return false;
  }
  return incomplete.nodes.every((node) =>
    node.any.every(
      (check) =>
        check.id === "color-contrast" &&
        check.data !== null &&
        typeof check.data === "object" &&
        "messageKey" in check.data &&
        check.data.messageKey === "elmPartiallyObscuring",
    ),
  );
}

function contrastFailure(results: Awaited<ReturnType<AxeBuilder["analyze"]>>): string {
  const lines: string[] = [];
  for (const violation of results.violations) {
    const sample = violation.nodes[0];
    lines.push(
      `violation ${violation.id} nodes=${violation.nodes.length} ${sample?.html ?? ""} ${sample?.failureSummary ?? ""}`,
    );
  }
  for (const incomplete of results.incomplete) {
    if (incomplete.id === "color-contrast" && !isObscuredPageContrastIncomplete(incomplete)) {
      const sample = incomplete.nodes[0];
      lines.push(
        `incomplete color-contrast nodes=${incomplete.nodes.length} ${sample?.html ?? ""}`,
      );
    }
  }
  const passed = results.passes.some((rule) => rule.id === "color-contrast");
  if (!passed) {
    lines.push("color-contrast missing from passes");
  }
  return lines.join("\n");
}

for (const item of CASES) {
  for (const width of item.widths) {
    test(`${item.id} @ ${width}`, async ({ page }) => {
      const viewport = viewportFor(width);
      await installApi(page);
      await login(page, item.role);
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await goto(page, casePath(item));

      if (item.id === "sheet-absent") {
        await expect(page.getByRole("button", { name: "Abrir menú" })).toHaveCount(0);
        await expect(page.getByRole("dialog", { name: "Navegación" })).toHaveCount(0);
        return;
      }

      const opener = item.opener
        ? page.getByRole("button", { name: item.opener, exact: true })
        : null;
      if (opener) {
        await expect(opener).toHaveCount(1);
        await opener.click();
      }

      const dialog = page.getByRole("dialog", { name: item.dialog ?? /.^/ });
      await expect(dialog).toBeVisible();

      if (item.id === "restore" || item.id === "checkout") {
        await saveOpenDialogShot(page, `${item.id}-${width}`);
      }

      const axe = await new AxeBuilder({ page }).include('[role="dialog"]').analyze();
      const detail = contrastFailure(axe);
      expect(axe.violations, detail).toEqual([]);
      expect(
        axe.incomplete.filter(
          (rule) => rule.id === "color-contrast" && !isObscuredPageContrastIncomplete(rule),
        ),
        detail,
      ).toEqual([]);
      expect(
        axe.passes.some((rule) => rule.id === "color-contrast"),
        detail,
      ).toBe(true);

      await page.keyboard.press("Escape");

      if (item.focus === "opener") {
        if (!opener) {
          throw new Error(`${item.id} has no opener`);
        }
        await expect(dialog).toHaveCount(0);
        await expect(opener).toBeFocused();
      } else {
        await expect(page).toHaveURL(/\/app$/);
        await expect(page.getByRole("dialog")).toHaveCount(0);
        const connected = await page.evaluate(() => {
          const active = document.activeElement;
          return Boolean(active && active.isConnected && document.body.contains(active));
        });
        expect(connected).toBe(true);
      }
    });
  }
}
