import { expect, type Page, type Route } from "@playwright/test";

export type Role = "client" | "admin";

const POND_ID = "66666666-6666-6666-6666-666666666666";

let sessionRole: Role = "client";

const pond = {
  id: POND_ID,
  name: "inventario-demo",
  engine_version: "16",
  plan_id: "micro",
  node_id: "node-sv-01",
  host_port: 15007,
  user_id: "11111111-1111-1111-1111-111111111111",
  size_bytes: 124901,
  healthy: true,
  created_at: "2026-09-22T20:00:00Z",
  desired_state: "running",
  observed_state: "running",
  last_restore_at: null,
};

const backup = {
  id: "88888888-8888-8888-8888-888888888888",
  pond_id: POND_ID,
  kind: "daily",
  status: "succeeded",
  size_bytes: 124901,
  sha256: "1f3e7d3ab148b8be24af9b97a10d1655db8c613de0dc02f88f752230ec7776d0",
  storage_path: "/var/lib/koicloud/backups/inventario-demo/20260922.dump",
  created_at: "2026-09-22T20:00:00Z",
  completed_at: "2026-09-22T20:00:00Z",
  expires_at: "2026-09-29T20:00:00Z",
};

const plans = [
  {
    id: "sandbox",
    name: "Sandbox",
    description: "1 pond, 1 GB, validez corta",
    active: true,
    billing_model: "hourly",
    currency: "USD",
    max_ponds: 1,
    max_storage_gb: 1,
    postpaid: false,
    price_monthly_usd: 0,
    unit_price: 0,
    validity_minutes: 10,
  },
  {
    id: "micro",
    name: "Micro",
    description: "1 pond, 1 GB, backups 7 días",
    active: true,
    billing_model: "monthly",
    currency: "USD",
    max_ponds: 1,
    max_storage_gb: 1,
    postpaid: false,
    price_monthly_usd: 5,
    unit_price: 5,
    validity_minutes: 43200,
  },
  {
    id: "pro",
    name: "Pro",
    description: "Hasta 10 ponds y 20 GB",
    active: true,
    billing_model: "hourly",
    currency: "USD",
    max_ponds: 10,
    max_storage_gb: 20,
    postpaid: true,
    price_monthly_usd: 0,
    unit_price: 0.02,
    validity_minutes: 43200,
  },
];

const adminUsers = [
  {
    id: "33333333-3333-3333-3333-333333333333",
    email: "ana@koicloud.dev",
    full_name: "Ana Activa",
    role: "client",
    status: "active",
    email_verified: true,
    active_subscription_plan: "micro",
    created_at: "2026-09-22T20:00:00Z",
  },
  {
    id: "44444444-4444-4444-4444-444444444444",
    email: "luis@koicloud.dev",
    full_name: "Luis Suspendido",
    role: "client",
    status: "suspended",
    email_verified: true,
    active_subscription_plan: "micro",
    created_at: "2026-09-22T20:00:00Z",
  },
];

function sessionUser(role: Role) {
  if (role === "admin") {
    return {
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      email: "admin@koicloud.dev",
      full_name: "Admin Gate",
      role: "admin",
      status: "active",
      email_verified: true,
      nit: "0614-220999-101-3",
      created_at: "2026-09-22T20:00:00Z",
    };
  }
  return {
    id: "11111111-1111-1111-1111-111111111111",
    email: "demo@koicloud.dev",
    full_name: "Operador Demo",
    role: "client",
    status: "active",
    email_verified: true,
    nit: "0614-220999-101-3",
    created_at: "2026-09-22T20:00:00Z",
  };
}

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

export async function installApi(page: Page) {
  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const { pathname } = url;
    const method = request.method();
    const user = sessionUser(sessionRole);

    if (method === "POST" && pathname.endsWith("/auth/login")) {
      return json(route, 200, {
        access_token: "access_e2e",
        refresh_token: "refresh_e2e",
        user,
      });
    }
    if (method === "GET" && pathname.endsWith("/me")) {
      return json(route, 200, { user, ponds_count: 1, subscription: null });
    }
    if (method === "GET" && pathname.endsWith("/plans")) {
      return json(route, 200, { plans });
    }
    if (method === "GET" && pathname.endsWith("/usage")) {
      return json(route, 200, {
        month: "2026-10",
        ponds: [],
        total_instance_hours: 0,
        total_storage_gb_hours: 0,
      });
    }
    if (method === "GET" && pathname.endsWith("/admin/users")) {
      return json(route, 200, { users: adminUsers, next_cursor: null });
    }
    if (method === "GET" && pathname.endsWith("/admin/ponds")) {
      return json(route, 200, { ponds: [], next_cursor: null });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}/backups`)) {
      return json(route, 200, { backups: [backup] });
    }
    if (method === "GET" && pathname.endsWith(`/ponds/${POND_ID}`)) {
      return json(route, 200, { pond });
    }
    if (method === "GET" && pathname.endsWith("/ponds")) {
      return json(route, 200, { ponds: [pond] });
    }
    if (pathname.includes("/confirm/")) {
      return json(route, 200, {});
    }
    return json(route, 404, { code: "not_found", message: pathname, request_id: "e2e" });
  });
}

export async function login(page: Page, role: Role) {
  sessionRole = role;
  const user = sessionUser(role);
  await page.goto("/login");
  await page.getByLabel("Correo").fill(user.email);
  await page.getByLabel("Contraseña").fill("Sup3rSegura!2026");
  await page.getByRole("button", { name: "Iniciar sesión" }).click();
  await expect(page).toHaveURL(/\/app$/);
}
