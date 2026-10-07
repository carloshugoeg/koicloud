import { HttpResponse, http } from "msw";
import { fixtures } from "@/mocks/fixtures";

const API_ROOT = "*/api/v1";

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

  http.get(`${API_ROOT}/usage`, () => {
    return HttpResponse.json(fixtures.usage);
  }),

  http.get(`${API_ROOT}/agent-access`, () => {
    return HttpResponse.json(fixtures.agentAccess);
  }),

  http.get(`${API_ROOT}/admin/users`, () => {
    return HttpResponse.json({ users: fixtures.adminUsers, next_cursor: null });
  }),
];
