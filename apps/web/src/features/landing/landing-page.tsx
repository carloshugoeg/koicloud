import { Link } from "react-router-dom";

const planCards = [
  {
    name: "Sandbox",
    detail: "Espacio de pruebas contra mocks y contratos generados.",
    tone: "border-turquoise-700",
  },
  {
    name: "Micro",
    detail: "Plan base de la demo: un pond real y consumo controlado.",
    tone: "border-green-700",
  },
  {
    name: "Pro",
    detail: "Capacidad ampliada para la administración y el agente.",
    tone: "border-marigold",
  },
];

export function LandingPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-content flex-col gap-10 px-4 py-8 lg:px-8">
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-line pb-5">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Equipo KoiCloud
          </p>
          <h1 className="font-display text-5xl text-ink">KoiCloud</h1>
        </div>
        <nav className="flex flex-wrap items-center gap-3">
          <Link
            className="rounded-sm border border-line-control bg-bone-raised px-4 py-2 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
            to="/login"
          >
            Iniciar sesión
          </Link>
          <Link
            className="rounded-sm bg-turquoise-700 px-4 py-2 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
            to="/register"
          >
            Crear cuenta
          </Link>
        </nav>
      </header>

      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <article className="space-y-4 rounded-md border border-line bg-bone-raised p-6">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Scaffold fase 0
          </p>
          <h2 className="font-display text-5xl leading-tight text-ink">
            Un panel editorial y denso para operar ponds de PostgreSQL.
          </h2>
          <p className="max-w-measure text-base leading-7 text-ink-muted">
            Esta base deja listas las rutas, el shell, la tipografía,
            el cliente API y los placeholders principales para que W2 pueda
            construir pantallas reales sin inventar contrato ni paleta.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              className="rounded-sm bg-turquoise-700 px-4 py-2 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
              to="/app"
            >
              Entrar al dashboard
            </Link>
            <Link
              className="rounded-sm border border-line-control bg-paper px-4 py-2 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
              to="/app/plans"
            >
              Ver planes
            </Link>
          </div>
        </article>

        <aside className="rounded-md border border-line bg-paper p-6">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Piel base
          </p>
          <div className="mt-4 space-y-3">
            <div className="h-8 rounded-sm border border-line bg-bone" />
            <div className="h-24 rounded-md border border-line bg-bone-raised" />
            <div className="grid grid-cols-2 gap-3">
              <div className="h-20 rounded-md border border-line bg-turquoise-100" />
              <div className="h-20 rounded-md border border-line bg-green-100" />
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-ink-muted">
            Los tokens salen de <code className="font-mono">src/index.css</code>;
            esta vista solo demuestra la dirección visual del scaffold.
          </p>
        </aside>
      </section>

      <section className="space-y-4">
        <div className="border-t-4 border-turquoise-700 pt-3">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            Planes
          </p>
        </div>

        <div className="grid gap-4 lg:grid-cols-3">
          {planCards.map((plan) => (
            <article
              key={plan.name}
              className={`rounded-md border border-line bg-bone-raised p-5 ${plan.tone}`}
            >
              <h3 className="font-display text-3xl text-ink">{plan.name}</h3>
              <p className="mt-3 text-sm leading-6 text-ink-muted">
                {plan.detail}
              </p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
