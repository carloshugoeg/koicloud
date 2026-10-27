import { useMemo, useState } from "react";
import {
  useAdminSubscriptionsQuery,
  type AdminSubscription,
} from "@/api/hooks/admin";
import { MoreResultsNote } from "@/features/admin/more-results-note";
import { ApiError, problemToMessage } from "@/lib/errors";

type StatusFilter = "all" | AdminSubscription["status"];

const STATUS_LABEL: Record<AdminSubscription["status"], string> = {
  pending_payment: "Pago pendiente",
  active: "Activa",
  canceled: "Cancelada",
  expired: "Expirada",
  past_due: "Vencida",
};

const STATUS_BADGE: Record<AdminSubscription["status"], string> = {
  pending_payment: "rounded-sm bg-marigold px-2 py-1 text-xs text-ink",
  active: "rounded-sm bg-green-100 px-2 py-1 text-xs text-ink",
  canceled: "rounded-sm bg-bone-sunk px-2 py-1 text-xs text-ink-muted",
  expired: "rounded-sm bg-bone-sunk px-2 py-1 text-xs text-ink-muted",
  past_due: "rounded-sm bg-danger-soft px-2 py-1 text-xs text-danger",
};

function formatPeriod(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("es-GT", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "UTC",
  }).format(date);
}

export function AdminSubscriptionsPage() {
  const subscriptionsQuery = useAdminSubscriptionsQuery();
  const [emailFilter, setEmailFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");

  const subscriptions = useMemo(() => {
    const rows = subscriptionsQuery.data?.subscriptions ?? [];
    const needle = emailFilter.trim().toLowerCase();
    return rows.filter((row) => {
      if (statusFilter !== "all" && row.status !== statusFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        row.user_email.toLowerCase().includes(needle) ||
        row.plan_id.toLowerCase().includes(needle)
      );
    });
  }, [subscriptionsQuery.data?.subscriptions, emailFilter, statusFilter]);

  if (subscriptionsQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="admin-subscriptions-loading">
        <div className="h-10 w-56 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-64 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (subscriptionsQuery.isError) {
    return (
      <div
        className="rounded-md border border-line bg-bone-raised p-5"
        data-testid="admin-subscriptions-error"
      >
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(subscriptionsQuery.error)}</p>
          <p className="mt-1 font-mono text-xs text-ink-faint">
            {subscriptionsQuery.error instanceof ApiError
              ? subscriptionsQuery.error.problem?.code
              : "error"}
          </p>
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void subscriptionsQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const haveMore = Boolean(subscriptionsQuery.data?.next_cursor);

  return (
    <div className="space-y-4" data-testid="admin-subscriptions-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-sm text-ink-muted" data-testid="admin-subscriptions-summary">
          {subscriptions.length} suscripciones visibles · solo lectura.
        </p>
        <div className="flex flex-wrap gap-2" data-testid="admin-subscriptions-filters">
          <label className="text-xs text-ink-muted">
            Correo / plan
            <input
              className="mt-1 block h-9 w-52 rounded-sm border border-line-control bg-bone-raised px-3 text-sm"
              value={emailFilter}
              onChange={(event) => setEmailFilter(event.target.value)}
              placeholder="correo o plan"
            />
          </label>
          <label className="text-xs text-ink-muted">
            Estado
            <select
              className="mt-1 block h-9 rounded-sm border border-line-control bg-bone-raised px-3 text-sm"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              <option value="all">Todos</option>
              {(Object.keys(STATUS_LABEL) as AdminSubscription["status"][]).map((status) => (
                <option key={status} value={status}>
                  {STATUS_LABEL[status]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {subscriptions.length === 0 ? (
        <div
          className="rounded-md border border-line bg-bone-raised p-8 text-center"
          data-testid="admin-subscriptions-empty"
        >
          <p className="text-sm text-ink-muted">No hay suscripciones con ese filtro.</p>
        </div>
      ) : (
        <div
          className="overflow-x-auto rounded-md border border-line bg-bone-raised"
          tabIndex={0}
          role="region"
          aria-label="Suscripciones"
          data-testid="admin-subscriptions-table"
        >
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead className="bg-bone-sunk text-left text-xs uppercase tracking-[0.12em] text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Dueño</th>
                <th className="px-4 py-3 font-medium">Plan</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 text-right font-medium">Inicio</th>
                <th className="px-4 py-3 text-right font-medium">Fin</th>
                <th className="px-4 py-3 font-medium">Cancela al fin</th>
              </tr>
            </thead>
            <tbody>
              {subscriptions.map((row) => (
                <tr
                  key={row.id}
                  className="border-t border-line"
                  data-testid={`admin-subscription-row-${row.id}`}
                >
                  <td className="px-4 py-3 font-mono text-xs">{row.user_email}</td>
                  <td className="px-4 py-3 font-mono text-xs">{row.plan_id}</td>
                  <td className="px-4 py-3">
                    <span className={STATUS_BADGE[row.status]}>
                      {STATUS_LABEL[row.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">
                    {formatPeriod(row.current_period_start)}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs tabular-nums">
                    {formatPeriod(row.current_period_end)}
                  </td>
                  <td className="px-4 py-3 text-xs text-ink-muted">
                    {row.cancel_at_period_end ? "Sí" : "No"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {haveMore ? <MoreResultsNote /> : null}
    </div>
  );
}
