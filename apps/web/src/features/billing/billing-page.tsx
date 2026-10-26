import { useState } from "react";
import { Link } from "react-router-dom";
import {
  useCancelSubscriptionMutation,
  useSubscriptionsQuery,
  type SubscriptionOut,
} from "@/api/hooks/subscriptions";
import { DataStateError } from "@/components/data-state";
import { CancelDialog } from "@/features/billing/cancel-dialog";
import {
  subscriptionPhase,
  subscriptionPhaseMeta,
} from "@/features/billing/subscription-phase";

const DAY_FORMAT = new Intl.DateTimeFormat("es-GT", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  timeZone: "America/Guatemala",
});

const CUTOFF_FORMAT = new Intl.DateTimeFormat("es-GT", {
  day: "2-digit",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "America/Guatemala",
});

function formatStamp(iso: string, withTime: boolean) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return (withTime ? CUTOFF_FORMAT : DAY_FORMAT).format(date);
}

function planLabel(planId: string) {
  if (!planId) {
    return planId;
  }
  return planId.charAt(0).toUpperCase() + planId.slice(1);
}

export function BillingPage() {
  const subscriptionsQuery = useSubscriptionsQuery();
  const cancel = useCancelSubscriptionMutation();
  const [targetId, setTargetId] = useState<string | null>(null);

  if (subscriptionsQuery.isPending) {
    return (
      <div className="space-y-3" role="status" aria-busy="true" data-testid="billing-loading">
        <p className="text-sm text-ink-muted">Cargando suscripciones…</p>
        <div className="h-10 rounded-sm bg-bone-sunk" />
        <div className="h-24 rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (subscriptionsQuery.isError) {
    return (
      <DataStateError
        error={subscriptionsQuery.error}
        onRetry={() => {
          void subscriptionsQuery.refetch();
        }}
        testId="billing-error"
      />
    );
  }

  const rows = subscriptionsQuery.data;
  const target = rows.find((row) => row.id === targetId) ?? null;

  function closeDialog() {
    setTargetId(null);
    cancel.reset();
  }

  function confirmCancel() {
    if (!target) {
      return;
    }
    cancel.mutate(target.id, { onSuccess: () => closeDialog() });
  }

  return (
    <div className="space-y-4" data-testid="billing-page">
      <p className="max-w-measure text-sm text-ink-muted">
        Historial de tus suscripciones. Cancelar al corte deja el plan activo hasta el fin del período.
      </p>

      {rows.length === 0 ? (
        <div
          className="rounded-md border border-line bg-bone-raised p-8 text-center"
          data-testid="billing-empty"
        >
          <h2 className="font-display text-2xl text-ink">Sin suscripciones</h2>
          <p className="mt-2 text-sm text-ink-muted">Todavía no tienes un plan contratado.</p>
          <Link
            to="/app/planes"
            className="mt-5 inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus-visible:shadow-focus"
          >
            Ver planes
          </Link>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-line bg-bone-raised">
          <table className="w-full table-fixed border-collapse text-sm" aria-label="Historial de suscripciones">
            <thead className="bg-bone-sunk text-left text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
              <tr>
                <th className="border-b border-line px-3 py-2 font-medium">Plan</th>
                <th className="border-b border-line px-3 py-2 font-medium">Estado</th>
                <th className="border-b border-line px-3 py-2 text-right font-medium">Período</th>
                <th className="border-b border-line px-3 py-2 text-right font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <SubscriptionRow
                  key={row.id}
                  row={row}
                  onCancel={() => setTargetId(row.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {target ? (
        <CancelDialog
          planLabel={planLabel(target.plan_id)}
          periodEndLabel={formatStamp(target.current_period_end, true)}
          pending={cancel.isPending}
          error={cancel.error}
          onDismiss={closeDialog}
          onConfirm={confirmCancel}
        />
      ) : null}
    </div>
  );
}

function SubscriptionRow({
  row,
  onCancel,
}: {
  row: SubscriptionOut;
  onCancel: () => void;
}) {
  const phase = subscriptionPhase(row);
  const meta = subscriptionPhaseMeta(row);

  return (
    <tr className="min-h-row border-b border-line" data-testid={`subscription-row-${row.id}`}>
      <td className="px-3 py-2 align-top font-medium text-ink">{planLabel(row.plan_id)}</td>
      <td className="px-3 py-2 align-top">
        <span
          className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${meta.badgeClass}`}
          data-testid={`subscription-phase-${row.id}`}
        >
          <span aria-hidden>{meta.glyph}</span>
          {meta.label}
        </span>
      </td>
      <td className="px-3 py-2 text-right align-top font-mono text-xs tabular-nums text-ink">
        <span className="block">{formatStamp(row.current_period_start, false)}</span>
        <span className="block">{formatStamp(row.current_period_end, false)}</span>
      </td>
      <td className="px-3 py-2 text-right align-top">
        {phase === "active" ? (
          <button
            type="button"
            className="whitespace-normal rounded-sm px-2 py-1 text-right text-sm font-medium text-turquoise-700 focus-visible:shadow-focus"
            onClick={onCancel}
          >
            Cancelar al corte
          </button>
        ) : (
          <span className="text-sm text-ink-muted">—</span>
        )}
      </td>
    </tr>
  );
}
