import { Link } from "react-router-dom";
import { DataStateEmpty } from "@/components/data-state";

export function NotFoundPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-content items-center overflow-x-hidden px-4 py-8 lg:px-8">
      <div className="w-full">
        <p className="mb-3 text-center text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
          404
        </p>
        <DataStateEmpty
          pondSize="notFound"
          title="Esta parte del estanque está vacía."
          description="La ruta no tiene una pantalla o el enlace no pertenece al alcance actual."
          action={
            <>
              <Link
                className="inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
                to="/app"
              >
                Ir al dashboard
              </Link>
              <Link
                className="inline-flex h-9 items-center rounded-sm border border-line-control bg-paper px-4 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
                to="/"
              >
                Volver al inicio
              </Link>
            </>
          }
        />
      </div>
    </main>
  );
}
