import { Link, useParams } from "react-router-dom";
import { PlaceholderPage } from "@/components/placeholder-page";

interface AuthScaffoldProps {
  title: string;
  description: string;
  route: string;
  ticket: string;
  actionLabel: string;
}

function AuthScaffoldPage({
  title,
  description,
  route,
  ticket,
  actionLabel,
}: AuthScaffoldProps) {
  return (
    <main className="mx-auto flex min-h-screen max-w-form items-center px-4 py-8">
      <section className="w-full rounded-md border border-line bg-bone-raised p-6 shadow-print">
        <div className="space-y-2 border-b border-line pb-4">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            {ticket}
          </p>
          <h1 className="font-display text-4xl text-ink">{title}</h1>
          <p className="text-sm leading-6 text-ink-muted">{description}</p>
        </div>

        <form className="mt-5 space-y-4">
          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink-muted">Correo</span>
            <input
              className="h-10 w-full rounded-sm border border-line-control bg-paper px-3 text-ink"
              placeholder="demo@koicloud.dev"
              type="email"
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-ink-muted">Contraseña</span>
            <input
              className="h-10 w-full rounded-sm border border-line-control bg-paper px-3 text-ink"
              placeholder="••••••••"
              type="password"
            />
          </label>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
            <code className="rounded-sm border border-line bg-paper px-3 py-2 font-mono text-sm text-ink">
              {route}
            </code>
            <button
              className="rounded-sm bg-turquoise-700 px-4 py-2 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
              type="button"
            >
              {actionLabel}
            </button>
          </div>
        </form>

        <div className="mt-5 flex flex-wrap gap-3 text-sm text-ink-muted">
          <Link to="/forgot">Recuperar contraseña</Link>
          <span>·</span>
          <Link to="/register">Crear cuenta</Link>
          <span>·</span>
          <Link to="/">Volver al inicio</Link>
        </div>
      </section>
    </main>
  );
}

function usePondRouteLabel(suffix?: string) {
  const { pondId } = useParams();
  return pondId ? `/app/ponds/${pondId}${suffix ?? ""}` : "/app/ponds/:pondId";
}

export function LoginPage() {
  return (
    <AuthScaffoldPage
      actionLabel="Entrar"
      description="Skeleton de login listo para conectarse a /auth/login y al refresh automático."
      route="/login"
      ticket="W2-01"
      title="Iniciar sesión"
    />
  );
}

export function RegisterPage() {
  return (
    <AuthScaffoldPage
      actionLabel="Registrar cuenta"
      description="Base visual para registro, verificación y cableado de errores por code."
      route="/register"
      ticket="W2-01"
      title="Crear cuenta"
    />
  );
}

export function ForgotPage() {
  return (
    <AuthScaffoldPage
      actionLabel="Enviar enlace"
      description="Placeholder del flujo de recuperación de contraseña."
      route="/forgot"
      ticket="W2-02"
      title="Recuperar acceso"
    />
  );
}

export function VerifyPage() {
  return (
    <PlaceholderPage
      description="Pantalla placeholder para verificación de correo y consumo del token de registro."
      route="/verify"
      ticket="W2-01"
      title="Verificar correo"
    />
  );
}

export function ResetPage() {
  return (
    <PlaceholderPage
      description="Pantalla placeholder para reestablecer la contraseña con token ya validado."
      route="/reset"
      ticket="W2-02"
      title="Restablecer contraseña"
    />
  );
}

export function DashboardPage() {
  return (
    <PlaceholderPage
      description="Entrada principal del usuario autenticado con KPIs y la tabla de ponds por construir."
      route="/app"
      ticket="W2-04"
      title="Ponds"
    >
      <div className="grid gap-3 md:grid-cols-3">
        {[
          ["Ponds activos", "3"],
          ["Plan actual", "Micro"],
          ["Uso del mes", "42 h"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-line bg-paper p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
              {label}
            </p>
            <p className="font-display text-4xl text-ink">{value}</p>
          </div>
        ))}
      </div>
    </PlaceholderPage>
  );
}

export function CreatePondPage() {
  return (
    <PlaceholderPage
      description="Base para el modal o página de creación del pond con validación y submit real."
      route="/app/ponds/new"
      ticket="W2-05"
      title="Crear pond"
    />
  );
}

export function PondDetailPage() {
  return (
    <PlaceholderPage
      description="Detalle scaffolded del pond con espacio para resumen, conexión, SQL, respaldos y uso."
      route={usePondRouteLabel()}
      ticket="W2-06"
      title="Detalle del pond"
    />
  );
}

export function SqlConsolePage() {
  return (
    <PlaceholderPage
      description="Skeleton para consola SQL con editor, resultados y guardas de modo lectura/escritura."
      route={usePondRouteLabel("/console")}
      ticket="W2-07"
      title="Consola SQL"
    />
  );
}

export function BackupsPage() {
  return (
    <PlaceholderPage
      description="Lista placeholder de respaldos y restauraciones del pond activo."
      route={usePondRouteLabel("/backups")}
      ticket="W2-08"
      title="Respaldos"
    />
  );
}

export function PlansPage() {
  return (
    <PlaceholderPage
      description="Catálogo de planes conectado al endpoint público /plans."
      route="/app/plans"
      ticket="W2-03"
      title="Planes"
    />
  );
}

export function BillingPage() {
  return (
    <PlaceholderPage
      description="Placeholder para facturación e historial de invoices del usuario."
      route="/app/billing"
      ticket="W2-09"
      title="Facturación"
    />
  );
}

export function UsagePage() {
  return (
    <PlaceholderPage
      description="Vista base para el uso mensual, gráficas y totales agregados."
      route="/app/usage"
      ticket="W2-09"
      title="Uso del mes"
    />
  );
}

export function AccountPage() {
  return (
    <PlaceholderPage
      description="Scaffold de perfil para nombre, NIT y cambios de contraseña."
      route="/app/account"
      ticket="E1-05"
      title="Cuenta"
    />
  );
}

export function AgentAccessPage() {
  return (
    <PlaceholderPage
      description="Ruta lista para revelar la URL MCP, mostrar el slug y rotar la contraseña."
      route="/app/agent-access"
      ticket="W2-11"
      title="Acceso agente"
    />
  );
}

export function AdminUsersPage() {
  return (
    <PlaceholderPage
      description="Tabla administrativa base para usuarios, suspensión y reactivación."
      route="/app/admin/users"
      ticket="W2-10"
      title="Usuarios"
    />
  );
}

export function AdminSubscriptionsPage() {
  return (
    <PlaceholderPage
      description="Placeholder del historial administrativo de suscripciones."
      route="/app/admin/subscriptions"
      ticket="W2-10"
      title="Suscripciones"
    />
  );
}

export function AdminPondsPage() {
  return (
    <PlaceholderPage
      description="Vista base para la tabla administrativa de ponds."
      route="/app/admin/ponds"
      ticket="W2-10"
      title="Ponds"
    />
  );
}

export function AdminAuditPage() {
  return (
    <PlaceholderPage
      description="Bitácora administrativa placeholder para eventos sensibles."
      route="/app/admin/audit"
      ticket="W2-10"
      title="Bitácora"
    />
  );
}
