import { Link } from "react-router-dom";
import { usePlansQuery } from "@/api/hooks";
import { formatPrice } from "@/lib/format-price";

export function LandingHero() {
  const { data: plans } = usePlansQuery();
  const micro = plans?.find((plan) => plan.id === "micro");
  const microPrice = micro ? formatPrice(micro) : "—";

  return (
    <section className="flex flex-col gap-8">
      <div>
        <h1 className="font-display text-4xl font-semibold tracking-tight text-ink sm:text-5xl lg:text-[56px] lg:leading-[60px]">
          Tu Postgres en línea antes de que se enfríe el café.
        </h1>
        <p className="mt-4 max-w-measure text-base leading-relaxed text-ink-muted">
          KoiCloud te da una base PostgreSQL 16 gestionada — un{" "}
          <strong className="font-semibold text-ink">pond</strong> — con cadena de
          conexión, consola SQL, respaldos diarios y uso medido. Desde la web,
          desde la terminal o desde tu agente.
        </p>

        <div className="mt-6 flex flex-wrap items-center gap-3">
          <Link
            to="/register"
            className="rounded-sm bg-turquoise-700 px-5 py-2.5 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900"
          >
            Crear cuenta
          </Link>
          <a
            href="#planes"
            className="rounded-sm border border-line-control bg-paper px-5 py-2.5 text-sm font-medium text-ink transition-colors duration-instant hover:border-turquoise-700 hover:text-turquoise-700"
          >
            Ver planes
          </a>
        </div>

        <div className="mt-8 flex flex-wrap gap-6 border-t border-line pt-6 sm:gap-8">
          <div>
            <div className="font-display text-2xl font-semibold tabular-nums text-ink sm:text-3xl">
              ~40 s
            </div>
            <div className="text-xs text-ink-muted">de crear a conectar</div>
          </div>
          <div>
            <div className="font-display text-2xl font-semibold tabular-nums text-ink sm:text-3xl">
              3
            </div>
            <div className="text-xs text-ink-muted">superficies: web, CLI, MCP</div>
          </div>
          <div>
            <div
              className="font-display text-2xl font-semibold tabular-nums text-ink sm:text-3xl"
              data-testid="landing-hero-micro-price"
            >
              {microPrice}
            </div>
            <div className="text-xs text-ink-muted">plan Micro al mes</div>
          </div>
        </div>
      </div>

      <div
        className="pond-water-hero relative h-[320px] w-full overflow-hidden rounded-md border border-line shadow-print"
        role="img"
        aria-label="Estanque de peces koi"
      >
        <i
          className="koi--x2 pointer-events-none absolute"
          style={{ left: "13%", top: "42%" }}
          aria-hidden="true"
        />
        <i
          className="koi pointer-events-none absolute"
          style={{ left: "57%", top: "10%", animationDelay: "-11s" }}
          aria-hidden="true"
        />
        <i
          className="koi pointer-events-none absolute"
          style={{ left: "87%", top: "30%", animationDelay: "-19s" }}
          aria-hidden="true"
        />
      </div>
    </section>
  );
}
