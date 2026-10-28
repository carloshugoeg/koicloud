import { getResponse } from "msw";
import { describe, expect, it } from "vitest";
import { handlers } from "@/mocks/handlers";

function isPassthrough(response: Response | undefined): boolean {
  return response?.headers.get("x-msw-intention") === "passthrough";
}

describe("W1-41 Preview MSW passthrough", () => {
  it("passthroughs login for seeded gate-admin email (not demo allowlist)", async () => {
    const request = new Request("http://localhost/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "gate-132-admin@koicloud.test",
        password: "not-a-secret-for-this-test",
      }),
    });

    const response = await getResponse(handlers, request);
    expect(isPassthrough(response)).toBe(true);
  });

  it("still mocks demo login (does not passthrough)", async () => {
    const request = new Request("http://localhost/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: "demo@koicloud.dev",
        password: "Sup3rSegura!2026",
      }),
    });

    const response = await getResponse(handlers, request);
    expect(isPassthrough(response)).toBe(false);
    expect(response?.status).toBe(200);
    const body = (await response?.json()) as { access_token?: string };
    expect(body.access_token).toBe("access_demo_token");
  });

  it("passthroughs /admin/** when Authorization is a non-demo Bearer", async () => {
    const request = new Request("http://localhost/api/v1/admin/users", {
      method: "GET",
      headers: { Authorization: "Bearer eyJhbGciOiJIUzI1NiJ9.real-preview-jwt" },
    });

    const response = await getResponse(handlers, request);
    expect(isPassthrough(response)).toBe(true);
  });

  it("still mocks /admin/** for demo access_admin_token", async () => {
    const request = new Request("http://localhost/api/v1/admin/users", {
      method: "GET",
      headers: { Authorization: "Bearer access_admin_token" },
    });

    const response = await getResponse(handlers, request);
    expect(isPassthrough(response)).toBe(false);
    expect(response?.status).toBe(200);
    const body = (await response?.json()) as { users?: unknown[] };
    expect(Array.isArray(body.users)).toBe(true);
  });
});
