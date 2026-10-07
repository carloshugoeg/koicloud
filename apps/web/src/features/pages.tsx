import { useParams } from "react-router-dom";
import { usePondsQuery } from "@/api/hooks";
import { PlaceholderPage } from "@/components/placeholder-page";

export { LoginPage } from "@/features/auth/login-page";
export { RegisterPage } from "@/features/auth/register-page";
export { VerifyPage } from "@/features/auth/verify-page";
export { ForgotPage } from "@/features/auth/forgot-page";
export { ResetPage } from "@/features/auth/reset-page";
export { PlansPage } from "@/features/plans/plans-page";

function usePondRouteLabel(suffix?: string) {
  const { pondId } = useParams();
  return pondId ? `/app/ponds/${pondId}${suffix ?? ""}` : "/app/ponds/:pondId";
}

export function DashboardPage() {
  const { data: ponds, isPending, isError } = usePondsQuery();
  const pondsValue = isPending ? "…" : isError ? "—" : String(ponds?.length ?? 0);

  return (
    <PlaceholderPage
      description="Scaffold W2-04. Los KPI inventados salieron: ponds viene de GET /ponds; plan y uso esperan endpoints reales."
      route="/app"
      ticket="W2-04"
      title="Ponds"
    >
      <div className="grid gap-3 md:grid-cols-3">
        {[
          ["Ponds", pondsValue],
          ["Plan actual", "—"],
          ["Uso del mes", "—"],
        ].map(([label, value]) => (
          <div key={label} className="rounded-md border border-line bg-paper p-4">
            <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
              {label}
            </p>
            <p className="font-display text-4xl text-ink">{value}</p>
          </div>
        ))}
      </div>
      {!isPending && !isError && (ponds?.length ?? 0) === 0 ? (
        <p className="mt-4 text-sm leading-6 text-ink-muted">
          Todavía no tenés ponds. Creá el primero cuando W2-05 conecte el formulario.
        </p>
      ) : null}
      {isError ? (
        <p className="mt-4 text-sm leading-6 text-ink-muted">
          No se pudo cargar GET /ponds. Revisá la sesión o el API.
        </p>
      ) : null}
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
