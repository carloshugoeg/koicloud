import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  pondNeedsPolling,
  useDeletePondMutation,
  useGetConnection,
  useGetPond,
  useTriggerBackupMutation,
} from "@/api/hooks/ponds";
import { BackupConfirmDialog } from "@/features/ponds/backup-confirm-dialog";
import { ConnectionCard } from "@/features/ponds/connection-card";
import { DeletePondDialog } from "@/features/ponds/delete-pond-dialog";
import { PondLifecycleActions } from "@/features/ponds/pond-lifecycle-actions";
import { PondRiskZone } from "@/features/ponds/pond-risk-zone";
import { pondDisplayMeta, pondLifecycleInFlight } from "@/features/ponds/pond-state";
import { ApiError, problemToMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";

export function PondDetailPage() {
  const { pondId = "" } = useParams();
  const navigate = useNavigate();
  const pondQuery = useGetPond(pondId || undefined);
  const connectionQuery = useGetConnection(pondId || undefined);
  const backupMutation = useTriggerBackupMutation(pondId);
  const deleteMutation = useDeletePondMutation(pondId);
  const [backupOpen, setBackupOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmName, setConfirmName] = useState("");

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

  const meta = pondDisplayMeta(pond);
  const inProgress = pondNeedsPolling(pond) || pondLifecycleInFlight(pond);
  const failed = pond.observed_state === "failed";
  const actionsDisabled = inProgress || pond.observed_state === "deleted";

  async function handleBackupConfirm() {
    try {
      await backupMutation.mutateAsync();
      setBackupOpen(false);
      toast({ tone: "ok", message: "Respaldo encolado" });
    } catch (error) {
      setBackupOpen(false);
      toast({ tone: "danger", message: problemToMessage(error) });
    }
  }

  async function handleDelete() {
    if (confirmName !== pond.name) return;
    try {
      await deleteMutation.mutateAsync();
      setDeleteOpen(false);
      setConfirmName("");
      void navigate("/app/ponds");
    } catch {
      // surfaced via deleteMutation.error
    }
  }

  function openDelete() {
    setConfirmName("");
    setDeleteOpen(true);
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
        <div className="flex flex-wrap items-center gap-2">
          {pond.observed_state === "running" ? (
            <button
              type="button"
              className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint"
              data-testid="backup-now"
              disabled={actionsDisabled || backupMutation.isPending}
              onClick={() => setBackupOpen(true)}
            >
              {backupMutation.isPending ? "Respaldando…" : "Respaldar ahora"}
            </button>
          ) : null}
          <button
            type="button"
            className="h-9 rounded-sm border border-danger bg-bone-raised px-4 text-sm font-medium text-danger disabled:border-line-control disabled:text-ink-faint"
            data-testid="open-delete-pond"
            disabled={actionsDisabled || deleteMutation.isPending}
            onClick={openDelete}
          >
            Eliminar…
          </button>
          <PondLifecycleActions pond={pond} />
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

      <PondRiskZone
        disabled={actionsDisabled || deleteMutation.isPending}
        onDelete={openDelete}
      />

      {backupOpen ? (
        <BackupConfirmDialog
          pondName={pond.name}
          pending={backupMutation.isPending}
          errorMessage={
            backupMutation.isError ? problemToMessage(backupMutation.error) : null
          }
          onCancel={() => setBackupOpen(false)}
          onConfirm={() => void handleBackupConfirm()}
        />
      ) : null}

      {deleteOpen ? (
        <DeletePondDialog
          pondName={pond.name}
          confirmName={confirmName}
          pending={deleteMutation.isPending}
          error={deleteMutation.error}
          onConfirmNameChange={setConfirmName}
          onCancel={() => {
            setDeleteOpen(false);
            setConfirmName("");
          }}
          onSubmit={() => void handleDelete()}
        />
      ) : null}
    </div>
  );
}
