import { createBrowserRouter, type RouteObject } from "react-router-dom";
import { RequireAdmin, RequireAuth, PublicOnly } from "@/app/guards";
import { AppShell } from "@/app/layout/app-shell";
import { NotFoundPage } from "@/app/not-found-page";
import { LandingPage } from "@/features/landing/landing-page";
import {
  AccountPage,
  AdminAuditPage,
  AdminPondsPage,
  AdminSubscriptionsPage,
  AdminUsersPage,
  AgentAccessPage,
  BackupsPage,
  BillingPage,
  CreatePondPage,
  DashboardPage,
  ForgotPage,
  LoginPage,
  PlansPage,
  PondDetailPage,
  RegisterPage,
  ResetPage,
  SqlConsolePage,
  UsagePage,
  VerifyPage,
} from "@/features/pages";

export interface RouteHandle {
  title: string;
}

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <LandingPage />,
    handle: { title: "Inicio" } satisfies RouteHandle,
  },
  {
    element: <PublicOnly />,
    children: [
      {
        path: "/login",
        element: <LoginPage />,
        handle: { title: "Iniciar sesión" } satisfies RouteHandle,
      },
      {
        path: "/register",
        element: <RegisterPage />,
        handle: { title: "Crear cuenta" } satisfies RouteHandle,
      },
      {
        path: "/forgot",
        element: <ForgotPage />,
        handle: { title: "Recuperar acceso" } satisfies RouteHandle,
      },
    ],
  },
  {
    path: "/verify",
    element: <VerifyPage />,
    handle: { title: "Verificar correo" } satisfies RouteHandle,
  },
  {
    path: "/reset",
    element: <ResetPage />,
    handle: { title: "Restablecer contraseña" } satisfies RouteHandle,
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/app",
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
            handle: { title: "Ponds" } satisfies RouteHandle,
          },
          {
            path: "ponds/new",
            element: <CreatePondPage />,
            handle: { title: "Crear pond" } satisfies RouteHandle,
          },
          {
            path: "ponds/:pondId",
            element: <PondDetailPage />,
            handle: { title: "Detalle del pond" } satisfies RouteHandle,
          },
          {
            path: "ponds/:pondId/console",
            element: <SqlConsolePage />,
            handle: { title: "Consola SQL" } satisfies RouteHandle,
          },
          {
            path: "ponds/:pondId/backups",
            element: <BackupsPage />,
            handle: { title: "Respaldos" } satisfies RouteHandle,
          },
          {
            path: "plans",
            element: <PlansPage />,
            handle: { title: "Planes" } satisfies RouteHandle,
          },
          {
            path: "planes",
            element: <PlansPage />,
            handle: { title: "Planes" } satisfies RouteHandle,
          },
          {
            path: "billing",
            element: <BillingPage />,
            handle: { title: "Facturación" } satisfies RouteHandle,
          },
          {
            path: "usage",
            element: <UsagePage />,
            handle: { title: "Uso del mes" } satisfies RouteHandle,
          },
          {
            path: "agent-access",
            element: <AgentAccessPage />,
            handle: { title: "Acceso agente" } satisfies RouteHandle,
          },
          {
            path: "account",
            element: <AccountPage />,
            handle: { title: "Cuenta" } satisfies RouteHandle,
          },
          {
            element: <RequireAdmin />,
            children: [
              {
                path: "admin/users",
                element: <AdminUsersPage />,
                handle: { title: "Usuarios" } satisfies RouteHandle,
              },
              {
                path: "admin/subscriptions",
                element: <AdminSubscriptionsPage />,
                handle: { title: "Suscripciones" } satisfies RouteHandle,
              },
              {
                path: "admin/ponds",
                element: <AdminPondsPage />,
                handle: { title: "Ponds" } satisfies RouteHandle,
              },
              {
                path: "admin/audit",
                element: <AdminAuditPage />,
                handle: { title: "Bitácora" } satisfies RouteHandle,
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "*",
    element: <NotFoundPage />,
    handle: { title: "No encontrado" } satisfies RouteHandle,
  },
];

export function createAppRouter() {
  return createBrowserRouter(appRoutes);
}
