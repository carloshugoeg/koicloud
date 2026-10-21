import http from "k6/http";
import { check } from "k6";
import { config, recordSample, scenarioMetrics, scenarioOptions } from "../lib/config.js";
import { accessToken, postLogin } from "../lib/session.js";

const metrics = scenarioMetrics("list_ponds");

export const options = scenarioOptions("list_ponds");

export function setup() {
  return { token: accessToken(postLogin("setup_login")) };
}

export default function (data) {
  const res = http.get(`${config.origin}/api/v1/ponds`, {
    headers: {
      Authorization: `Bearer ${data.token}`,
      "X-KOI-Surface": "web",
    },
    tags: { step: "list_ponds" },
    responseCallback: http.expectedStatuses(200),
  });
  recordSample(metrics, res, res.status === 200);
  check(res, {
    "list_ponds 200": (r) => r.status === 200,
  });
}
