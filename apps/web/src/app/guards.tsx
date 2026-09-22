import { Navigate, Outlet, useLocation } from "react-router-dom";
import { hasRole, useAuthStore } from "@/lib/auth-store";

export function RequireAuth() {
  const location = useLocation();
  const session = useAuthStore((state) => state.session);

  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export function RequireAdmin() {
  const session = useAuthStore((state) => state.session);

  if (!hasRole(session?.user, "admin")) {
    return <Navigate to="/app" replace />;
  }

  return <Outlet />;
}

export function PublicOnly() {
  const session = useAuthStore((state) => state.session);

  if (session) {
    return <Navigate to="/app" replace />;
  }

  return <Outlet />;
}
