import { expect, test } from "@playwright/test";

const demo = {
  email: "demo@koicloud.dev",
  password: "Sup3rSegura!2026",
} as const;

test("preview db at head lets /me through, then logout makes the old token 401", async ({ request }) => {
  test.skip(
    !process.env.PLAYWRIGHT_BASE_URL,
    "Set PLAYWRIGHT_BASE_URL to the preview that should already be on revision 0005.",
  );

  const login = await request.post("/api/v1/auth/login", { data: demo });
  expect(login.status()).toBe(200);
  const access = (await login.json()).access_token as string;

  const before = await request.get("/api/v1/me", {
    headers: { authorization: `Bearer ${access}` },
  });
  expect(before.status()).toBe(200);

  const logout = await request.post("/api/v1/auth/logout", {
    headers: { authorization: `Bearer ${access}` },
  });
  expect(logout.status()).toBe(204);

  const after = await request.get("/api/v1/me", {
    headers: { authorization: `Bearer ${access}` },
  });
  expect(after.status()).toBe(401);
  expect((await after.json()).code).toBe("token_invalid");
});
