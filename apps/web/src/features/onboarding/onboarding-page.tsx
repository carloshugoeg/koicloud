import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useCompleteOnboardingMutation,
  usePlansQuery,
  type PlanOut,
} from "@/api/hooks";
import { AuthErrorBanner } from "@/features/auth/auth-layout";
import { CheckoutModal } from "@/features/plans/checkout-modal";
import { formatPrice, formatPricePeriod } from "@/lib/format-price";

const PAID_PLAN_IDS = new Set(["micro", "pro"]);

export function OnboardingPage() {
  const navigate = useNavigate();
  const plansQuery = usePlansQuery();
  const completeMutation = useCompleteOnboardingMutation();
  const [checkoutPlan, setCheckoutPlan] = useState<PlanOut | null>(null);
  const [localError, setLocalError] = useState<Error | null>(null);

  const paidPlans = (plansQuery.data ?? []).filter((plan) => PAID_PLAN_IDS.has(plan.id));

  async function continueFree() {
    setLocalError(null);
    try {
      await completeMutation.mutateAsync();
      navigate("/app", { replace: true });
    } catch (error) {
      setLocalError(error instanceof Error ? error : new Error("No se pudo continuar."));
    }
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden text-ink">
      <div
        data-testid="onboarding-pond"
        className="pond-water-auth pointer-events-none absolute inset-0"
        role="img"
        aria-label="Estanque de peces koi"
      >
        <i
          className="koi--x2 absolute"
          style={{ left: "12%", top: "38%" }}
          aria-hidden="true"
        />
        <i
          className="koi absolute"
          style={{ left: "58%", top: "14%", animationDelay: "-11s" }}
          aria-hidden="true"
        />
        <i
          className="koi absolute"
          style={{ left: "78%", top: "62%", animationDelay: "-19s" }}
          aria-hidden="true"
        />
      </div>

      <div className="relative z-10 mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center gap-8 px-4 py-10 sm:px-6">
        <header className="space-y-2 rounded-md border border-line bg-bone-raised/95 px-5 py-4 shadow-print">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
            Bienvenida · Elige tu plan
          </p>
          <h1 className="font-display text-3xl font-semibold text-ink">¿Cómo quieres empezar?</h1>
          <p className="max-w-2xl text-sm leading-6 text-ink-muted">
            Tu cuenta ya tiene el modo sandbox gratis. Puedes contratar Micro o Pro ahora, o
            continuar gratis y cambiar de plan cuando quieras.
          </p>
        </header>

        <AuthErrorBanner error={localError ?? completeMutation.error ?? plansQuery.error} />

        {plansQuery.isLoading ? (
          <p className="rounded-md border border-line bg-bone-raised/95 px-4 py-3 text-sm text-ink-muted shadow-print">
            Cargando planes…
          </p>
        ) : null}

        {!plansQuery.isLoading && paidPlans.length === 0 && !plansQuery.isError ? (
          <p className="rounded-md border border-line bg-bone-raised/95 px-4 py-3 text-sm text-ink-muted shadow-print">
            No hay planes disponibles por ahora.
          </p>
        ) : null}

        {plansQuery.isError ? (
          <p className="rounded-md border border-line bg-bone-raised/95 px-4 py-3 text-sm text-danger shadow-print">
            No pudimos cargar los planes. Reintentá en un momento.
          </p>
        ) : null}

        <ul className="grid gap-4 sm:grid-cols-2">
          {paidPlans.map((plan) => (
            <li
              key={plan.id}
              className="rounded-md border border-line bg-bone-raised/95 p-5 shadow-print"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
                {plan.id}
              </p>
              <h2 className="mt-1 font-display text-2xl font-semibold text-ink">{plan.name}</h2>
              <p className="mt-2 text-sm leading-5 text-ink-muted">{plan.description}</p>
              <p className="mt-4 font-mono text-lg tabular-nums text-ink">
                {formatPrice(plan)}
                <span className="text-sm text-ink-muted"> {formatPricePeriod(plan)}</span>
              </p>
              <button
                type="button"
                className="mt-4 inline-flex h-9 items-center justify-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900"
                onClick={() => setCheckoutPlan(plan)}
              >
                Elegir {plan.name}
              </button>
            </li>
          ))}
        </ul>

        <div className="rounded-md border border-line bg-bone-raised/95 p-5 shadow-print">
          <h2 className="font-display text-xl font-semibold text-ink">
            Continuar gratis (modo sandbox)
          </h2>
          <p className="mt-2 text-sm leading-5 text-ink-muted">
            Sigues en sandbox para probar el producto. Puedes contratar un plan después desde Uso y
            facturación.
          </p>
          <button
            type="button"
            disabled={completeMutation.isPending}
            className="mt-4 inline-flex h-9 items-center justify-center rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink hover:bg-bone disabled:text-ink-faint"
            onClick={() => void continueFree()}
          >
            {completeMutation.isPending ? "Guardando…" : "Continuar gratis (modo sandbox)"}
          </button>
        </div>
      </div>

      {checkoutPlan ? (
        <CheckoutModal
          plan={checkoutPlan}
          onClose={() => setCheckoutPlan(null)}
          onSuccess={() => {
            void (async () => {
              try {
                await completeMutation.mutateAsync();
                setCheckoutPlan(null);
                navigate("/app", { replace: true });
              } catch (error) {
                setLocalError(
                  error instanceof Error
                    ? error
                    : new Error("No se pudo completar el onboarding."),
                );
                setCheckoutPlan(null);
              }
            })();
          }}
        />
      ) : null}
    </div>
  );
}
