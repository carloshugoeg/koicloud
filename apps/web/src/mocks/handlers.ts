import { HttpResponse, http } from "msw";
import type { components } from "@/api/schema";
import { adminUser, fixtures } from "@/mocks/fixtures";

const API_ROOT = "*/api/v1";
const SUSPEND_CONFIRM_TEXT = "SUSPENDER";

type AgentAccessMock = {
  slug: string;
  url: string;
  enabled: boolean;
  rotated_at: string;
};

type AdminUser = components["schemas"]["AdminUserOut"];
type AuditEvent = components["schemas"]["AuditEventOut"];

function freshAgentAccess(): AgentAccessMock {
  return { ...fixtures.agentAccess };
}

function freshAdminUsers(): AdminUser[] {
  return fixtures.adminUsers.map((user) => ({ ...user }));
}

function freshAdminAudit(): AuditEvent[] {
  return fixtures.adminAuditEvents.map((event) => ({
    ...event,
    metadata: { ...event.metadata },
  }));
}

let agentAccessState = freshAgentAccess();
let adminUsersState = freshAdminUsers();
let adminAuditState = freshAdminAudit();

export const ROTATED_AGENT_PASSWORD = "rotated-once-secret";

export function resetAgentAccessState() {
  agentAccessState = freshAgentAccess();
}

export function resetAdminUsersState() {
  adminUsersState = freshAdminUsers();
  adminAuditState = freshAdminAudit();
}

export const handlers = [
  http.post(`${API_ROOT}/auth/register`, () => {
    return HttpResponse.json(
      {
        user_id: fixtures.session.user.id,
        email_verified: false,
      },
      { status: 201 },
    );
  }),

  http.post(`${API_ROOT}/auth/verify`, () => {
    return HttpResponse.json({
      user_id: fixtures.session.user.id,
      email_verified: true,
    });
  }),

  http.post(`${API_ROOT}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email?: string };
    // Preview/test-only admin seed (MSW). Never a real credential store.
    if (body.email?.trim().toLowerCase() === adminUser.email) {
      return HttpResponse.json({
        access_token: "access_admin_token",
        refresh_token: "refresh_admin_token",
        user: {
          id: adminUser.id,
          email: adminUser.email,
          full_name: adminUser.full_name,
          role: "admin" as const,
          status: adminUser.status,
          email_verified: true,
          nit: "0614-220999-101-3",
          created_at: adminUser.created_at,
        },
      });
    }
    return HttpResponse.json(fixtures.session);
  }),

  http.post(`${API_ROOT}/auth/forgot`, () => {
    return HttpResponse.json({ ok: true });
  }),

  http.post(`${API_ROOT}/auth/reset`, () => {
    return HttpResponse.json({ ok: true });
  }),

  http.post(`${API_ROOT}/auth/resend-verification`, () => {
    return HttpResponse.json({ ok: true }, { status: 202 });
  }),

  http.post(`${API_ROOT}/auth/refresh`, () => {
    return HttpResponse.json(fixtures.refreshed);
  }),

  http.get(`${API_ROOT}/plans`, () => {
    return HttpResponse.json({ plans: fixtures.plans, next_cursor: null });
  }),

  http.get(`${API_ROOT}/me`, () => {
    return HttpResponse.json({
      user: fixtures.session.user,
      ponds_count: fixtures.ponds.length,
      subscription: fixtures.subscriptionResponse.subscription,
    });
  }),

  http.patch(`${API_ROOT}/me`, async ({ request }) => {
    const body = (await request.json()) as {
      full_name?: string | null;
      nit?: string | null;
    };
    return HttpResponse.json({
      user: {
        ...fixtures.session.user,
        full_name: body.full_name ?? fixtures.session.user.full_name,
        nit: body.nit === undefined ? fixtures.session.user.nit : body.nit,
      },
    });
  }),

  http.post(`${API_ROOT}/me/change-password`, async ({ request }) => {
    const body = (await request.json()) as {
      current_password?: string;
      new_password?: string;
    };
    if ((body.new_password?.length ?? 0) < 10) {
      return HttpResponse.json(
        {
          code: "password_too_weak",
          message: "La contraseña no cumple los requisitos mínimos.",
          request_id: "req_pw_weak",
        },
        { status: 422 },
      );
    }
    if (body.current_password !== "Sup3rSegura!2026") {
      return HttpResponse.json(
        {
          code: "invalid_credentials",
          message: "Correo o contraseña incorrectos.",
          request_id: "req_pw_bad",
        },
        { status: 401 },
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.delete(`${API_ROOT}/me`, async ({ request }) => {
    const body = (await request.json()) as { confirm_email?: string };
    if (body.confirm_email !== fixtures.session.user.email) {
      return HttpResponse.json(
        {
          code: "email_mismatch",
          message: "El correo no coincide.",
          request_id: "req_email_mm",
        },
        { status: 422 },
      );
    }
    return HttpResponse.json({ ok: true }, { status: 202 });
  }),

  http.post(`${API_ROOT}/subscriptions`, async ({ request }) => {
    const body = (await request.json()) as { plan_id?: string };
    if (!body?.plan_id) {
      return HttpResponse.json(
        {
          code: "plan_required",
          message: "El plan es requerido.",
          request_id: "req_plan_err",
        },
        { status: 400 },
      );
    }
    return HttpResponse.json(
      {
        ...fixtures.subscriptionResponse,
        subscription: {
          ...fixtures.subscriptionResponse.subscription,
          plan_id: body.plan_id,
        },
      },
      { status: 202 },
    );
  }),

  http.get(`${API_ROOT}/ponds`, () => {
    return HttpResponse.json({ ponds: fixtures.ponds, next_cursor: null });
  }),

  http.post(`${API_ROOT}/ponds`, async ({ request }) => {
    const body = (await request.json()) as { name?: string };

    return HttpResponse.json(
      {
        pond: {
          ...fixtures.pond,
          name: body.name ?? fixtures.pond.name,
          observed_state: "pending",
        },
        job: {
          id: "job_create_01",
          type: "create_pond",
          status: "queued",
        },
      },
      { status: 202 },
    );
  }),

  http.get(`${API_ROOT}/ponds/:pondId`, ({ params }) => {
    return HttpResponse.json({
      pond: {
        ...fixtures.pond,
        id: String(params.pondId),
      },
    });
  }),

  http.get(`${API_ROOT}/ponds/:pondId/connection`, () => {
    return HttpResponse.json({
      connection: fixtures.connection,
    });
  }),

  http.get(`${API_ROOT}/ponds/:pondId/backups`, () => {
    return HttpResponse.json({ backups: fixtures.backups, next_cursor: null });
  }),

  http.post(`${API_ROOT}/ponds/:pondId/sql`, async ({ request }) => {
    const body = (await request.json()) as { query?: string; mode?: string };
    if (!body?.query?.trim()) {
      return HttpResponse.json(
        {
          code: "internal_error",
          message: "query required",
          request_id: "req_sql_empty",
        },
        { status: 400 },
      );
    }
    if (body.mode === "write") {
      return HttpResponse.json({
        ...fixtures.sqlResult,
        columns: ["affected"],
        rows: [[1]],
        row_count: 1,
        duration_ms: 31,
      });
    }
    return HttpResponse.json(fixtures.sqlResult);
  }),

  http.get(`${API_ROOT}/ponds/:pondId/sql/history`, () => {
    return HttpResponse.json({
      events: fixtures.sqlHistory,
      next_cursor: null,
    });
  }),

  http.post(`${API_ROOT}/ponds/:pondId/backups`, ({ params }) => {
    return HttpResponse.json(
      {
        backup: {
          ...fixtures.backups[1],
          completed_at: null,
          expires_at: null,
          id: "bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb",
          kind: "on_demand",
          pond_id: String(params.pondId),
          status: "queued",
        },
        job: {
          attempts: 0,
          created_at: "2026-10-26T15:00:00Z",
          id: "job_backup_01",
          node_id: "node-sv-01",
          pond_id: String(params.pondId),
          status: "queued",
          type: "backup_pond",
        },
      },
      { status: 202 },
    );
  }),

  http.post(`${API_ROOT}/ponds/:pondId/retry`, ({ params }) => {
    return HttpResponse.json(
      {
        job: {
          attempts: 1,
          created_at: "2026-10-26T15:00:00Z",
          id: "job_retry_01",
          node_id: "node-sv-01",
          pond_id: String(params.pondId),
          status: "queued",
          type: "backup_pond",
        },
      },
      { status: 202 },
    );
  }),

  http.post(`${API_ROOT}/ponds/:pondId/restore`, async ({ params }) => {
    return HttpResponse.json(
      {
        job: {
          id: "job_restore_01",
          type: "restore_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-09-22T21:00:00Z",
          node_id: "node-sv-01",
          pond_id: String(params.pondId),
        },
      },
      { status: 202 },
    );
  }),

  http.post(`${API_ROOT}/ponds/:pondId/stop`, ({ params }) => {
    return HttpResponse.json(
      {
        pond: {
          ...fixtures.pond,
          id: String(params.pondId),
          desired_state: "stopped",
          observed_state: "running",
        },
        job: {
          id: "job_stop_01",
          type: "stop_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-09-22T21:00:00Z",
          node_id: "node-sv-01",
          pond_id: String(params.pondId),
          claimed_at: null,
          completed_at: null,
          last_error: null,
        },
      },
      { status: 202 },
    );
  }),

  http.post(`${API_ROOT}/ponds/:pondId/start`, ({ params }) => {
    return HttpResponse.json(
      {
        pond: {
          ...fixtures.pond,
          id: String(params.pondId),
          desired_state: "running",
          observed_state: "stopped",
        },
        job: {
          id: "job_start_01",
          type: "start_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-09-22T21:00:00Z",
          node_id: "node-sv-01",
          pond_id: String(params.pondId),
          claimed_at: null,
          completed_at: null,
          last_error: null,
        },
      },
      { status: 202 },
    );
  }),

  http.post(`${API_ROOT}/ponds/:pondId/retry`, ({ params }) => {
    return HttpResponse.json(
      {
        job: {
          id: "job_retry_01",
          type: "start_pond",
          status: "queued",
          attempts: 0,
          created_at: "2026-09-22T21:00:00Z",
          node_id: "node-sv-01",
          pond_id: String(params.pondId),
          claimed_at: null,
          completed_at: null,
          last_error: null,
        },
      },
      { status: 202 },
    );
  }),

  http.get(`${API_ROOT}/usage`, ({ request }) => {
    const month = new URL(request.url).searchParams.get("month");
    if (month === fixtures.usageEmpty.month) {
      return HttpResponse.json(fixtures.usageEmpty);
    }

    if (month) {
      return HttpResponse.json({ ...fixtures.usage, month });
    }

    return HttpResponse.json(fixtures.usage);
  }),

  http.get(`${API_ROOT}/invoices`, () => {
    return HttpResponse.json({ invoices: fixtures.invoices, next_cursor: null });
  }),

  http.get(`${API_ROOT}/invoices/:invoiceId`, ({ params }) => {
    const invoiceId = String(params.invoiceId);
    if (invoiceId !== fixtures.invoiceDetail.invoice.id) {
      return HttpResponse.json(
        {
          code: "internal_error",
          message: "Invoice not found",
          request_id: "req_invoice_missing",
        },
        { status: 404 },
      );
    }

    return HttpResponse.json(fixtures.invoiceDetail);
  }),

  http.get(`${API_ROOT}/invoices/:invoiceId/pdf`, ({ params }) => {
    const invoiceId = String(params.invoiceId);
    if (invoiceId !== fixtures.invoiceDetail.invoice.id) {
      return HttpResponse.json(
        {
          code: "internal_error",
          message: "Invoice not found",
          request_id: "req_invoice_pdf_missing",
        },
        { status: 404 },
      );
    }

    const pdfBytes = new TextEncoder().encode("%PDF-1.4\n%KOI invoice fixture\n");
    return new HttpResponse(pdfBytes, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="${fixtures.invoiceDetail.invoice.number}.pdf"`,
      },
    });
  }),

  http.get(`${API_ROOT}/agent-access`, () => {
    return HttpResponse.json(agentAccessState);
  }),

  http.post(`${API_ROOT}/agent-access/rotate`, () => {
    agentAccessState = {
      ...agentAccessState,
      rotated_at: "2026-10-18T20:00:00Z",
    };
    return HttpResponse.json({
      slug: agentAccessState.slug,
      url: agentAccessState.url,
      password: ROTATED_AGENT_PASSWORD,
    });
  }),

  http.post(`${API_ROOT}/agent-access/toggle`, async ({ request }) => {
    const body = (await request.json()) as { enabled?: boolean };
    agentAccessState = {
      ...agentAccessState,
      enabled: Boolean(body.enabled),
    };
    return HttpResponse.json({ enabled: agentAccessState.enabled });
  }),

  http.get(`${API_ROOT}/admin/users`, () => {
    return HttpResponse.json({ users: adminUsersState, next_cursor: null });
  }),

  http.post(`${API_ROOT}/admin/users/:userId/suspend`, async ({ params, request }) => {
    const body = (await request.json()) as { confirm_text?: string; reason?: string };
    if (body.confirm_text !== SUSPEND_CONFIRM_TEXT) {
      return HttpResponse.json(
        {
          code: "confirmation_action_mismatch",
          message: "confirmation_action_mismatch",
        },
        { status: 409 },
      );
    }
    const trimmedReason = body.reason?.trim() ?? "";
    if (trimmedReason.length > 500) {
      return HttpResponse.json(
        {
          detail: [
            {
              type: "string_too_long",
              loc: ["body", "reason"],
              msg: "String should have at most 500 characters",
              ctx: { max_length: 500 },
            },
          ],
        },
        { status: 422 },
      );
    }
    const userId = String(params.userId);
    const index = adminUsersState.findIndex((user) => user.id === userId);
    if (index < 0) {
      return HttpResponse.json(
        { code: "user_not_found", message: "user_not_found" },
        { status: 404 },
      );
    }
    const updated = { ...adminUsersState[index], status: "suspended" as const };
    adminUsersState = [
      ...adminUsersState.slice(0, index),
      updated,
      ...adminUsersState.slice(index + 1),
    ];
    if (trimmedReason) {
      adminAuditState = [
        {
          id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaa01",
          actor_user_id: "22222222-2222-2222-2222-222222222222",
          actor_kind: "admin",
          target_kind: "user",
          target_id: userId,
          action: "suspend_user",
          metadata: { reason: trimmedReason },
          at: "2026-09-22T20:00:00Z",
        },
        ...adminAuditState,
      ];
    }
    return HttpResponse.json({ user: updated });
  }),

  http.post(`${API_ROOT}/admin/users/:userId/reactivate`, ({ params }) => {
    const userId = String(params.userId);
    const index = adminUsersState.findIndex((user) => user.id === userId);
    if (index < 0) {
      return HttpResponse.json(
        { code: "user_not_found", message: "user_not_found" },
        { status: 404 },
      );
    }
    const updated = { ...adminUsersState[index], status: "active" as const };
    adminUsersState = [
      ...adminUsersState.slice(0, index),
      updated,
      ...adminUsersState.slice(index + 1),
    ];
    return HttpResponse.json({ user: updated });
  }),

  http.get(`${API_ROOT}/admin/ponds`, () => {
    return HttpResponse.json({ ponds: fixtures.adminPonds, next_cursor: null });
  }),

  http.get(`${API_ROOT}/admin/audit`, () => {
    return HttpResponse.json({ events: adminAuditState, next_cursor: null });
  }),

  http.post(`${API_ROOT}/confirm/:token`, ({ params }) => {
    return respondConfirm("POST", String(params.token));
  }),

  http.delete(`${API_ROOT}/confirm/:token`, ({ params }) => {
    return respondConfirm("DELETE", String(params.token));
  }),
];

/** OpenAPI example token. Anything else must match real API error codes. */
const LIVE_CONFIRM_TOKENS = new Set(["conf_create_pond_demo"]);

type ConfirmCatalogCode =
  | "confirmation_not_found"
  | "confirmation_expired"
  | "confirmation_action_mismatch";

function confirmProblem(status: 404 | 409 | 410, code: ConfirmCatalogCode) {
  return HttpResponse.json(
    { code, message: code, request_id: "req_confirm_mock" },
    { status },
  );
}

/**
 * Mirror POST/DELETE /confirm/{token}: unknown → 404, expired → 410,
 * action mismatch → 409 (POST only). Preview MSW must not accept a fake token.
 */
function respondConfirm(method: "POST" | "DELETE", token: string) {
  const key = token.toLowerCase();
  if (key.includes("expired")) {
    return confirmProblem(410, "confirmation_expired");
  }
  if (method === "POST" && key.includes("mismatch")) {
    return confirmProblem(409, "confirmation_action_mismatch");
  }
  if (LIVE_CONFIRM_TOKENS.has(token)) {
    if (method === "DELETE") {
      return new HttpResponse(null, { status: 204 });
    }
    return HttpResponse.json({});
  }
  return confirmProblem(404, "confirmation_not_found");
}
