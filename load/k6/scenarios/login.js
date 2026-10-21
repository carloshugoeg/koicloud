import http from "k6/http";
import { check } from "k6";
import { baseUrl, demoCredentials, rnf01Thresholds, twentyVu } from "../lib/config.js";

export const options = {
  ...twentyVu,
  thresholds: rnf01Thresholds,
};

export default function () {
  const creds = demoCredentials();
  const res = http.post(
    `${baseUrl()}/api/v1/auth/login`,
    JSON.stringify({ email: creds.email, password: creds.password }),
    { headers: { "Content-Type": "application/json", "X-KOI-Surface": "web" } },
  );
  check(res, {
    "login status 200": (r) => r.status === 200,
    "login has access_token": (r) => {
      try {
        return Boolean(JSON.parse(r.body).access_token);
      } catch (_) {
        return false;
      }
    },
  });
}
