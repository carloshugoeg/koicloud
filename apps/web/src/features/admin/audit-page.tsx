import { useMemo } from "react";
import { useAdminAuditQuery, type AuditEvent } from "@/api/hooks/admin";
import { MoreResultsNote } from "@/features/admin/more-results-note";
import { ApiError, problemToMessage } from "@/lib/errors";

function dayKey(iso: string) {
  return iso.slice(0, 10);
}

function formatStamp(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("es-GT", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);
}

function metadataLine(event: AuditEvent) {
  const bits = Object.entries(event.metadata).map(([key, value]) => `${key}=${String(value)}`);
  return bits.length > 0 ? bits.join(" · ") : "—";
}

export function AdminAuditPage() {
  const auditQuery = useAdminAuditQuery();

  const groups = useMemo(() => {
    const events = auditQuery.data?.events ?? [];
    const byDay = new Map<string, AuditEvent[]>();
    for (const event of events) {
      const key = dayKey(event.at);
      const bucket = byDay.get(key) ?? [];
      bucket.push(event);
      byDay.set(key, bucket);
    }
    return [...byDay.entries()];
  }, [auditQuery.data?.events]);

  if (auditQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="admin-audit-loading">
        <div className="h-10 w-56 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-64 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (auditQuery.isError) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="admin-audit-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(auditQuery.error)}</p>
          <p className="mt-1 font-mono text-xs text-ink-faint">
            {auditQuery.error instanceof ApiError ? auditQuery.error.problem?.code : "error"}
          </p>
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void auditQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const auditHaveMore = Boolean(auditQuery.data?.next_cursor);

  return (
    <div className="space-y-4" data-testid="admin-audit-page">
      <p className="text-sm text-ink-muted">Últimos eventos sensibles del sistema.</p>

      {groups.length === 0 ? (
        <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="admin-audit-empty">
          <p className="text-sm text-ink-muted">Todavía no hay eventos en la bitácora.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map(([day, events]) => (
            <section key={day} className="overflow-hidden rounded-md border border-line bg-bone-raised">
              <div className="border-b border-line bg-bone-sunk px-4 py-2 font-mono text-xs uppercase tracking-[0.14em] text-ink-muted">
                {day}
              </div>
              <ul className="divide-y divide-line font-mono text-xs">
                {events.map((event) => (
                  <li
                    key={event.id}
                    className="grid gap-1 px-4 py-3 sm:grid-cols-[7rem_1fr]"
                    data-testid={`audit-row-${event.id}`}
                  >
                    <span className="text-ink-faint">{formatStamp(event.at)}Z</span>
                    <span className="text-ink">
                      <span className="text-turquoise-900">{event.action}</span>
                      {" · "}
                      responsable {event.actor_kind}
                      {event.actor_user_id ? `/${event.actor_user_id.slice(0, 8)}` : ""}
                      {" · "}
                      objetivo {event.target_kind}/{event.target_id.slice(0, 8)}
                      {" · "}
                      {metadataLine(event)}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}

      {auditHaveMore ? <MoreResultsNote /> : null}
    </div>
  );
}
