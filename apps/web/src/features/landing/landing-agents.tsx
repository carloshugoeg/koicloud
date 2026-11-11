import { AGENT_POINTS } from "@/features/landing/landing-copy";

export function LandingAgents() {
  return (
    <section id="agentes" className="space-y-5">
      <div className="border-t-2 border-koi pt-3">
        <h2 className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
          Hecho para agentes
        </h2>
        <p className="mt-2 max-w-measure text-sm text-ink-muted">
          Si usas Claude Code u otro agente con MCP, KoiCloud es un Postgres que el agente
          puede operar con límites claros.
        </p>
      </div>

      <ul className="grid list-none gap-4 md:grid-cols-3">
        {AGENT_POINTS.map((point) => (
          <li
            key={point.title}
            className="rounded-md border border-line bg-bone-raised p-5 shadow-print"
          >
            <h3 className="font-display text-xl font-semibold text-ink">{point.title}</h3>
            <p className="mt-2 text-sm leading-6 text-ink-muted">{point.body}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
