import { useState } from "react";
import { Link } from "react-router-dom";
import { usePlansQuery, type PlanOut, type SubscribeResponse } from "@/api/hooks";
import { problemToMessage } from "@/lib/errors";
import { CheckoutModal } from "@/features/plans/checkout-modal";

function formatPrice(plan: PlanOut): string {
  if (plan.id === "pro") return "$0.02·h";
  if (plan.price_monthly_usd === 0) return "$0";
  return `$${plan.price_monthly_usd}`;
}

function formatPeriod(plan: PlanOut): string {
  if (plan.id === "sandbox") return "10 min";
  if (plan.id === "pro") return "pospago por hora";
  return "al mes";
}

export function PlansPage() {
  const { data: plans, isPending, isError, error, refetch } = usePlansQuery();
  const [selectedPlan, setSelectedPlan] = useState<PlanOut | null>(null);
  const [subscriptionSuccess, setSubscriptionSuccess] = useState<SubscribeResponse | null>(null);

  return (
    <div className="space-y-8 p-4 lg:p-8">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
          Catálogo y suscripciones
        </p>
        <h1 className="font-display text-3xl text-ink">Planes disponibles</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Elegí el plan adecuado para tus bases de datos PostgreSQL en contenedores aislados.
        </p>
      </div>

      {subscriptionSuccess ? (
        <div className="rounded-sm border-l-4 border-green-700 bg-paper p-6 shadow-print" role="region" aria-label="Suscripción confirmada">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <span className="inline-flex items-center gap-1.5 rounded-sm bg-green-100 px-2 py-0.5 text-xs font-medium text-ink">
                ● Activa
              </span>
              <h2 className="mt-2 font-display text-2xl text-ink">¡Suscripción contratada con éxito!</h2>
              <p className="mt-1 text-sm text-ink-muted">
                Tu plan <strong className="font-medium text-ink">{subscriptionSuccess.subscription.plan_id.toUpperCase()}</strong> está activo.
                Factura emitida: <code className="font-mono text-xs">{subscriptionSuccess.invoice.number}</code> (${subscriptionSuccess.invoice.total_usd.toFixed(4)} USD).
              </p>
            </div>
            <Link
              to="/app/ponds/new"
              className="inline-flex h-9 items-center justify-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900"
            >
              Crear mi primer pond →
            </Link>
          </div>
        </div>
      ) : null}

      {isPending ? (
        <div className="grid gap-6 md:grid-cols-3" data-testid="plans-loading">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-64 animate-pulse rounded-sm border border-line bg-bone-sunk" />
          ))}
        </div>
      ) : isError ? (
        <div className="rounded-sm border-l-4 border-danger bg-paper p-4" role="alert">
          <p className="text-sm font-medium text-ink">{problemToMessage(error)}</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 rounded-sm border border-line-control bg-bone-raised px-3 py-1.5 text-xs font-medium text-ink hover:bg-bone"
          >
            Reintentar
          </button>
        </div>
      ) : (
        <>
          <div className="grid gap-6 md:grid-cols-3">
            {plans?.map((plan) => {
              const isRecommended = plan.id === "micro";
              return (
                <div
                  key={plan.id}
                  className={`flex flex-col justify-between rounded-sm bg-bone-raised p-6 ${
                    isRecommended ? "border-2 border-turquoise-700" : "border border-line"
                  }`}
                  data-testid={`plan-card-${plan.id}`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <h2 className="font-display text-2xl text-ink">{plan.name}</h2>
                      {isRecommended ? (
                        <span className="rounded-sm bg-turquoise-100 px-2 py-0.5 text-xs font-medium text-turquoise-900">
                          Recomendado
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm text-ink-muted">{plan.description}</p>
                    <div className="mt-4 flex items-baseline gap-1">
                      <span className="font-display text-4xl text-ink tabular-nums">{formatPrice(plan)}</span>
                      <span className="text-xs text-ink-muted">/ {formatPeriod(plan)}</span>
                    </div>
                    <ul className="mt-6 space-y-2 text-sm text-ink">
                      <li className="flex items-center gap-2">
                        <span className="text-xs text-turquoise-700">●</span>
                        <span>{plan.max_ponds} pond{plan.max_ponds > 1 ? "s" : ""}</span>
                      </li>
                      <li className="flex items-center gap-2">
                        <span className="text-xs text-turquoise-700">●</span>
                        <span>{plan.max_storage_gb} GB de almacenamiento</span>
                      </li>
                      <li className="flex items-center gap-2">
                        <span className="text-xs text-turquoise-700">●</span>
                        <span>
                          {plan.id === "sandbox" ? "Validez 10 minutos" : plan.id === "micro" ? "Respaldos diarios (7 d)" : "Hasta 10 ponds y 20 GB"}
                        </span>
                      </li>
                    </ul>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelectedPlan(plan)}
                    className="mt-6 h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900"
                  >
                    Elegir plan {plan.name}
                  </button>
                </div>
              );
            })}
          </div>

          <div className="overflow-x-auto rounded-sm border border-line bg-paper">
            <div className="border-b border-line-control bg-bone-sunk px-4 py-3">
              <h2 className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
                Comparativa de características
              </h2>
            </div>
            <table className="w-full text-left text-sm" role="table">
              <thead>
                <tr className="border-b border-line-control bg-bone-sunk text-xs text-ink-muted">
                  <th className="px-4 py-2.5 font-medium">Característica</th>
                  <th className="px-4 py-2.5 text-right font-medium">Sandbox</th>
                  <th className="px-4 py-2.5 text-right font-medium">Micro</th>
                  <th className="px-4 py-2.5 text-right font-medium">Pro</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                <tr className="hover:bg-bone-raised">
                  <td className="px-4 py-2.5 font-medium text-ink">Ponds simultáneos</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">1</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">1</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">10</td>
                </tr>
                <tr className="hover:bg-bone-raised">
                  <td className="px-4 py-2.5 font-medium text-ink">Almacenamiento por pond</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">1 GB</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">1 GB</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">20 GB</td>
                </tr>
                <tr className="hover:bg-bone-raised">
                  <td className="px-4 py-2.5 font-medium text-ink">Respaldos automáticos</td>
                  <td className="px-4 py-2.5 text-right text-ink">No</td>
                  <td className="px-4 py-2.5 text-right text-ink">Diarios (7 días)</td>
                  <td className="px-4 py-2.5 text-right text-ink">Diarios (30 días)</td>
                </tr>
                <tr className="hover:bg-bone-raised">
                  <td className="px-4 py-2.5 font-medium text-ink">Precio base</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">$0 / 10 min</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">$5 / mes</td>
                  <td className="px-4 py-2.5 text-right font-mono tabular-nums text-ink">$0.02·h</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      {selectedPlan ? (
        <CheckoutModal
          plan={selectedPlan}
          onClose={() => setSelectedPlan(null)}
          onSuccess={(res) => {
            setSelectedPlan(null);
            setSubscriptionSuccess(res);
          }}
        />
      ) : null}
    </div>
  );
}
