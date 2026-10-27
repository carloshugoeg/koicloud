import type { Backup } from "@/api/hooks/ponds";

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

type BackupsTableProps = {
  backups: Backup[];
  onRestore: (backup: Backup) => void;
};

export function BackupsTable({ backups, onRestore }: BackupsTableProps) {
  return (
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
                    data-testid="open-restore"
                    onClick={() => onRestore(backup)}
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
  );
}
