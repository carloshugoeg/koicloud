import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useGetPond,
  useListBackups,
  useRestoreBackupMutation,
  type Backup,
} from "@/api/hooks/ponds";
import { problemToMessage } from "@/lib/errors";
import { pondStateMeta } from "@/features/ponds/pond-state";

function formatBytes(size: number): string {
  if (size <= 0) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function shortSha(sha: string): string {
  if (sha.length < 12) return sha;
  return `${sha.slice(0, 4)}…${sha.slice(-4)}`;
}

function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

function kindChipClass(kind: Backup["kind"]): string {
  if (kind === "pre_delete") return "bg-koi-soft text-ink";
  return "bg-bone-sunk text-ink";
}

export function BackupsPage() {
  const { pondId = "" } = useParams();
  const pondQuery = useGetPond(pondId || undefined);
  const backupsQuery = useListBackups(pondId || undefined);
  const restoreMutation = useRestoreBackupMutation(pondId);
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
  const nameMatches = Boolean(pond && confirmName === pond.name);

  async function handleRestore() {
    if (!selected || !pond || !nameMatches) return;
    try {
      const result = await restoreMutation.mutateAsync(selected.id);
      setQueuedJobId(result.job.id);
      setSelected(null);
      setConfirmName("");
    } catch {
      // surfaced via restoreMutation.error
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
              El <span className="font-mono">pre_delete</span> se crea siempre antes de eliminar un pond
            </span>
          </div>
        </div>
      )}

      {selected && pond ? (
        <div
          className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
          data-testid="restore-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="restore-title"
        >
          <div className="w-full max-w-lg rounded-md border border-line-control bg-bone-raised shadow-dialog">
            <div className="h-1 bg-danger" />
            <div className="space-y-4 p-5">
              <h3 id="restore-title" className="font-display text-2xl text-ink">
                Restaurar respaldo del {formatWhen(selected.created_at)}
              </h3>
              <div className="rounded-sm border border-danger bg-danger-soft px-3 py-2 text-sm text-ink">
                Esto borra los datos actuales de{" "}
                <span className="font-mono font-medium">{pond.name}</span> y los reemplaza por el
                respaldo. No se puede deshacer.
              </div>
              <label className="block space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
                  Escribe el nombre del pond para confirmar
                </span>
                <input
                  className="h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink"
                  value={confirmName}
                  onChange={(e) => setConfirmName(e.target.value)}
                  autoComplete="off"
                  data-testid="restore-confirm-input"
                />
                <span className="block text-xs text-ink-muted">
                  Esperado: <span className="font-mono font-medium text-ink">{pond.name}</span>
                </span>
              </label>
            </div>
            <div className="flex items-center gap-3 border-t border-line px-5 py-4">
              <button
                type="button"
                className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
                onClick={() => {
                  setSelected(null);
                  setConfirmName("");
                }}
              >
                Cancelar
              </button>
              <span className="grow" />
              <button
                type="button"
                className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone-raised disabled:bg-bone-sunk disabled:text-ink-faint"
                disabled={!nameMatches || restoreMutation.isPending}
                onClick={() => void handleRestore()}
                data-testid="restore-confirm-button"
              >
                {restoreMutation.isPending ? "Restaurando…" : "Restaurar pond"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
