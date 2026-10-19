import type { AdminUser } from "@/api/hooks/admin";
import { problemToMessage } from "@/lib/errors";

type SuspendDialogProps = {
  user: AdminUser;
  confirmEmail: string;
  motivo: string;
  pending: boolean;
  error: unknown;
  onConfirmEmailChange: (value: string) => void;
  onMotivoChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
};

export function SuspendDialog({
  user,
  confirmEmail,
  motivo,
  pending,
  error,
  onConfirmEmailChange,
  onMotivoChange,
  onCancel,
  onSubmit,
}: SuspendDialogProps) {
  const emailMatches = confirmEmail.trim().toLowerCase() === user.email.toLowerCase();

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4" data-testid="suspend-dialog">
      <div className="w-full max-w-md rounded-md border border-line bg-bone-raised shadow-lg">
        <div className="h-1 bg-danger" />
        <div className="space-y-4 p-5">
          <h3 className="font-display text-2xl text-ink">Suspender a {user.full_name}</h3>
          <div className="rounded-sm border border-danger/40 bg-danger-soft px-3 py-2 text-sm text-ink">
            La cuenta no podrá iniciar sesión. Sus ponds siguen corriendo y no se borra ningún dato.
          </div>
          <label className="block text-xs text-ink-muted">
            Escribe el correo de la cuenta para confirmar
            <input
              className="mt-1 block h-10 w-full rounded-sm border border-line-control bg-bone px-3 font-mono text-sm"
              value={confirmEmail}
              onChange={(event) => onConfirmEmailChange(event.target.value)}
              data-testid="suspend-confirm-email"
            />
            <span className="mt-1 block font-mono text-[11px]">Esperado: {user.email}</span>
          </label>
          <label className="block text-xs text-ink-muted">
            Motivo
            <input
              className="mt-1 block h-10 w-full rounded-sm border border-line-control bg-bone px-3 text-sm"
              value={motivo}
              onChange={(event) => onMotivoChange(event.target.value)}
              data-testid="suspend-motivo"
            />
          </label>
          {error ? (
            <p className="text-sm text-danger" data-testid="suspend-error">
              {problemToMessage(error)}
            </p>
          ) : null}
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
          <button type="button" className="h-9 px-3 text-sm" onClick={onCancel}>
            Cancelar
          </button>
          <button
            type="button"
            className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone disabled:opacity-40"
            data-testid="suspend-submit"
            disabled={!emailMatches || !motivo.trim() || pending}
            onClick={onSubmit}
          >
            Suspender cuenta
          </button>
        </div>
      </div>
    </div>
  );
}
