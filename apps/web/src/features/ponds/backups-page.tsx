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
import { pushToast } from "@/lib/toast";
import {
  formatBytes,
  formatWhen,
  kindChipClass,
  shortSha,
} from "@/features/ponds/backup-format";
import { pondStateMeta } from "@/features/ponds/pond-state";
import { RestoreDialog } from "@/features/ponds/restore-dialog";

export function BackupsPage() {
  const { pondId = "" } = useParams();
  const pondQuery = useGetPond(pondId || undefined);
  const backupsQuery = useListBackups(pondId || undefined);
  const restoreMutation = useRestoreBackupMutation(pondId);
  const backupNowMutation = useTriggerBackupMutation(pondId);
  const [selected, setSelected] = useState<Backup | null>(null);
  const [confirmName, setConfirmName] = useState("");
  const [queuedJobId, setQueuedJobId] = useState<string | null>(null);

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
    if (!selected || !pond) return;
    try {
      const result = await restoreMutation.mutateAsync(selected.id);
      setQueuedJobId(result.job.id);
      setSelected(null);
      setConfirmName("");
    } catch (error) {
      pushToast({
        title: "No se pudo restaurar",
        detail: problemToMessage(error),
        tone: "danger",
      });
    }
  }

  async function handleBackupNow() {
    try {
      const result = await backupNowMutation.mutateAsync();
      pushToast({
        title: "Respaldo encolado",
        detail: `Job ${result.job.id}`,
        tone: "ok",
      });
    } catch (error) {
      pushToast({
        title: "No se pudo respaldar",
        detail: problemToMessage(error),
        tone: "danger",
      });
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
          className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:bg-bone-sunk disabled:text-ink-faint"
          onClick={() => void handleBackupNow()}
          disabled={backupNowMutation.isPending || !pond}
          data-testid="backup-now"
        >
          {backupNowMutation.isPending ? "Encolando…" : "Respaldar ahora"}
        </button>
      </div>

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
        <div className="overflow-x-auto rounded-md border border-line">
          <table className="w-full min-w-[800px] border-collapse text-sm">
            <thead className="bg-bone-sunk text-left text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
              <tr>
                <th className="border-b border-line-control px-3 py-2">Creado</th>
                <th className="border-b border-line-control px-3 py-2">Tipo</th>
                <th className="border-b border-line-control px-3 py-2">Estado</th>
                <th className="border-b border-line-control px-3 py-2 text-right">Tamaño</th>
                <th className="border-b border-line-control px-3 py-2">sha256</th>
                <th className="border-b border-line-control px-3 py-2">Expira</th>
                <th className="border-b border-line-control px-3 py-2 text-right">Acción</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((backup) => (
                <tr key={backup.id} className="border-b border-line hover:bg-bone-raised">
                  <td className="px-3 py-2 font-mono text-xs">{formatWhen(backup.created_at)}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex rounded-sm px-2 py-0.5 text-xs font-medium ${kindChipClass(backup.kind)}`}
                      data-kind={backup.kind}
                    >
                      {backup.kind}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs">{backup.status}</td>
                  <td className="px-3 py-2 text-right tabular-nums">
                    {backup.status === "succeeded" ? formatBytes(backup.size_bytes) : "—"}
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-ink-muted">
                    {backup.status === "succeeded" ? shortSha(backup.sha256) : "—"}
                  </td>
                  <td className="px-3 py-2 text-ink-muted">—</td>
                  <td className="px-3 py-2 text-right">
                    {backup.status === "succeeded" ? (
                      <button
                        type="button"
                        className="text-sm font-medium text-turquoise-700 hover:text-turquoise-900"
                        onClick={() => {
                          setSelected(backup);
                          setConfirmName("");
                        }}
                      >
                        Restaurar…
                      </button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex justify-between border-t border-line bg-bone px-3 py-2 text-xs text-ink-muted">
            <span>{backups.length} respaldos</span>
            <span>
              El <span className="font-mono">pre_delete</span> se crea siempre antes de eliminar un
              pond
            </span>
          </div>
        </div>
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
    </div>
  );
}
