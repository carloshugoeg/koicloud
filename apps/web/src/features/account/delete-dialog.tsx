import { useState } from "react";
import { ApiError, problemToMessage } from "@/lib/errors";

type DeleteAccountDialogProps = {
  email: string;
  pondsCount: number;
  pending: boolean;
  error: unknown;
  onCancel: () => void;
  onConfirm: (confirmEmail: string) => void;
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
      {code ? <p className="mt-1 font-mono text-xs text-ink-faint">{code}</p> : null}
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
}: DeleteAccountDialogProps) {
  const [confirmEmail, setConfirmEmail] = useState("");
  const matches = confirmEmail.trim().toLowerCase() === email.toLowerCase();

  return (
    <div
      className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4"
      data-testid="delete-me-dialog"
    >
      <div className="w-full max-w-md rounded-md border border-line bg-bone-raised shadow-dialog">
        <div className="h-1 bg-danger" />
        <div className="space-y-4 p-5">
          <h3 className="font-display text-2xl text-ink">Eliminar tu cuenta</h3>
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
          <button type="button" className="h-9 px-3 text-sm text-ink" onClick={onCancel}>
            Cancelar
          </button>
          <button
            type="button"
            data-testid="delete-me-submit"
            className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised disabled:opacity-40"
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
