import { Link } from "react-router-dom";
import { FINAL_CTA } from "@/features/landing/landing-copy";

export function LandingFinalCta() {
  return (
    <section
      id="cta-final"
      className="rounded-md border border-turquoise-700 bg-turquoise-100 px-5 py-8 text-center sm:px-8"
    >
      <h2 className="font-display text-2xl font-semibold text-ink sm:text-[28px] sm:leading-[34px]">
        {FINAL_CTA.title}
      </h2>
      <p className="mx-auto mt-3 max-w-measure text-sm leading-6 text-ink-muted">{FINAL_CTA.body}</p>
      <div className="mt-6 flex flex-col items-stretch justify-center gap-3 sm:flex-row sm:items-center">
        <Link
          to="/register"
          className="inline-flex min-h-11 items-center justify-center rounded-sm bg-turquoise-700 px-6 py-3 text-sm font-medium text-bone-raised transition-colors duration-instant hover:bg-turquoise-900 focus-visible:outline-none focus-visible:shadow-focus"
        >
          Crear cuenta
        </Link>
        <Link
          to="/login"
          className="inline-flex min-h-11 items-center justify-center rounded-sm border border-line-control bg-paper px-6 py-3 text-sm font-medium text-ink transition-colors duration-instant hover:border-turquoise-700 hover:text-turquoise-700 focus-visible:outline-none focus-visible:shadow-focus"
        >
          Iniciar sesión
        </Link>
      </div>
    </section>
  );
}
