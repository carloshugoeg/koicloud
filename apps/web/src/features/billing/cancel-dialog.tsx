import { useEffect, useRef, type RefObject } from "react";
import { problemToMessage } from "@/lib/errors";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

type CancelDialogProps = {
  planLabel: string;
  periodEndLabel: string;
  pending: boolean;
  error: unknown;
  onDismiss: () => void;
  onConfirm: () => void;
  returnFocusRef: RefObject<HTMLElement | null>;
};

export function CancelDialog({
  planLabel,
  periodEndLabel,
  pending,
  error,
  onDismiss,
  onConfirm,
  returnFocusRef,
}: CancelDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const dismissButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }

    dismissButtonRef.current?.focus();
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
        if (!pending) {
          onDismiss();
        }
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
  }, [onDismiss, pending, returnFocusRef]);

  return (
    <div
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="cancel-subscription-veil"
    >
      <button
        type="button"
        className="absolute inset-0 border-0 bg-transparent"
        aria-label="Cerrar fondo del diálogo"
        tabIndex={-1}
        onClick={onDismiss}
        disabled={pending}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-subscription-title"
        className="relative w-full max-w-lg overflow-hidden rounded-md border border-line-control bg-bone-raised shadow-dialog"
        data-testid="cancel-subscription-dialog"
      >
        <div className="h-2 bg-marigold" />
        <div className="space-y-3 p-5">
          <h2 id="cancel-subscription-title" className="font-display text-2xl text-ink">
            Cancelar al corte
          </h2>
          <p className="text-sm text-ink">
            El plan <span className="font-mono">{planLabel}</span> sigue activo hasta{" "}
            <span className="font-mono tabular-nums">{periodEndLabel}</span>. Después no se
            renueva.
          </p>
          {error ? (
            <p className="border-l-[3px] border-danger pl-3 text-sm text-ink" role="alert">
              {problemToMessage(error)}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap justify-end gap-3 border-t border-line px-5 py-4">
          <button
            ref={dismissButtonRef}
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:shadow-focus"
            onClick={onDismiss}
            disabled={pending}
          >
            Volver
          </button>
          <button
            type="button"
            className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-muted"
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? "Cancelando…" : "Cancelar al corte"}
          </button>
        </div>
      </div>
    </div>
  );
}
