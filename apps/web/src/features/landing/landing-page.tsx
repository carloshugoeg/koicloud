import { Link } from "react-router-dom";
import { LandingHero } from "@/features/landing/landing-hero";
import { LandingPlans } from "@/features/landing/landing-plans";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-bone text-ink" data-landing-prerender>
      <header className="border-b border-line bg-bone">
        <div className="mx-auto flex h-14 max-w-content items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link to="/" className="inline-flex items-center gap-2.5 no-underline">
            <span aria-hidden="true" className="koi-mark-32 shrink-0" />
            <span className="font-display text-2xl font-semibold tracking-tight text-ink">
              KoiCloud
            </span>
          </Link>

          <nav className="flex items-center gap-3 text-sm sm:gap-5">
            <a
              href="#planes"
              className="hidden font-medium text-ink-muted transition-colors duration-instant hover:text-ink sm:inline"
            >
              Planes
            </a>
            <a
              href="#como-funciona"
              className="hidden font-medium text-ink-muted transition-colors duration-instant hover:text-ink sm:inline"
            >
              Cómo funciona
            </a>
            <Link
              to="/login"
              className="rounded-sm border border-line-control bg-paper px-3 py-1.5 text-xs font-medium text-ink transition-colors duration-instant hover:border-turquoise-700 hover:text-turquoise-700"
            >
              Iniciar sesión
            </Link>
            <Link
              to="/register"
              className="hidden rounded-sm bg-turquoise-700 px-3 py-1.5 text-xs font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 sm:inline-block"
            >
              Crear cuenta
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex max-w-content flex-col gap-14 px-4 py-8 pb-24 sm:px-6 lg:px-8 lg:pb-8">
        <LandingHero />

        <LandingPlans />

        <section id="como-funciona" className="space-y-6">
          <div className="border-t-2 border-green-700 pt-3">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
              Cómo funciona
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-3">
            <div className="rounded-b-sm border-x border-b border-t-4 border-line border-t-turquoise-700 bg-bone-raised p-5 shadow-print">
              <p className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Paso 1
              </p>
              <h3 className="mt-2 font-display text-xl font-semibold text-ink">
                Contratas un plan
              </h3>
              <p className="mt-1 text-xs leading-5 text-ink-muted">
                El pago es simulado y queda registrado con su factura. Tu suscripción define
                cuántos ponds puedes tener.
              </p>
            </div>

            <div className="rounded-b-sm border-x border-b border-t-4 border-line border-t-green-700 bg-bone-raised p-5 shadow-print">
              <p className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Paso 2
              </p>
              <h3 className="mt-2 font-display text-xl font-semibold text-ink">
                Creas tu pond
              </h3>
              <p className="mt-1 text-xs leading-5 text-ink-muted">
                Encolamos el trabajo, el nodo levanta un contenedor PostgreSQL 16 real y te
                devolvemos host, puerto y credenciales.
              </p>
            </div>

            <div className="rounded-b-sm border-x border-b border-t-4 border-line border-t-marigold bg-bone-raised p-5 shadow-print">
              <p className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Paso 3
              </p>
              <h3 className="mt-2 font-display text-xl font-semibold text-ink">
                Te conectas
              </h3>
              <p className="mt-1 text-xs leading-5 text-ink-muted">
                Desde tu app con la URI, desde la consola SQL del navegador, desde la CLI o
                desde tu agente por MCP.
              </p>
            </div>
          </div>
        </section>

        <footer className="flex flex-wrap items-center justify-between gap-4 border-t border-line py-6 text-xs text-ink-muted">
          <p>
            Equipo KoiCloud — Hugo Escobar, Jason Gutiérrez, Jousé Menendez, Diego Joachin.
          </p>
          <p>Universidad Rafael Landívar · 2026</p>
        </footer>
      </main>

      <div
        className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-bone-raised p-3 shadow-print md:hidden"
        data-testid="landing-sticky-cta"
      >
        <Link
          to="/register"
          className="block w-full rounded-sm bg-turquoise-700 px-4 py-2.5 text-center text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900"
        >
          Crear cuenta
        </Link>
      </div>
    </div>
  );
}
