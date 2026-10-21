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

export default function (data) {
  const res = http.get(`${baseUrl()}/api/v1/ponds`, {
    headers: {
      Authorization: `Bearer ${data.token}`,
      "X-KOI-Surface": "web",
    },
  });
  check(res, {
    "list_ponds status 200": (r) => r.status === 200,
  });
}
