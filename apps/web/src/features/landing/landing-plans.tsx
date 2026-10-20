import { Link } from "react-router-dom";
import { usePlansQuery } from "@/api/hooks";

interface PlanCardData {
  id: string;
  name: string;
  bandColor: string;
  isFeatured?: boolean;
  price: string;
  period?: string;
  help: string;
  features: string[];
  ctaText: string;
}

const defaultPlans: PlanCardData[] = [
  {
    id: "sandbox",
    name: "Sandbox",
    bandColor: "bg-green-700",
    price: "USD 0",
    help: "Pruebas internas del producto.",
    features: [
      "1 pond · 1 GB",
      "Vigencia 10 minutos",
      "Sin respaldos",
    ],
    ctaText: "Probar",
  },
  {
    id: "micro",
    name: "Micro",
    bandColor: "bg-turquoise-700",
    isFeatured: true,
    price: "USD 5",
    period: "/ mes",
    help: "1 pond, 1 GB, respaldos 7 días.",
    features: [
      "1 pond · 1 GB",
      "Vigencia mensual · pago simulado",
      "Respaldo diario · retención 7 días",
      "Consola SQL y acceso agente",
    ],
    ctaText: "Contratar Micro",
  },
  {
    id: "pro",
    name: "Pro",
    bandColor: "bg-marigold",
    price: "USD 0.02",
    period: "/ hora",
    help: "Hasta 10 ponds, post-pago por uso.",
    features: [
      "Hasta 10 ponds · 20 GB",
      "Vigencia por uso · post-pago",
      "Respaldo diario · retención 7 días",
    ],
    ctaText: "Contratar Pro",
  },
];

export function LandingPlans() {
  const { data: apiPlans } = usePlansQuery();

  const plans = defaultPlans.map((card) => {
    const apiPlan = apiPlans?.find((p) => p.id === card.id);
    if (!apiPlan) return card;
    const price = apiPlan.id === "pro"
      ? "USD 0.02"
      : `USD ${apiPlan.price_monthly_usd}`;
    return { ...card, name: apiPlan.name, price };
  });

  return (
    <section id="planes" className="space-y-6">
      <div className="border-t-2 border-turquoise-700 pt-3">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
          Planes · precio y vigencia
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {plans.map((plan) => (
          <article
            key={plan.id}
            className={`flex flex-col justify-between overflow-hidden rounded-md bg-bone-raised shadow-print transition-colors ${
              plan.isFeatured
                ? "border-2 border-turquoise-700"
                : "border border-line"
            }`}
          >
            <div>
              <div className={`h-1.5 w-full ${plan.bandColor}`} />
              <div className="p-5 space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-display text-2xl font-semibold text-ink">
                    {plan.name}
                  </h3>
                  {plan.isFeatured ? (
                    <span className="rounded-sm border border-turquoise-700/30 bg-turquoise-100 px-2 py-0.5 text-xs font-medium text-turquoise-900">
                      Recomendado
                    </span>
                  ) : null}
                </div>

                <div className="font-display text-4xl font-semibold tracking-tight text-ink">
                  {plan.price}
                  {plan.period ? (
                    <small className="font-sans text-sm font-normal text-ink-muted">
                      {" "}
                      {plan.period}
                    </small>
                  ) : null}
                </div>

                <p className="text-xs text-ink-muted">{plan.help}</p>

                <ul className="space-y-1.5 border-t border-line pt-3 text-xs text-ink-muted">
                  {plan.features.map((feat) => (
                    <li key={feat} className="flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-ink-muted" aria-hidden="true" />
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
                  plan.isFeatured
                    ? "bg-turquoise-700 text-bone-raised hover:bg-turquoise-900"
                    : "border border-line-control bg-paper text-ink hover:border-turquoise-700 hover:text-turquoise-700"
                }`}
              >
                {plan.ctaText}
              </Link>
            </div>
          </article>
        ))}
      </div>

      <div className="flex items-center gap-3 rounded-sm border border-line bg-bone-raised p-4 text-xs leading-5 text-ink-muted">
        <span className="font-mono text-sm font-bold text-turquoise-700" aria-hidden="true">
          ▲
        </span>
        <p>
          <strong className="font-semibold text-ink">Pago simulado.</strong>{" "}
          Este es un proyecto académico: no se realiza ningún cobro real y no hay pasarela de pago.
        </p>
      </div>
    </section>
  );
}
