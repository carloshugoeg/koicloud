import { ApiError, problemToMessage } from "@/lib/errors";
import { useStartPondMutation, useStopPondMutation, type Pond } from "@/api/hooks/ponds";
import { pondLifecycleInFlight } from "@/features/ponds/pond-state";

type Props = {
  pond: Pond;
};

export function PondLifecycleActions({ pond }: Props) {
  const stopMutation = useStopPondMutation(pond.id);
  const startMutation = useStartPondMutation(pond.id);
  const inFlight = pondLifecycleInFlight(pond);
  const busy = inFlight || stopMutation.isPending || startMutation.isPending;
  const canStop = pond.observed_state === "running" && pond.desired_state === "running" && !busy;
  const canStart = pond.observed_state === "stopped" && pond.desired_state === "stopped" && !busy;
  const error = stopMutation.error ?? startMutation.error;

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="pond-lifecycle-actions">
      <button
        type="button"
        className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink disabled:text-ink-faint"
        disabled={!canStop}
        onClick={() => stopMutation.mutate()}
        data-testid="pond-stop"
      >
        {stopMutation.isPending || (inFlight && pond.desired_state === "stopped")
          ? "Deteniendo…"
          : "Detener"}
      </button>
      <button
        type="button"
        className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink disabled:text-ink-faint"
        disabled={!canStart}
        onClick={() => startMutation.mutate()}
        data-testid="pond-start"
      >
        {startMutation.isPending || (inFlight && pond.desired_state === "running")
          ? "Iniciando…"
          : "Iniciar"}
      </button>
      {error ? (
        <p className="w-full text-sm text-danger" data-testid="pond-lifecycle-error">
          {problemToMessage(error)}
          {error instanceof ApiError && error.problem?.code ? (
            <span className="ml-2 font-mono text-xs text-ink-faint">{error.problem.code}</span>
          ) : null}
        </p>
      ) : null}
    </div>
  );
}
