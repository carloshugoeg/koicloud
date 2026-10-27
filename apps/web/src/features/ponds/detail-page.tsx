import { Link, useParams } from "react-router-dom";
import {
  pondIsTransient,
  useGetConnection,
  useGetPond,
  useRetryFailedJobMutation,
  useTriggerBackupMutation,
} from "@/api/hooks/ponds";
import { ConnectionCard } from "@/features/ponds/connection-card";
import { pondStateMeta } from "@/features/ponds/pond-state";
import { ApiError, problemToMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";

export function PondDetailPage() {
  const { pondId = "" } = useParams();
  const pondQuery = useGetPond(pondId || undefined);
  const connectionQuery = useGetConnection(pondId || undefined);
  const backupMutation = useTriggerBackupMutation(pondId);
  const retryMutation = useRetryFailedJobMutation(pondId);

  if (pondQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="pond-detail-loading">
        <div className="h-10 w-64 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-56 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (pondQuery.isError) {
    const code =
      pondQuery.error instanceof ApiError ? pondQuery.error.problem?.code : undefined;
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="pond-detail-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(pondQuery.error)}</p>
          {code ? <p className="mt-1 font-mono text-xs text-ink-faint">{code}</p> : null}
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void pondQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const pond = pondQuery.data;
  if (!pond) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="pond-detail-empty">
        <h2 className="font-display text-2xl text-ink">Sin datos del pond</h2>
        <p className="mt-2 text-sm text-ink-muted">Volvé al listado e intentá de nuevo.</p>
        <Link
          to="/app/ponds"
          className="mt-5 inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
        >
          Ver ponds
        </Link>
      </div>
    );
  }

  const meta = pondStateMeta(pond.observed_state);
  const inProgress = pondIsTransient(pond.observed_state);
  const failed = pond.observed_state === "failed";

  async function handleBackupNow() {
    try {
      await backupMutation.mutateAsync();
      toast({ tone: "ok", message: "Respaldo encolado" });
    } catch (error) {
      toast({ tone: "danger", message: problemToMessage(error) });
    }
  }

  async function handleRetry() {
    try {
      await retryMutation.mutateAsync();
      toast({ tone: "ok", message: "Reintento encolado" });
    } catch (error) {
      toast({ tone: "danger", message: problemToMessage(error) });
    }
  }

  return (
    <div className="space-y-5" data-testid="pond-detail">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-3xl text-ink">{pond.name}</h2>
            <span
              className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${meta.badgeClass}`}
              data-testid="pond-status-badge"
            >
              <span aria-hidden>{meta.glyph}</span>
              {meta.label}
            </span>
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            PostgreSQL {pond.engine_version} · plan {pond.plan_id} · nodo {pond.node_id}
          </p>
          <nav className="mt-3 flex flex-wrap gap-3 text-sm">
            <span className="font-medium text-ink">Resumen</span>
            <Link className="text-turquoise-700" to={`/app/ponds/${pond.id}/backups`}>
              Respaldos
            </Link>
            <Link className="text-turquoise-700" to={`/app/ponds/${pond.id}/console`}>
              Consola
            </Link>
          </nav>
        </div>
        <div className="flex flex-wrap gap-2">
          {pond.observed_state === "running" ? (
            <button
              type="button"
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint"
              data-testid="backup-now"
              disabled={backupMutation.isPending}
              onClick={() => void handleBackupNow()}
            >
              {backupMutation.isPending ? "Respaldando…" : "Respaldar ahora"}
            </button>
          ) : null}
          {pond.observed_state === "failed" ? (
            <button
              type="button"
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint"
              data-testid="retry-failed"
              disabled={retryMutation.isPending}
              onClick={() => void handleRetry()}
            >
              {retryMutation.isPending ? "Reintentando…" : "Reintentar"}
            </button>
          ) : null}
        </div>
      </div>

      {inProgress ? (
        <section
          className="flex flex-wrap items-center gap-3 rounded-md border border-line bg-bone-raised p-4"
          data-testid="pond-in-progress"
        >
          <span
            className="pond-water-strip relative inline-flex h-16 w-48 shrink-0 items-center justify-center overflow-hidden"
            aria-hidden
          >
            <i className="koi" />
          </span>
          <div>
            <p className="text-sm font-medium text-ink">{meta.label}</p>
            <p className="mt-1 text-sm text-ink-muted">
              Suele tomar unos 40 segundos. Esta vista se actualiza sola hasta el estado final.
            </p>
          </div>
        </section>
      ) : null}

      {failed ? (
        <section
          className="rounded-md border border-danger bg-bone-raised p-4"
          data-testid="pond-failed"
        >
          <div className="border-l-[3px] border-danger pl-3">
            <p className="text-sm font-medium text-danger">
              <span aria-hidden>{meta.glyph} </span>
              {meta.label}
            </p>
            <p className="mt-1 text-sm text-ink">
              {pond.last_error
                ? `Último error: ${pond.last_error}`
                : "El nodo no pudo completar la operación. Revisá el listado o reintentá más tarde."}
            </p>
          </div>
        </section>
      ) : null}

      <ConnectionCard
        connection={connectionQuery.data}
        pending={connectionQuery.isPending}
        error={connectionQuery.error}
        isError={connectionQuery.isError}
      />
    </div>
  );
}
