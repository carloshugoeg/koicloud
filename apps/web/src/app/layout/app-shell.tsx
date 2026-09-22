import { NavLink, Outlet, useMatches } from "react-router-dom";
import { useAuthStore } from "@/lib/auth-store";

const primaryLinks = [
  { to: "/app", label: "Ponds" },
  { to: "/app/plans", label: "Planes" },
  { to: "/app/usage", label: "Uso del mes" },
  { to: "/app/billing", label: "Facturación" },
  { to: "/app/agent-access", label: "Acceso agente" },
  { to: "/app/account", label: "Cuenta" },
];

const adminLinks = [
  { to: "/app/admin/users", label: "Usuarios" },
  { to: "/app/admin/subscriptions", label: "Suscripciones" },
  { to: "/app/admin/ponds", label: "Ponds" },
  { to: "/app/admin/audit", label: "Bitácora" },
];

function linkClassName(isActive: boolean) {
  return [
    "block rounded-sm border px-3 py-2 text-sm transition-colors duration-fast ease-brand-out",
    isActive
      ? "border-turquoise-700 bg-turquoise-100 text-turquoise-900"
      : "border-transparent text-ink hover:border-line-control hover:bg-bone",
  ].join(" ");
}

function readTitle(handle: unknown) {
  if (
    typeof handle === "object" &&
    handle !== null &&
    typeof (handle as { title?: unknown }).title === "string"
  ) {
    return (handle as { title: string }).title;
  }

  return "KoiCloud";
}

export function AppShell() {
  const session = useAuthStore((state) => state.session);
  const clearSession = useAuthStore((state) => state.clearSession);
  const matches = useMatches();
  const currentTitle = readTitle(matches[matches.length - 1]?.handle);

  return (
    <div className="min-h-screen bg-bone text-ink lg:grid" style={{ gridTemplateColumns: "var(--sidebar-w) 1fr" }}>
      <aside className="border-b border-line bg-bone-sunk px-4 py-5 lg:border-b-0 lg:border-r">
        <div className="space-y-1 border-b border-line pb-4">
          <p className="font-display text-3xl text-ink">KoiCloud</p>
          <p className="text-sm text-ink-muted">
            Scaffold base para W2 sobre el contrato congelado.
          </p>
        </div>

        <nav className="mt-5 space-y-6">
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
              Estanque
            </p>
            <div className="space-y-1">
              {primaryLinks.map((link) => (
                <NavLink key={link.to} className={({ isActive }) => linkClassName(isActive)} to={link.to}>
                  {link.label}
                </NavLink>
              ))}
            </div>
          </div>

          {session?.user.role === "admin" ? (
            <div className="space-y-2">
              <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
                Administración
              </p>
              <div className="space-y-1">
                {adminLinks.map((link) => (
                  <NavLink key={link.to} className={({ isActive }) => linkClassName(isActive)} to={link.to}>
                    {link.label}
                  </NavLink>
                ))}
              </div>
            </div>
          ) : null}
        </nav>
      </aside>

      <div className="min-w-0">
        <header
          className="flex flex-wrap items-center justify-between gap-4 border-b border-line bg-bone px-4 py-4 lg:px-8"
          style={{ minHeight: "var(--header-h)" }}
        >
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-ink-muted">
              Control plane
            </p>
            <h1 className="font-display text-3xl text-ink">{currentTitle}</h1>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm font-medium text-ink">
                {session?.user.full_name ?? "Operador"}
              </p>
              <p className="text-xs text-ink-muted">{session?.user.email}</p>
            </div>
            <button
              className="rounded-sm border border-line-control bg-bone-raised px-3 py-2 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700 hover:text-turquoise-700"
              onClick={clearSession}
              type="button"
            >
              Cerrar sesión
            </button>
          </div>
        </header>

        <main className="mx-auto max-w-content px-4 py-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
