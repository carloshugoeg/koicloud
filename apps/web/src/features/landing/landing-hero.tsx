import { Link } from "react-router-dom";
import {
  LANDING_HERO_SUPPORT,
  LANDING_THESIS,
  LANDING_WHAT_IS,
} from "@/features/landing/landing-copy";

export function LandingHero() {
  return (
    <section
      className="flex flex-col gap-10 sm:gap-12 lg:gap-14"
      aria-labelledby="landing-hero-title"
    >
      <div className="max-w-measure">
        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-turquoise-700">
          DBaaS académico · agent-first
        </p>
        <h1
          id="landing-hero-title"
          className="mt-4 font-display text-[1.75rem] font-semibold leading-tight tracking-tight text-ink sm:mt-5 sm:text-4xl lg:text-[40px] lg:leading-[44px]"
          data-testid="landing-what-is"
        >
          {LANDING_WHAT_IS}
        </h1>
        <p className="mt-5 max-w-measure text-base leading-7 text-ink-muted sm:mt-6 sm:text-lg sm:leading-8">
          {LANDING_HERO_SUPPORT}
        </p>

        <blockquote className="mt-8 border-l-4 border-koi pl-5 sm:mt-10 sm:pl-6">
          <p className="font-display text-xl font-semibold leading-snug text-ink sm:text-2xl sm:leading-snug">
            {LANDING_THESIS}
          </p>
        </blockquote>

        <div className="mt-8 flex flex-col gap-3 sm:mt-10 sm:flex-row sm:flex-wrap sm:items-center sm:gap-4">
          <Link
            to="/register"
            className="inline-flex min-h-11 items-center justify-center rounded-sm bg-turquoise-700 px-5 py-3 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 focus-visible:outline-none focus-visible:shadow-focus"
            data-testid="landing-hero-signup"
          >
            Crear cuenta
          </Link>
          <a
            href="#como-funciona"
            className="inline-flex min-h-11 items-center justify-center rounded-sm border border-line-control bg-paper px-5 py-3 text-sm font-medium text-ink transition-colors duration-instant hover:border-turquoise-700 hover:text-turquoise-700 focus-visible:outline-none focus-visible:shadow-focus"
          >
            Cómo funciona
          </a>
        </div>
      </div>

      <div
        className="pond-water-hero relative h-52 w-full overflow-hidden rounded-lg border border-line shadow-print sm:h-[300px] lg:h-[340px]"
        role="img"
        aria-label="Estanque de peces koi"
      >
        <i
          className="koi--x2 pointer-events-none absolute"
          style={{ left: "10%", top: "36%" }}
          aria-hidden="true"
        />
        <i
          className="koi pointer-events-none absolute"
          style={{ left: "54%", top: "12%", animationDelay: "-11s" }}
          aria-hidden="true"
        />
        <i
          className="koi pointer-events-none absolute"
          style={{ left: "78%", top: "42%", animationDelay: "-19s" }}
          aria-hidden="true"
        />
      </div>
    </section>
  );
}
