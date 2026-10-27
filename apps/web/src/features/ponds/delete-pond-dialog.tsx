import { problemToMessage } from "@/lib/errors";

type DeletePondDialogProps = {
  pondName: string;
  confirmName: string;
  pending: boolean;
  error: unknown;
  onConfirmNameChange: (value: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
};

export function DeletePondDialog({
  pondName,
  confirmName,
  pending,
  error,
  onConfirmNameChange,
  onCancel,
  onSubmit,
}: DeletePondDialogProps) {
  const nameMatches = confirmName === pondName;

  return (
    <div
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="delete-pond-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="delete-pond-title"
    >
      <div className="w-full max-w-lg rounded-md border border-line-control bg-bone-raised shadow-dialog">
        <div className="h-1 bg-danger" />
        <div className="space-y-4 p-5">
          <h3 id="delete-pond-title" className="font-display text-2xl text-ink">
            Eliminar pond
          </h3>
          <div className="rounded-sm border border-danger bg-danger-soft px-3 py-2 text-sm text-ink">
            Encolamos primero un respaldo <span className="font-mono">pre_delete</span> y luego el
            borrado del contenedor. Escribí el nombre exacto de{" "}
            <span className="font-mono font-medium">{pondName}</span> para continuar.
          </div>
          <label className="block space-y-1.5">
            <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
              Escribe el nombre del pond para confirmar
            </span>
            <input
              className="h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink"
              value={confirmName}
              onChange={(e) => onConfirmNameChange(e.target.value)}
              autoComplete="off"
              data-testid="delete-confirm-input"
            />
            <span className="block text-xs text-ink-muted">
              Esperado: <span className="font-mono font-medium text-ink">{pondName}</span>
            </span>
          </label>
          {error ? (
            <p className="text-sm text-danger" data-testid="delete-pond-error">
              {problemToMessage(error)}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-3 border-t border-line px-5 py-4">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
            onClick={onCancel}
          >
            Cancelar
          </button>
          <span className="grow" />
          <button
            type="button"
            className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised disabled:bg-bone-sunk disabled:text-ink-muted"
            disabled={!nameMatches || pending}
            onClick={onSubmit}
            data-testid="delete-confirm-button"
          >
            {pending ? "Eliminando…" : "Eliminar pond"}
          </button>
        </div>
      </div>
    </div>
  );
}
