import { FAQ_ITEMS } from "@/features/landing/landing-copy";

export function LandingFaq() {
  return (
    <section id="faq" className="space-y-5">
      <div className="border-t-2 border-line pt-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
          Preguntas honestas
        </h2>
        <p className="mt-2 max-w-measure text-sm text-ink-muted">
          Lo que sí hacemos y lo que no prometemos.
        </p>
      </div>

      <dl className="space-y-4">
        {FAQ_ITEMS.map((item) => (
          <div
            key={item.q}
            className="rounded-md border border-line bg-bone-raised px-4 py-4 sm:px-5"
          >
            <dt className="font-display text-xl font-semibold text-ink">{item.q}</dt>
            <dd className="mt-2 text-sm leading-6 text-ink-muted">{item.a}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
