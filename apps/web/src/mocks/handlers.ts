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
    return HttpResponse.json(fixtures.agentAccess);
  }),

  http.get(`${API_ROOT}/admin/users`, () => {
    return HttpResponse.json({ users: fixtures.adminUsers, next_cursor: null });
  }),
];
