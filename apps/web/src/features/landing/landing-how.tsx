import { HOW_IT_WORKS } from "@/features/landing/landing-copy";

export function LandingHow() {
  return (
    <section id="como-funciona" className="space-y-5">
      <div className="border-t-2 border-green-700 pt-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
          Cómo funciona
        </h2>
        <p className="mt-2 max-w-measure text-sm text-ink-muted">
          Tres pasos. Sin cuenta de cloud compleja ni facturación real.
        </p>
      </div>

      <ol className="grid list-none gap-4 md:grid-cols-3">
        {HOW_IT_WORKS.map((item) => (
          <li
            key={item.step}
            className={`rounded-b-sm border-x border-b border-t-4 border-line bg-bone-raised p-5 shadow-print ${item.band}`}
          >
            <p className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
              {item.step}
            </p>
            <h3 className="mt-2 font-display text-xl font-semibold text-ink">{item.title}</h3>
            <p className="mt-2 text-sm leading-6 text-ink-muted">{item.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
