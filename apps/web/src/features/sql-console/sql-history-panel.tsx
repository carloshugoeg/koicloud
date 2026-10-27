import { useSqlHistoryQuery } from "@/api/hooks/sql-console";
import { problemToMessage } from "@/lib/errors";

function formatStamp(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("es-GT", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

export function SqlHistoryPanel({ pondId }: { pondId: string }) {
  const historyQuery = useSqlHistoryQuery(pondId || undefined);

  return (
    <aside
      className="min-w-0 overflow-hidden rounded-md border border-line bg-bone-raised p-4"
      data-testid="sql-history"
    >
      <h3 className="font-display text-lg text-ink">Historial</h3>
      <p className="mt-1 text-xs text-ink-muted">Tus últimas consultas en este pond.</p>

      {historyQuery.isPending ? (
        <div className="mt-4 h-24 animate-pulse rounded-sm bg-bone-sunk" />
      ) : null}

      {historyQuery.isError ? (
        <p className="mt-4 text-sm text-ink">{problemToMessage(historyQuery.error)}</p>
      ) : null}

      {historyQuery.data ? (
        <ul className="mt-4 space-y-3">
          {historyQuery.data.events.length === 0 ? (
            <li className="text-sm text-ink-muted">Aún no hay consultas.</li>
          ) : (
            historyQuery.data.events.map((event) => (
              <li
                key={event.id}
                className="min-w-0 rounded-sm border border-line bg-paper px-3 py-2"
                data-testid="sql-history-item"
              >
                <p className="truncate font-mono text-xs text-ink" title={event.query_truncated}>
                  {event.query_truncated}
                </p>
                <p className="mt-1 flex flex-wrap gap-2 font-mono text-[11px] text-ink-muted">
                  <span>{formatStamp(event.executed_at)}</span>
                  <span>{event.mode}</span>
                  <span>{event.duration_ms} ms</span>
                  <span>{event.row_count} filas</span>
                </p>
              </li>
            ))
          )}
        </ul>
      ) : null}
    </aside>
  );
}
