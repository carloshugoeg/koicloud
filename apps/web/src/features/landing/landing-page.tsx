import { Link } from "react-router-dom";
import { LandingAgents } from "@/features/landing/landing-agents";
import { LandingFaq } from "@/features/landing/landing-faq";
import { LandingFinalCta } from "@/features/landing/landing-final-cta";
import { LandingHero } from "@/features/landing/landing-hero";
import { LandingHow } from "@/features/landing/landing-how";
import { LandingPlans } from "@/features/landing/landing-plans";
import { LandingSurfaces } from "@/features/landing/landing-surfaces";

export function LandingPage() {
  return (
    <div className="min-h-screen bg-bone text-ink" data-landing-prerender>
      <header className="sticky top-0 z-30 border-b border-line bg-bone/95 backdrop-blur-sm">
        <div className="mx-auto flex h-14 max-w-content items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
          <Link to="/" className="inline-flex min-w-0 items-center gap-2 no-underline">
            <span aria-hidden="true" className="koi-mark-32 shrink-0" />
            <span className="truncate font-display text-xl font-semibold tracking-tight text-ink sm:text-2xl">
              KoiCloud
            </span>
          </Link>

          <nav className="flex shrink-0 items-center gap-2 text-sm sm:gap-4">
            <a
              href="#planes"
              className="hidden font-medium text-ink-muted transition-colors duration-instant hover:text-ink md:inline"
            >
              Planes
            </a>
            <a
              href="#como-funciona"
              className="hidden font-medium text-ink-muted transition-colors duration-instant hover:text-ink md:inline"
            >
              Cómo funciona
            </a>
            <Link
              to="/login"
              className="rounded-sm border border-line-control bg-paper px-3 py-2 text-xs font-medium text-ink transition-colors duration-instant hover:border-turquoise-700 hover:text-turquoise-700 focus-visible:outline-none focus-visible:shadow-focus"
            >
              Iniciar sesión
            </Link>
            <Link
              to="/register"
              className="inline-flex min-h-9 items-center rounded-sm bg-turquoise-700 px-3 py-2 text-xs font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 focus-visible:outline-none focus-visible:shadow-focus"
            >
              Crear cuenta
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto flex max-w-content flex-col gap-12 px-4 py-6 pb-28 sm:gap-14 sm:px-6 sm:py-8 lg:px-8 lg:pb-10">
        <LandingHero />
        <LandingHow />
        <LandingAgents />
        <LandingSurfaces />
        <LandingPlans />
        <LandingFaq />
        <LandingFinalCta />

        <footer className="flex flex-col gap-2 border-t border-line py-6 text-xs text-ink-muted sm:flex-row sm:flex-wrap sm:items-center sm:justify-between sm:gap-4">
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
          className="flex min-h-11 w-full items-center justify-center rounded-sm bg-turquoise-700 px-4 py-3 text-center text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 focus-visible:outline-none focus-visible:shadow-focus"
        >
          Crear cuenta
        </Link>
      </div>
    </div>
  );
}
