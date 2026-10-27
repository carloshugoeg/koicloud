import { useEffect, useRef, type RefObject } from "react";
import { useState } from "react";
import { ApiError, problemToMessage } from "@/lib/errors";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

type DeleteAccountDialogProps = {
  email: string;
  pondsCount: number;
  pending: boolean;
  error: unknown;
  onCancel: () => void;
  onConfirm: (confirmEmail: string) => void;
  returnFocusRef: RefObject<HTMLElement | null>;
};

function FieldError({ error }: { error: unknown }) {
  if (!error) return null;
  const code = error instanceof ApiError ? error.problem?.code : undefined;
  return (
    <div
      role="alert"
      className="rounded-sm border border-danger border-l-4 bg-bone-raised px-3 py-2 text-sm text-danger"
    >
      <p className="font-medium">{problemToMessage(error)}</p>
      {code ? <p className="mt-1 font-mono text-xs text-ink-muted">{code}</p> : null}
    </div>
  );
}

export function DeleteAccountDialog({
  email,
  pondsCount,
  pending,
  error,
  onCancel,
  onConfirm,
  returnFocusRef,
}: DeleteAccountDialogProps) {
  const [confirmEmail, setConfirmEmail] = useState("");
  const matches = confirmEmail.trim().toLowerCase() === email.toLowerCase();
  const dialogRef = useRef<HTMLDivElement>(null);
  const cancelButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }

    cancelButtonRef.current?.focus();
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
          onCancel();
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
  }, [onCancel, pending, returnFocusRef]);

  return (
    <div
      className="dialog-veil fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4"
      data-testid="delete-me-veil"
    >
      <button
        type="button"
        className="absolute inset-0 border-0 bg-transparent"
        aria-label="Cerrar fondo del diálogo"
        tabIndex={-1}
        onClick={onCancel}
        disabled={pending}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-account-title"
        className="relative w-full max-w-md rounded-md border border-line bg-bone-raised shadow-dialog"
        data-testid="delete-me-dialog"
      >
        <div className="h-1 bg-danger" />
        <div className="space-y-4 p-5">
          <h3 id="delete-account-title" className="font-display text-2xl text-ink">
            Eliminar tu cuenta
          </h3>
          <div className="rounded-sm border border-danger/40 bg-koi-soft px-3 py-2 text-sm text-ink">
            Esto elimina <strong className="tabular-nums">{pondsCount}</strong> pond
            {pondsCount === 1 ? "" : "s"}, sus respaldos y tu historial. No se puede deshacer.
          </div>
          <label className="block text-xs font-medium text-ink-muted" htmlFor="delete-confirm-email">
            Escribe tu correo para confirmar
            <input
              id="delete-confirm-email"
              data-testid="delete-confirm-email"
              className="mt-1 block h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink focus:shadow-focus"
              value={confirmEmail}
              onChange={(event) => setConfirmEmail(event.target.value)}
              autoComplete="off"
            />
            <span className="mt-1 block font-mono text-[11px] text-ink-muted">
              Esperado: {email}
            </span>
          </label>
          <FieldError error={error} />
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
          <button
            ref={cancelButtonRef}
            type="button"
            className="h-9 px-3 text-sm text-ink focus-visible:shadow-focus"
            onClick={onCancel}
            disabled={pending}
          >
            Cancelar
          </button>
          <button
            type="button"
            data-testid="delete-me-submit"
            className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised focus-visible:shadow-focus disabled:opacity-40"
            disabled={!matches || pending}
            onClick={() => onConfirm(confirmEmail.trim())}
          >
            {pending ? "Eliminando…" : "Eliminar cuenta"}
          </button>
        </div>
      </div>
    </div>
  );
}

export { FieldError };
