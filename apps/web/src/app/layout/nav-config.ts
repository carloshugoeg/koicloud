export type NavIconName =
  | "ponds"
  | "create"
  | "usage"
  | "billing"
  | "plans"
  | "agent"
  | "account"
  | "users"
  | "subscriptions"
  | "adminPonds"
  | "audit";

export interface NavItem {
  to: string;
  label: string;
  icon: NavIconName;
  end?: boolean;
}

export interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
  adminOnly?: boolean;
}

/** Sidebar groups and order — visual-guidelines §5.1 */
export const navGroups: NavGroup[] = [
  {
    id: "estanque",
    label: "Estanque",
    items: [
      { to: "/app/ponds", label: "Ponds", icon: "ponds", end: true },
      { to: "/app/ponds/new", label: "Crear pond", icon: "create" },
    ],
  },
  {
    id: "consumo",
    label: "Consumo",
    items: [
      { to: "/app/uso", label: "Uso del mes", icon: "usage" },
      { to: "/app/billing", label: "Facturación", icon: "billing" },
      { to: "/app/plans", label: "Planes", icon: "plans" },
    ],
  },
  {
    id: "agente",
    label: "Agente",
    items: [{ to: "/app/acceso-agente", label: "Acceso agente", icon: "agent" }],
  },
  {
    id: "cuenta",
    label: "Cuenta",
    items: [{ to: "/app/account", label: "Perfil", icon: "account" }],
  },
  {
    id: "admin",
    label: "Administración",
    adminOnly: true,
    items: [
      { to: "/app/admin/users", label: "Usuarios", icon: "users" },
      { to: "/app/admin/subscriptions", label: "Suscripciones", icon: "subscriptions" },
      { to: "/app/admin/ponds", label: "Ponds", icon: "adminPonds" },
      { to: "/app/admin/audit", label: "Bitácora", icon: "audit" },
    ],
  },
];
