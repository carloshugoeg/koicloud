import http from "k6/http";
import { config } from "./config.js";

export function postLogin(step) {
  return http.post(
    `${config.origin}/api/v1/auth/login`,
    JSON.stringify({ email: config.email, password: config.password }),
    {
      headers: {
        "Content-Type": "application/json",
        "X-KOI-Surface": "web",
      },
      tags: { step },
      responseCallback: http.expectedStatuses(200),
    },
  );
}

export function hasAccessToken(res) {
  if (!res || res.status !== 200) {
    return false;
  }
  try {
    return Boolean(res.json("access_token"));
  } catch {
    return false;
  }
}

export function accessToken(res) {
  if (!hasAccessToken(res)) {
    throw new Error(`login failed with status ${res ? res.status : "none"}`);
  }
  return res.json("access_token");
}
