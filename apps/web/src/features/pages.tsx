import { Navigate, useLocation } from "react-router-dom";
import { PlaceholderPage } from "@/components/placeholder-page";

export { LoginPage } from "@/features/auth/login-page";
export { RegisterPage } from "@/features/auth/register-page";
export { VerifyPage } from "@/features/auth/verify-page";
export { ForgotPage } from "@/features/auth/forgot-page";
export { ResetPage } from "@/features/auth/reset-page";
export { PlansPage } from "@/features/plans/plans-page";
export { DashboardPage } from "@/features/ponds/dashboard-page";
export { BackupsPage } from "@/features/ponds/backups-page";
export { PondDetailPage } from "@/features/ponds/detail-page";
export { CreatePondPage } from "@/features/ponds/create-page";

export { SqlConsolePage } from "@/features/sql-console/sql-console-page";

export { UsoPage, UsoPage as BillingPage } from "@/features/uso/uso-page";

export function UsagePage() {
  return <Navigate replace to="/app/uso" />;
}

export { AccountPage } from "@/features/account/account-page";

export { AgentAccessPage } from "@/features/agent-access/agent-access-page";

export function AgentAccessAliasPage() {
  return <Navigate replace to="/app/acceso-agente" />;
}

export { ConfirmPage } from "@/features/confirm/confirm-page";

export function ConfirmAliasPage() {
  const location = useLocation();
  return (
    <Navigate
      replace
      to={{ pathname: "/app/confirm", search: location.search }}
      state={location.state}
    />
  );
}

export { AdminUsersPage } from "@/features/admin/users-page";
export { AdminPondsPage } from "@/features/admin/ponds-page";
export { AdminAuditPage } from "@/features/admin/audit-page";

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
