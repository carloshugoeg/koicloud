import { problemToMessage } from "@/lib/errors";

type CancelDialogProps = {
  planLabel: string;
  periodEndLabel: string;
  pending: boolean;
  error: unknown;
  onDismiss: () => void;
  onConfirm: () => void;
};

export function CancelDialog({
  planLabel,
  periodEndLabel,
  pending,
  error,
  onDismiss,
  onConfirm,
}: CancelDialogProps) {
  return (
    <div
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      data-testid="cancel-subscription-veil"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-subscription-title"
        className="w-full max-w-lg overflow-hidden rounded-md border border-line-control bg-bone-raised shadow-dialog"
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
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:shadow-focus"
            onClick={onDismiss}
            disabled={pending}
          >
            Volver
          </button>
          <button
            type="button"
            className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
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
