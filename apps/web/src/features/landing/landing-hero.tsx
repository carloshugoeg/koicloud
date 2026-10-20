import { Link } from "react-router-dom";

export function LandingHero() {
  return (
    <section className="grid items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
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

        <div className="mt-8 flex flex-wrap gap-6 sm:gap-8 border-t border-line pt-6">
          <div>
            <div className="font-display text-2xl sm:text-3xl font-semibold text-ink">~40 s</div>
            <div className="text-xs text-ink-muted">de crear a conectar</div>
          </div>
          <div>
            <div className="font-display text-2xl sm:text-3xl font-semibold text-ink">3</div>
            <div className="text-xs text-ink-muted">superficies: web, CLI, MCP</div>
          </div>
          <div>
            <div className="font-display text-2xl sm:text-3xl font-semibold text-ink">USD 5</div>
            <div className="text-xs text-ink-muted">plan Micro al mes</div>
          </div>
        </div>
      </div>

      <div
        className="pond-water-hero relative h-[320px] w-full overflow-hidden rounded-[6px] border border-line shadow-print"
        role="img"
        aria-label="Estanque de peces koi"
      >
        <i className="koi--x2 absolute pointer-events-none" style={{ left: "13%", top: "42%" }} aria-hidden="true" />
        <i className="koi absolute pointer-events-none" style={{ left: "57%", top: "10%", animationDelay: "-11s" }} aria-hidden="true" />
        <i className="koi absolute pointer-events-none" style={{ left: "87%", top: "30%", animationDelay: "-19s" }} aria-hidden="true" />
      </div>
    </section>
  );
}
