import { Link } from "react-router-dom";
import { usePlansQuery, type PlanOut } from "@/api/hooks";
import { problemToMessage } from "@/lib/errors";

const PLAN_PRESENTATION: Record<
  string,
  { bandColor: string; isFeatured?: boolean; ctaText: string }
> = {
  sandbox: {
    bandColor: "bg-green-700",
    ctaText: "Probar",
  },
  micro: {
    bandColor: "bg-turquoise-700",
    isFeatured: true,
    ctaText: "Contratar Micro",
  },
  pro: {
    bandColor: "bg-marigold",
    ctaText: "Contratar Pro",
  },
};

function formatPrice(plan: PlanOut): string {
  if (plan.id === "pro") return "USD 0.02";
  return `USD ${plan.price_monthly_usd}`;
}

function formatPeriod(plan: PlanOut): string | undefined {
  if (plan.id === "sandbox") return undefined;
  if (plan.id === "pro") return "/ hora";
  return "/ mes";
}

function formatValidity(plan: PlanOut): string {
  if (plan.id === "sandbox") {
    return `Vigencia ${plan.validity_minutes} minutos`;
  }
  if (plan.postpaid) {
    return "Vigencia por uso · post-pago";
  }
  return "Vigencia mensual · pago simulado";
}

function planFeatures(plan: PlanOut): string[] {
  return [
    `${plan.max_ponds} pond${plan.max_ponds > 1 ? "s" : ""} · ${plan.max_storage_gb} GB`,
    formatValidity(plan),
  ];
}

export function LandingPlans() {
  const { data: plans, isPending, isError, error, refetch } = usePlansQuery();

  return (
    <section id="planes" className="space-y-6">
      <div className="border-t-2 border-turquoise-700 pt-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
          Planes · precio y vigencia
        </h2>
      </div>

      {isPending ? (
        <div className="grid gap-6 md:grid-cols-3" data-testid="landing-plans-loading">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-64 animate-pulse rounded-md border border-line bg-bone-sunk"
              aria-hidden="true"
            />
          ))}
          <p className="sr-only">Cargando planes…</p>
        </div>
      ) : isError ? (
        <div
          className="rounded-sm border-l-4 border-danger bg-paper p-4"
          role="alert"
          data-testid="landing-plans-error"
        >
          <p className="text-sm font-medium text-ink">{problemToMessage(error)}</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="mt-3 rounded-sm border border-line-control bg-bone-raised px-3 py-1.5 text-xs font-medium text-ink hover:bg-bone"
          >
            Reintentar
          </button>
        </div>
      ) : !plans || plans.length === 0 ? (
        <div
          className="rounded-sm border border-line bg-bone-raised p-6 text-sm text-ink-muted"
          data-testid="landing-plans-empty"
        >
          No hay planes publicados por ahora.
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-3">
          {plans.map((plan) => {
            const presentation = PLAN_PRESENTATION[plan.id] ?? {
              bandColor: "bg-turquoise-700",
              ctaText: "Crear cuenta",
            };
            const period = formatPeriod(plan);
            return (
              <article
                key={plan.id}
                data-testid={`landing-plan-card-${plan.id}`}
                className={`flex flex-col justify-between overflow-hidden rounded-md bg-bone-raised shadow-print transition-colors ${
                  presentation.isFeatured
                    ? "border-2 border-turquoise-700"
                    : "border border-line"
                }`}
              >
                <div>
                  <div className={`h-1.5 w-full ${presentation.bandColor}`} />
                  <div className="space-y-3 p-5">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="font-display text-2xl font-semibold text-ink">
                        {plan.name}
                      </h3>
                      {presentation.isFeatured ? (
                        <span className="rounded-sm border border-turquoise-700/30 bg-turquoise-100 px-2 py-0.5 text-xs font-medium text-turquoise-900">
                          Recomendado
                        </span>
                      ) : null}
                    </div>

                    <div className="font-display text-4xl font-semibold tracking-tight tabular-nums text-ink">
                      {formatPrice(plan)}
                      {period ? (
                        <small className="font-sans text-sm font-normal text-ink-muted">
                          {" "}
                          {period}
                        </small>
                      ) : null}
                    </div>

                    <p className="text-xs text-ink-muted">{plan.description}</p>

                    <ul className="space-y-1.5 border-t border-line pt-3 text-xs text-ink-muted">
                      {planFeatures(plan).map((feat) => (
                        <li key={feat} className="flex items-center gap-2">
                          <span
                            className="h-1.5 w-1.5 rounded-full bg-ink-muted"
                            aria-hidden="true"
                          />
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>

                <div className="p-5 pt-0">
                  <Link
                    to="/register"
                    className={`block w-full rounded-sm py-2 text-center text-xs font-medium transition-colors duration-instant ${
                      presentation.isFeatured
                        ? "bg-turquoise-700 text-bone-raised hover:bg-turquoise-900"
                        : "border border-line-control bg-paper text-ink hover:border-turquoise-700 hover:text-turquoise-700"
                    }`}
                  >
                    {presentation.ctaText}
                  </Link>
                </div>
              </article>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-3 rounded-sm border border-line bg-bone-raised p-4 text-xs leading-5 text-ink-muted">
        <span className="font-mono text-sm font-bold text-turquoise-700" aria-hidden="true">
          ▲
        </span>
        <p>
          <strong className="font-semibold text-ink">Pago simulado.</strong> Este es un
          proyecto académico: no se realiza ningún cobro real y no hay pasarela de pago.
        </p>
      </div>
    </section>
  );
}
