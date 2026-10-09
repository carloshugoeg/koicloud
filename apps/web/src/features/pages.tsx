import { Navigate, useParams } from "react-router-dom";
import { PlaceholderPage } from "@/components/placeholder-page";

export { LoginPage } from "@/features/auth/login-page";
export { RegisterPage } from "@/features/auth/register-page";
export { VerifyPage } from "@/features/auth/verify-page";
export { ForgotPage } from "@/features/auth/forgot-page";
export { ResetPage } from "@/features/auth/reset-page";
export { DashboardPage } from "@/features/ponds/dashboard-page";
export { BackupsPage } from "@/features/ponds/backups-page";
export { PondDetailPage } from "@/features/ponds/detail-page";
export { CreatePondPage } from "@/features/ponds/create-page";

function usePondRouteLabel(suffix?: string) {
  const { pondId } = useParams();
  return pondId ? `/app/ponds/${pondId}${suffix ?? ""}` : "/app/ponds/:pondId";
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

export { UsoPage, UsoPage as BillingPage } from "@/features/uso/uso-page";

export function UsagePage() {
  return <Navigate replace to="/app/uso" />;
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
