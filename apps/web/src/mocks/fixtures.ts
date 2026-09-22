import type { components } from "@/api/schema";

type User = components["schemas"]["UserOut"];
type AdminUser = components["schemas"]["AdminUserOut"];
type Plan = components["schemas"]["PlanOut"];
type Pond = components["schemas"]["PondOut"];
type Backup = components["schemas"]["BackupOut"];
type Usage = components["schemas"]["UsageResponse"];
type AgentAccess = components["schemas"]["AgentAccessOut"];
type PondConnection = components["schemas"]["ConnectionOut"];

export const demoUser: User = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "demo@koicloud.dev",
  full_name: "Operador Demo",
  role: "client",
  status: "active",
  email_verified: true,
  nit: "0614-220999-101-3",
  created_at: "2026-09-22T20:00:00Z",
};

export const adminUser: AdminUser = {
  id: "22222222-2222-2222-2222-222222222222",
  email: "admin@koicloud.dev",
  full_name: "Admin Demo",
  role: "admin",
  status: "active",
  email_verified: true,
  active_subscription_plan: "pro",
  created_at: "2026-09-22T20:00:00Z",
};

export const fixtures = {
  session: {
    access_token: "access_demo_token",
    refresh_token: "refresh_demo_token",
    user: demoUser,
  } satisfies components["schemas"]["LoginResponse"],
  refreshed: {
    access_token: "access_refreshed_token",
    refresh_token: "refresh_refreshed_token",
  } satisfies components["schemas"]["TokenPairResponse"],
  plans: [
    {
      active: true,
      description: "Pruebas internas (10 min)",
      id: "sandbox",
      max_ponds: 1,
      max_storage_gb: 1,
      name: "Sandbox",
      postpaid: false,
      price_monthly_usd: 0,
      validity_minutes: 10,
    },
    {
      active: true,
      description: "1 pond, 1 GB, backups 7 días",
      id: "micro",
      max_ponds: 1,
      max_storage_gb: 1,
      name: "Micro",
      postpaid: false,
      price_monthly_usd: 5,
      validity_minutes: 43_200,
    },
    {
      active: true,
      description: "Hasta 10 ponds, post-pago por uso",
      id: "pro",
      max_ponds: 10,
      max_storage_gb: 20,
      name: "Pro",
      postpaid: true,
      price_monthly_usd: 0,
      validity_minutes: 43_200,
    },
  ] satisfies Plan[],
  pond: {
    created_at: "2026-09-22T20:00:00Z",
    desired_state: "running",
    engine_version: "16",
    healthy: true,
    host_port: 15_007,
    id: "66666666-6666-6666-6666-666666666666",
    last_error: null,
    last_restore_at: null,
    name: "inventario-demo",
    node_id: "node-sv-01",
    observed_state: "running",
    plan_id: "micro",
    user_id: demoUser.id,
  } satisfies Pond,
  ponds: [
    {
      created_at: "2026-09-22T20:00:00Z",
      desired_state: "running",
      engine_version: "16",
      healthy: true,
      host_port: 15_007,
      id: "66666666-6666-6666-6666-666666666666",
      last_error: null,
      last_restore_at: null,
      name: "inventario-demo",
      node_id: "node-sv-01",
      observed_state: "running",
      plan_id: "micro",
      user_id: demoUser.id,
    },
    {
      created_at: "2026-09-22T20:00:00Z",
      desired_state: "running",
      engine_version: "16",
      healthy: true,
      host_port: 15_012,
      id: "77777777-7777-7777-7777-777777777777",
      last_error: null,
      last_restore_at: null,
      name: "reportes-demo",
      node_id: "node-sv-01",
      observed_state: "provisioning",
      plan_id: "micro",
      user_id: demoUser.id,
    },
  ] satisfies Pond[],
  connection: {
    database: "inventario_demo",
    host: "db.koicloud.dev",
    password: "p0nd-Temp!2026",
    port: 15_007,
    uri: "postgresql://koi_inventario:p0nd-Temp%212026@db.koicloud.dev:15007/inventario_demo",
    username: "koi_inventario",
  } satisfies PondConnection,
  backups: [
    {
      completed_at: "2026-09-22T20:00:00Z",
      created_at: "2026-09-22T20:00:00Z",
      id: "88888888-8888-8888-8888-888888888888",
      kind: "daily",
      pond_id: "66666666-6666-6666-6666-666666666666",
      sha256: "1f3e7d3ab148b8be24af9b97a10d1655db8c613de0dc02f88f752230ec7776d0",
      size_bytes: 124_901,
      status: "succeeded",
      storage_path: "/var/lib/koicloud/backups/inventario-demo/20260922.dump",
    },
    {
      completed_at: "2026-09-21T20:00:00Z",
      created_at: "2026-09-21T20:00:00Z",
      id: "99999999-9999-9999-9999-999999999999",
      kind: "pre_delete",
      pond_id: "66666666-6666-6666-6666-666666666666",
      sha256: "7f3e7d3ab148b8be24af9b97a10d1655db8c613de0dc02f88f752230ec7776d1",
      size_bytes: 126_532,
      status: "succeeded",
      storage_path: "/var/lib/koicloud/backups/inventario-demo/pre-delete.dump",
    },
  ] satisfies Backup[],
  usage: {
    month: "2026-09",
    ponds: [
      {
        pond_id: "66666666-6666-6666-6666-666666666666",
        pond_name: "inventario-demo",
        instance_hours: 124.5,
        storage_gb_hours: 31.2,
      },
    ],
    total_instance_hours: 124.5,
    total_storage_gb_hours: 31.2,
  } satisfies Usage,
  agentAccess: {
    slug: "demo-agent",
    url: "https://koicloud.local/mcp",
    enabled: true,
    rotated_at: "2026-09-22T20:00:00Z",
  } satisfies AgentAccess,
  adminUsers: [adminUser] satisfies AdminUser[],
};
