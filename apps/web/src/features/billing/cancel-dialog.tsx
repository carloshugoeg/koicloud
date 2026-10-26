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
      className="dialog-veil fixed inset-0 z-40 flex items-center justify-center p-4"
      data-testid="cancel-subscription-veil"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="cancel-subscription-title"
        className="w-full max-w-md overflow-hidden rounded-md border border-line bg-bone-raised shadow-dialog"
        data-testid="cancel-subscription-dialog"
        onKeyDown={(event) => {
          if (event.key === "Escape" && !pending) {
            onDismiss();
            return;
          }
          if (event.key !== "Tab") {
            return;
          }
          const focusable = event.currentTarget.querySelectorAll<HTMLElement>(
            "button:not([disabled]), a[href], input:not([disabled])",
          );
          if (focusable.length === 0) {
            return;
          }
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }}
      >
        <div className="h-2 bg-marigold" />
        <div className="space-y-3 p-5">
          <h2 id="cancel-subscription-title" className="font-display text-2xl text-ink">
            Cancelar al corte
          </h2>
          <p className="text-sm text-ink">
            El plan {planLabel} sigue activo hasta el corte del período. Después de esa hora deja de renovarse.
          </p>
          <p className="font-mono text-sm tabular-nums text-ink" data-testid="cancel-period-end">
            {periodEndLabel}
          </p>
          {error ? (
            <p className="text-sm text-danger" role="alert">
              {problemToMessage(error)}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-3 text-sm font-medium text-ink focus-visible:shadow-focus"
            onClick={onDismiss}
            disabled={pending}
            autoFocus
          >
            Cancelar
          </button>
          <button
            type="button"
            className="inline-flex h-9 items-center justify-center gap-2 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus-visible:shadow-focus disabled:cursor-not-allowed"
            onClick={onConfirm}
            disabled={pending}
          >
            {pending ? (
              <>
                <span
                  className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-bone-raised border-t-transparent"
                  aria-hidden
                />
                Cancelando…
              </>
            ) : (
              "Confirmar cancelación al corte"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
