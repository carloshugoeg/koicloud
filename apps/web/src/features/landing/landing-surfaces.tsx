import { OPERATE_WAYS } from "@/features/landing/landing-copy";

export function LandingSurfaces() {
  return (
    <section id="superficies" className="space-y-8">
      <div className="border-t-2 border-turquoise-700 pt-6 sm:pt-8">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
          Tres formas de operarlo
        </h2>
        <p className="mt-3 max-w-measure text-base leading-7 text-ink-muted">
          Una sola API. La UI, la CLI y los agentes llaman a los mismos comandos.
        </p>
      </div>

      <ul className="grid list-none gap-6 md:grid-cols-3 md:gap-8">
        {OPERATE_WAYS.map((way) => (
          <li
            key={way.title}
            className={`rounded-b-sm border-x border-b border-t-4 border-line bg-paper p-6 ${way.accent}`}
          >
            <h3 className="font-display text-xl font-semibold text-ink">{way.title}</h3>
            <p className="mt-3 text-sm leading-7 text-ink-muted">{way.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
