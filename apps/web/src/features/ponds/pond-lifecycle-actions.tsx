import { useRef, useState } from "react";
import { ModalDialog } from "@/components/modal-dialog";
import { ApiError, problemToMessage } from "@/lib/errors";
import {
  useRetryFailedJobMutation,
  useStartPondMutation,
  useStopPondMutation,
  type Pond,
} from "@/api/hooks/ponds";
import { pondLifecycleInFlight } from "@/features/ponds/pond-state";

type Props = {
  pond: Pond;
};

export function PondLifecycleActions({ pond }: Props) {
  const stopMutation = useStopPondMutation(pond.id);
  const startMutation = useStartPondMutation(pond.id);
  const retryMutation = useRetryFailedJobMutation(pond.id);
  const [stopOpen, setStopOpen] = useState(false);
  const stopButtonRef = useRef<HTMLButtonElement>(null);
  const inFlight = pondLifecycleInFlight(pond);
  const busy =
    inFlight || stopMutation.isPending || startMutation.isPending || retryMutation.isPending;
  const failed = pond.observed_state === "failed";
  const canStop = pond.observed_state === "running" && pond.desired_state === "running" && !busy;
  // Contract: POST /start needs observed=stopped. Failed jobs set observed=failed, so
  // chart error→starting via /start is unreachable; recovery is POST /retry.
  const canStart = pond.observed_state === "stopped" && pond.desired_state === "stopped" && !busy;
  const canRetry = failed && !busy;
  const error = stopMutation.error ?? startMutation.error ?? retryMutation.error;

  function confirmStop() {
    stopMutation.mutate(undefined, {
      onSuccess: () => setStopOpen(false),
    });
  }

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="pond-lifecycle-actions">
      <button
        type="button"
        ref={stopButtonRef}
        className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised focus-visible:outline-none focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
        disabled={!canStop}
        onClick={() => setStopOpen(true)}
        data-testid="pond-stop"
      >
        {stopMutation.isPending || (inFlight && pond.desired_state === "stopped")
          ? "Deteniendo…"
          : "Detener"}
      </button>
      <button
        type="button"
        className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:outline-none focus-visible:shadow-focus disabled:text-ink-faint"
        disabled={!canStart}
        onClick={() => startMutation.mutate()}
        data-testid="pond-start"
      >
        {startMutation.isPending || (inFlight && pond.desired_state === "running")
          ? "Iniciando…"
          : "Iniciar"}
      </button>
      {failed ? (
        <button
          type="button"
          className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus-visible:outline-none focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
          disabled={!canRetry}
          onClick={() => retryMutation.mutate()}
          data-testid="pond-retry"
        >
          {retryMutation.isPending ? "Reintentando…" : "Reintentar"}
        </button>
      ) : null}
      {error && !stopOpen ? (
        <p className="w-full text-sm text-danger" data-testid="pond-lifecycle-error">
          {problemToMessage(error)}
          {error instanceof ApiError && error.problem?.code ? (
            <span className="ml-2 font-mono text-xs text-ink-faint">{error.problem.code}</span>
          ) : null}
        </p>
      ) : null}
      {stopOpen ? (
        <ModalDialog
          titleId="stop-confirm-title"
          onClose={() => setStopOpen(false)}
          returnFocusRef={stopButtonRef}
          data-testid="stop-confirm-dialog"
          className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
          panelClassName="relative z-10 w-full max-w-lg overflow-hidden rounded-md border border-line-control bg-bone-raised shadow-dialog"
          closeLabel="Cerrar fondo del diálogo"
        >
          <div className="h-1 bg-danger" />
          <div className="space-y-4 p-5">
            <h3 id="stop-confirm-title" className="font-display text-2xl text-ink">
              Detener pond
            </h3>
            <p className="text-sm text-ink">
              {pond.name} deja de aceptar conexiones. Podés iniciarlo de nuevo cuando quieras.
            </p>
            {stopMutation.isError ? (
              <p className="text-sm text-danger" data-testid="stop-confirm-error">
                {problemToMessage(stopMutation.error)}
              </p>
            ) : null}
          </div>
          <div className="flex items-center gap-3 border-t border-line px-5 py-4">
            <button
              type="button"
              className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:outline-none focus-visible:shadow-focus"
              onClick={() => setStopOpen(false)}
              disabled={stopMutation.isPending}
            >
              Cancelar
            </button>
            <span className="grow" />
            <button
              type="button"
              className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised focus-visible:outline-none focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
              disabled={stopMutation.isPending}
              onClick={confirmStop}
              data-testid="stop-confirm-button"
            >
              {stopMutation.isPending ? "Deteniendo…" : "Detener"}
            </button>
          </div>
        </ModalDialog>
      ) : null}
    </div>
  );
}
