import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useCancelSubscriptionMutation,
  useSubscriptionsQuery,
  type Subscription,
} from "@/api/hooks/subscriptions";
import { DataStateError, DataStateLoading } from "@/components/data-state";
import { CancelDialog } from "@/features/billing/cancel-dialog";
import {
  canCancelSubscription,
  subscriptionPhaseMeta,
} from "@/features/billing/subscription-phase";

const dayFormat = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/Guatemala",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

function formatDay(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "—";
  }
  return dayFormat.format(date);
}

export function BillingPage() {
  const query = useSubscriptionsQuery();
  const cancel = useCancelSubscriptionMutation();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (query.isPending) {
    return <DataStateLoading testId="billing-loading" />;
  }

  if (query.isError) {
    return (
      <DataStateError
        error={query.error}
        onRetry={() => void query.refetch()}
        testId="billing-error"
      />
    );
  }

  const rows = query.data ?? [];
  const selected = rows.find((row) => row.id === selectedId) ?? null;

  async function confirmCancel() {
    if (!selected) {
      return;
    }
    try {
      await cancel.mutateAsync(selected.id);
      setSelectedId(null);
    } catch {
      // The dialog reads cancel.error.
    }
  }

  return (
    <div className="space-y-6" data-testid="billing-page">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">Facturación</p>
        <h1 className="font-display text-3xl text-ink">Suscripciones</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Cancelar al corte deja el plan activo hasta el fin del período.
        </p>
      </div>

      {rows.length === 0 ? (
        <div
          className="rounded-md border border-line bg-bone-raised p-8 text-center"
          data-testid="billing-empty"
        >
          <h2 className="font-display text-2xl text-ink">Sin suscripciones</h2>
          <p className="mt-2 text-sm text-ink-muted">Cuando contrates un plan, el historial aparece aquí.</p>
          <Link
            to="/app/planes"
            className="mt-5 inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
          >
            Ver planes
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-sm border border-line bg-paper">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-bone-sunk text-xs text-ink-muted">
                <th className="px-4 py-2.5 font-medium">Plan</th>
                <th className="px-4 py-2.5 font-medium">Estado</th>
                <th className="px-4 py-2.5 font-medium">Período</th>
                <th className="px-4 py-2.5 text-right font-medium">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((row: Subscription) => {
                const phase = subscriptionPhaseMeta(row);
                return (
                  <tr key={row.id} data-testid={`subscription-${row.id}`}>
                    <td className="px-4 py-2.5 font-mono text-ink">{row.plan_id}</td>
                    <td className="px-4 py-2.5">
                      <span
                        className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${phase.badgeClass}`}
                      >
                        <span aria-hidden>{phase.glyph}</span>
                        {phase.label}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs tabular-nums text-ink">
                      {formatDay(row.current_period_start)} → {formatDay(row.current_period_end)}
                    </td>
                    <td className="px-4 py-2.5 text-right">
                      {canCancelSubscription(row) ? (
                        <button
                          type="button"
                          className="h-8 rounded-sm border border-danger bg-bone-raised px-3 text-xs font-medium text-danger"
                          onClick={() => setSelectedId(row.id)}
                        >
                          Cancelar al corte
                        </button>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {selected ? (
        <CancelDialog
          planLabel={selected.plan_id}
          periodEndLabel={formatDay(selected.current_period_end)}
          pending={cancel.isPending}
          error={cancel.error}
          onDismiss={() => setSelectedId(null)}
          onConfirm={() => void confirmCancel()}
        />
      ) : null}
    </div>
  );
}
