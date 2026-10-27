import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useGetPond,
  useListBackups,
  useRestoreBackupMutation,
  useTriggerBackupMutation,
  type Backup,
} from "@/api/hooks/ponds";
import { problemToMessage } from "@/lib/errors";
import { BackupConfirmDialog } from "@/features/ponds/backup-confirm-dialog";
import { BackupsTable } from "@/features/ponds/backups-table";
import { RestoreDialog } from "@/features/ponds/restore-dialog";
import { pondStateMeta } from "@/features/ponds/pond-state";

export function BackupsPage() {
  const { pondId = "" } = useParams();
  const pondQuery = useGetPond(pondId || undefined);
  const backupsQuery = useListBackups(pondId || undefined);
  const restoreMutation = useRestoreBackupMutation(pondId);
  const backupMutation = useTriggerBackupMutation(pondId);
  const [selected, setSelected] = useState<Backup | null>(null);
  const [confirmName, setConfirmName] = useState("");
  const [backupOpen, setBackupOpen] = useState(false);
  const [queuedJobId, setQueuedJobId] = useState<string | null>(null);
  const [backupJobId, setBackupJobId] = useState<string | null>(null);

  if (pondQuery.isPending || backupsQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="backups-loading">
        <div className="h-10 w-64 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-48 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (pondQuery.isError || backupsQuery.isError) {
    const err = pondQuery.error ?? backupsQuery.error;
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="backups-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(err)}</p>
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => {
            void pondQuery.refetch();
            void backupsQuery.refetch();
          }}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const pond = pondQuery.data;
  const backups = backupsQuery.data ?? [];
  const meta = pond ? pondStateMeta(pond.observed_state) : null;

  async function handleRestore() {
    if (!selected || !pond || confirmName !== pond.name) return;
    try {
      const result = await restoreMutation.mutateAsync(selected.id);
      setQueuedJobId(result.job.id);
      setSelected(null);
      setConfirmName("");
    } catch {
      // surfaced via restoreMutation.error
    }
  }

  async function handleBackup() {
    try {
      const result = await backupMutation.mutateAsync();
      setBackupJobId(result.job.id);
      setBackupOpen(false);
    } catch {
      // surfaced via backupMutation.error
    }
  }

  return (
    <div className="space-y-5" data-testid="backups-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-3xl text-ink">{pond?.name ?? "Pond"}</h2>
            {meta ? (
              <span
                className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${meta.badgeClass}`}
              >
                <span aria-hidden>{meta.glyph}</span>
                {meta.label}
              </span>
            ) : null}
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            Respaldo diario a las 03:15. Retención según el plan activo.
          </p>
          <nav className="mt-3 flex flex-wrap gap-3 text-sm">
            <Link className="text-turquoise-700" to={`/app/ponds/${pondId}`}>
              Resumen
            </Link>
            <span className="font-medium text-ink">Respaldos</span>
          </nav>
        </div>
        <button
          type="button"
          className="h-8 rounded-sm border border-line-control bg-bone-raised px-3 text-sm font-medium text-ink disabled:text-ink-muted"
          disabled={!pond || backupMutation.isPending}
          onClick={() => setBackupOpen(true)}
          data-testid="trigger-backup"
        >
          Respaldar ahora
        </button>
      </div>

      {backupJobId ? (
        <div
          className="rounded-md border border-line bg-turquoise-100 px-4 py-3 text-sm text-turquoise-900"
          data-testid="backup-queued"
        >
          Respaldo encolado. Job <span className="font-mono">{backupJobId}</span> · estado{" "}
          <span className="font-mono">queued</span>.
        </div>
      ) : null}

      {queuedJobId ? (
        <div
          className="rounded-md border border-line bg-turquoise-100 px-4 py-3 text-sm text-turquoise-900"
          data-testid="restore-queued"
        >
          Restauración encolada. Job <span className="font-mono">{queuedJobId}</span> · estado{" "}
          <span className="font-mono">queued</span>.
        </div>
      ) : null}

      {restoreMutation.isError ? (
        <div className="rounded-md border border-line bg-bone-raised px-4 py-3 text-sm text-danger">
          {problemToMessage(restoreMutation.error)}
        </div>
      ) : null}

      {backups.length === 0 ? (
        <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="backups-empty">
          <h3 className="font-display text-2xl text-ink">Sin respaldos todavía</h3>
          <p className="mt-2 text-sm text-ink-muted">
            El scheduler diario y los respaldos bajo demanda aparecerán aquí.
          </p>
        </div>
      ) : (
        <BackupsTable
          backups={backups}
          onRestore={(backup) => {
            setSelected(backup);
            setConfirmName("");
          }}
        />
      )}

      {selected && pond ? (
        <RestoreDialog
          pondName={pond.name}
          backup={selected}
          confirmName={confirmName}
          pending={restoreMutation.isPending}
          onConfirmNameChange={setConfirmName}
          onCancel={() => {
            setSelected(null);
            setConfirmName("");
          }}
          onConfirm={() => void handleRestore()}
        />
      ) : null}

      {backupOpen && pond ? (
        <BackupConfirmDialog
          pondName={pond.name}
          pending={backupMutation.isPending}
          errorMessage={
            backupMutation.isError ? problemToMessage(backupMutation.error) : null
          }
          onCancel={() => setBackupOpen(false)}
          onConfirm={() => void handleBackup()}
        />
      ) : null}
    </div>
  );
}
