import type { AdminUser } from "@/api/hooks/admin";
import { problemToMessage } from "@/lib/errors";

type ReactivateDialogProps = {
  user: AdminUser;
  pending: boolean;
  error: unknown;
  onCancel: () => void;
  onSubmit: () => void;
};

export function ReactivateDialog({
  user,
  pending,
  error,
  onCancel,
  onSubmit,
}: ReactivateDialogProps) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4" data-testid="reactivate-dialog">
      <div className="w-full max-w-md rounded-md border border-line bg-bone-raised">
        <div className="space-y-4 p-5">
          <h3 className="font-display text-2xl text-ink">Reactivar a {user.full_name}</h3>
          <p className="text-sm text-ink-muted">
            La cuenta podrá iniciar sesión de nuevo. Confirmá para continuar.
          </p>
          {error ? <p className="text-sm text-danger">{problemToMessage(error)}</p> : null}
        </div>
        <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
          <button type="button" className="h-9 px-3 text-sm" onClick={onCancel}>
            Cancelar
          </button>
          <button
            type="button"
            className="h-9 rounded-sm border border-turquoise-700 bg-turquoise-100 px-4 text-sm font-medium text-turquoise-900 disabled:opacity-40"
            data-testid="reactivate-submit"
            disabled={pending}
            onClick={onSubmit}
          >
            Reactivar cuenta
          </button>
        </div>
      </div>
    </div>
  );
}
