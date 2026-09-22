import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-content items-center px-4 py-8 lg:px-8">
      <section className="w-full rounded-md border border-line bg-bone-raised p-8 text-center shadow-print">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
          404
        </p>
        <h1 className="mt-3 font-display text-5xl text-ink">
          Esta parte del estanque está vacía.
        </h1>
        <p className="mx-auto mt-4 max-w-measure text-base leading-7 text-ink-muted">
          La ruta existe en el router, pero todavía no tiene una pantalla real
          o el enlace solicitado no pertenece al alcance actual.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <Link
            className="rounded-sm bg-turquoise-700 px-4 py-2 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
            to="/app"
          >
            Ir al dashboard
          </Link>
          <Link
            className="rounded-sm border border-line-control bg-paper px-4 py-2 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
            to="/"
          >
            Volver al inicio
          </Link>
        </div>
      </section>
    </main>
  );
}
