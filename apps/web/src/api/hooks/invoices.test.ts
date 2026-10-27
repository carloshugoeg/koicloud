import { afterEach, describe, expect, it, vi } from "vitest";
import { downloadInvoicePdf } from "@/api/hooks/invoices";
import { ApiError } from "@/lib/errors";

vi.mock("@/api/client", () => ({
  apiClient: {
    GET: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";

const getMock = vi.mocked(apiClient.GET);

describe("downloadInvoicePdf", () => {
  afterEach(() => {
    getMock.mockReset();
  });

  it("throws internal_error without inventing a client request_id when the PDF body is missing", async () => {
    getMock.mockResolvedValue({
      data: undefined,
      error: undefined,
      response: new Response(null, { status: 200 }),
    } as Awaited<ReturnType<typeof apiClient.GET>>);

    let caught: unknown;
    try {
      await downloadInvoicePdf("inv_1");
    } catch (error) {
      caught = error;
    }

    expect(caught).toBeInstanceOf(ApiError);
    const problem = (caught as ApiError).problem;
    expect(problem?.code).toBe("internal_error");
    expect(problem).not.toHaveProperty("request_id");
  });
});
