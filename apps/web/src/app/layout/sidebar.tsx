import { useEffect, useRef, type RefObject } from "react";
import { SidebarNav } from "@/app/layout/sidebar-nav";
import { CloseIcon } from "@/app/layout/nav-icons";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function Brand({ collapsed }: { collapsed: boolean }) {
  return (
    <div
      className={[
        "border-b border-line",
        collapsed ? "flex justify-center px-2 py-4" : "space-y-1 px-3 pb-4 pt-1",
      ].join(" ")}
    >
      <div className={["flex items-center gap-2", collapsed ? "justify-center" : ""].join(" ")}>
        <span className="koi-mark-32 shrink-0" aria-hidden />
        {collapsed ? (
          <span className="sr-only">KoiCloud</span>
        ) : (
          <p className="font-display text-2xl text-ink">KoiCloud</p>
        )}
      </div>
      {collapsed ? null : (
        <p className="text-sm text-ink-muted">Panel de control del estanque.</p>
      )}
    </div>
  );
}

/** Permanent sidebar: full ≥1024, icon rail 768–1023. Hidden below 768. */
export function SidebarRail({
  isAdmin,
  collapsed,
}: {
  isAdmin: boolean;
  collapsed: boolean;
}) {
  return (
    <aside
      data-testid="sidebar-rail"
      data-collapsed={collapsed ? "true" : "false"}
      className={[
        "flex flex-col overflow-y-auto border-r border-line bg-bone-sunk",
        collapsed
          ? "w-[var(--sidebar-w-collapsed)] px-2 py-4"
          : "w-[var(--sidebar-w)] px-3 py-5",
      ].join(" ")}
      style={{ minHeight: "100vh" }}
    >
      <Brand collapsed={collapsed} />
      <div className="mt-5 flex-1">
        <SidebarNav isAdmin={isAdmin} collapsed={collapsed} />
      </div>
    </aside>
  );
}

/** Sheet drawer for < 768 px — Escape, focus in/out, Tab containment (CA4). */
export function SidebarSheet({
  isAdmin,
  open,
  onClose,
  returnFocusRef,
}: {
  isAdmin: boolean;
  open: boolean;
  onClose: () => void;
  returnFocusRef: RefObject<HTMLElement | null>;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }

    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }

    closeButtonRef.current?.focus();
    const returnTarget = returnFocusRef.current;

    function focusables(): HTMLElement[] {
      if (!dialogRef.current) return [];
      return Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => !el.hasAttribute("disabled") && el.tabIndex !== -1,
      );
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const items = focusables();
      if (items.length === 0) {
        event.preventDefault();
        return;
      }

      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (active === first || !dialogRef.current?.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last || !dialogRef.current?.contains(active)) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      returnTarget?.focus();
    };
  }, [open, onClose, returnFocusRef]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50" data-testid="sidebar-sheet">
      <button
        type="button"
        className="dialog-veil absolute inset-0 border-0"
        aria-label="Cerrar fondo del menú"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Navegación"
        className="absolute inset-y-0 left-0 flex w-[min(100%,var(--sidebar-w))] flex-col overflow-y-auto border-r border-line bg-bone-sunk px-3 py-4 shadow-dialog"
      >
        <div className="mb-2 flex items-start justify-end">
          <button
            ref={closeButtonRef}
            type="button"
            className="rounded-sm border border-line-control bg-bone-raised p-2 text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
            aria-label="Cerrar menú"
            onClick={onClose}
          >
            <CloseIcon />
          </button>
        </div>
        <Brand collapsed={false} />
        <div className="mt-5">
          <SidebarNav isAdmin={isAdmin} collapsed={false} onNavigate={onClose} />
        </div>
      </div>
    </div>
  );
}
