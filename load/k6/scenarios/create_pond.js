import http from "k6/http";
import { check } from "k6";
import { baseUrl, demoCredentials, rnf01Thresholds, twentyVu } from "../lib/config.js";

export const options = {
  ...twentyVu,
  thresholds: rnf01Thresholds,
};

export function setup() {
  const creds = demoCredentials();
  const res = http.post(
    `${baseUrl()}/api/v1/auth/login`,
    JSON.stringify({ email: creds.email, password: creds.password }),
    { headers: { "Content-Type": "application/json", "X-KOI-Surface": "web" } },
  );
  if (res.status !== 200) {
    throw new Error(`setup login failed: ${res.status} ${res.body}`);
  }
  return { token: JSON.parse(res.body).access_token };
}

/**
 * Measures POST /api/v1/ponds (propose). 202 (created) or 409 (confirmation_required)
 * are success for latency. Does not confirm or provision.
 */
export default function (data) {
  const name = `k6-${__VU}-${__ITER}-${Date.now()}`;
  const res = http.post(
    `${baseUrl()}/api/v1/ponds`,
    JSON.stringify({ name, engine_version: "16" }),
    {
      headers: {
        Authorization: `Bearer ${data.token}`,
        "Content-Type": "application/json",
        "X-KOI-Surface": "web",
      },
    },
  );
  check(res, {
    "create_pond propose 202 or 409": (r) => r.status === 202 || r.status === 409,
  });
}
