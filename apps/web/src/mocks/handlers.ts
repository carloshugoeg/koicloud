import { HttpResponse, http } from "msw";
import type { components } from "@/api/schema";
import { fixtures } from "@/mocks/fixtures";

const API_ROOT = "*/api/v1";
const SUSPEND_CONFIRM_TEXT = "SUSPENDER";

type AgentAccessMock = {
  slug: string;
  url: string;
  enabled: boolean;
  rotated_at: string;
};

type AdminUser = components["schemas"]["AdminUserOut"];

function freshAgentAccess(): AgentAccessMock {
  return { ...fixtures.agentAccess };
}

function freshAdminUsers(): AdminUser[] {
  return fixtures.adminUsers.map((user) => ({ ...user }));
}

let agentAccessState = freshAgentAccess();
let adminUsersState = freshAdminUsers();

export const ROTATED_AGENT_PASSWORD = "rotated-once-secret";

export function resetAgentAccessState() {
  agentAccessState = freshAgentAccess();
}

export function resetAdminUsersState() {
  adminUsersState = freshAdminUsers();
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

  http.post(`${API_ROOT}/auth/login`, () => {
    return HttpResponse.json(fixtures.session);
  }),

  http.post(`${API_ROOT}/auth/forgot`, () => {
    return HttpResponse.json({ ok: true });
  }),

  http.post(`${API_ROOT}/auth/reset`, () => {
    return HttpResponse.json({ ok: true });
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
    const body = (await request.json()) as { confirm_text?: string };
    if (body.confirm_text !== SUSPEND_CONFIRM_TEXT) {
      return HttpResponse.json(
        {
          code: "confirmation_action_mismatch",
          message: "confirmation_action_mismatch",
        },
        { status: 409 },
      );
    }
    const userId = String(params.userId);
    const index = adminUsersState.findIndex((user) => user.id === userId);
    if (index < 0) {
      return HttpResponse.json(
        { code: "internal_error", message: "user_not_found" },
        { status: 404 },
      );
    }
    const updated = { ...adminUsersState[index], status: "suspended" as const };
    adminUsersState = [
      ...adminUsersState.slice(0, index),
      updated,
      ...adminUsersState.slice(index + 1),
    ];
    return HttpResponse.json({ user: updated });
  }),

  http.post(`${API_ROOT}/admin/users/:userId/reactivate`, ({ params }) => {
    const userId = String(params.userId);
    const index = adminUsersState.findIndex((user) => user.id === userId);
    if (index < 0) {
      return HttpResponse.json(
        { code: "internal_error", message: "user_not_found" },
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
    return HttpResponse.json({ events: fixtures.adminAuditEvents, next_cursor: null });
  }),
];
