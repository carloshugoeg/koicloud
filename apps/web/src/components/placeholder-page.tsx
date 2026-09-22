import type { ReactNode } from "react";

interface PlaceholderPageProps {
  title: string;
  description: string;
  route: string;
  ticket: string;
  children?: ReactNode;
}

export function PlaceholderPage({
  title,
  description,
  route,
  ticket,
  children,
}: PlaceholderPageProps) {
  return (
    <section className="space-y-6">
      <header className="space-y-3 border-b border-line pb-4">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
          {ticket}
        </p>
        <div className="space-y-2">
          <h2 className="font-display text-4xl text-ink">{title}</h2>
          <p className="max-w-measure text-base leading-7 text-ink-muted">
            {description}
          </p>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(18rem,1fr)]">
        <article className="rounded-md border border-line bg-bone-raised p-5">
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
              Ruta registrada
            </p>
            <code className="block rounded-sm border border-line bg-paper px-3 py-2 font-mono text-sm text-ink">
              {route}
            </code>
          </div>

          <div className="mt-5 space-y-3">
            <p className="text-sm font-medium text-ink">Listo para conectar</p>
            <ul className="space-y-2 text-sm leading-6 text-ink-muted">
              <li>Guard y layout reales ya montados.</li>
              <li>Tokens visuales y tipografías aplicados al shell.</li>
              <li>Store de auth, cliente API y mocks base disponibles.</li>
            </ul>
          </div>

          {children ? <div className="mt-5">{children}</div> : null}
        </article>

        <aside className="rounded-md border border-line bg-paper p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Próximo paso
          </p>
          <p className="mt-3 text-sm leading-6 text-ink-muted">
            Reemplazá este placeholder por la pantalla definitiva usando los
            datos del OpenAPI y los handlers de MSW. El scaffold conserva la
            ruta, el chrome y el catálogo de errores.
          </p>
        </aside>
      </div>
    </section>
  );
}
