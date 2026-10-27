type BackupConfirmDialogProps = {
  pondName: string;
  pending: boolean;
  errorMessage?: string | null;
  onCancel: () => void;
  onConfirm: () => void;
};

/** Local web confirm for on-demand backup (not propose→confirm tokens — those are W2-16 / CLI/MCP). */
export function BackupConfirmDialog({
  pondName,
  pending,
  errorMessage,
  onCancel,
  onConfirm,
}: BackupConfirmDialogProps) {
  return (
    <div
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="backup-confirm-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="backup-confirm-title"
    >
      <div className="w-full max-w-lg rounded-md border border-line-control bg-bone-raised shadow-dialog">
        <div className="h-1 bg-marigold" />
        <div className="space-y-4 p-5">
          <h3 id="backup-confirm-title" className="font-display text-2xl text-ink">
            Respaldar ahora
          </h3>
          <p className="text-sm text-ink">
            Se encola un respaldo <span className="font-mono">on_demand</span> de{" "}
            <span className="font-mono font-medium">{pondName}</span>. El pond sigue en línea.
          </p>
          {errorMessage ? (
            <p className="text-sm text-danger" data-testid="backup-confirm-error">
              {errorMessage}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-3 border-t border-line px-5 py-4">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
            onClick={onCancel}
            disabled={pending}
          >
            Cancelar
          </button>
          <span className="grow" />
          <button
            type="button"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:bg-bone-sunk disabled:text-ink-muted"
            disabled={pending}
            onClick={onConfirm}
            data-testid="backup-confirm-button"
          >
            {pending ? "Respaldando…" : "Respaldar ahora"}
          </button>
        </div>
      </div>
    </div>
  );
}
