import http from "k6/http";
import { check } from "k6";
import { config, recordSample, scenarioMetrics, scenarioOptions } from "../lib/config.js";
import { accessToken, postLogin } from "../lib/session.js";

const metrics = scenarioMetrics("create_pond");

export const options = scenarioOptions("create_pond");

const ACCEPTED = [200, 201, 202, 409];

export function setup() {
  return { token: accessToken(postLogin("setup_login")) };
}

function pondName() {
  const vu = String(__VU).padStart(2, "0");
  const iter = String(__ITER).padStart(4, "0");
  const tick = Date.now().toString(36);
  return `k6-${vu}-${iter}-${tick}`.slice(0, 40);
}

export default function (data) {
  const res = http.post(
    `${config.origin}/api/v1/ponds`,
    JSON.stringify({ name: pondName(), engine_version: "16" }),
    {
      headers: {
        Authorization: `Bearer ${data.token}`,
        "Content-Type": "application/json",
        "X-KOI-Surface": "cli",
      },
      tags: { step: "create_pond" },
      responseCallback: http.expectedStatuses(200, 201, 202, 409),
    },
  );
  const ok = ACCEPTED.includes(res.status);
  recordSample(metrics, res, ok);
  check(res, {
    "create_pond 200, 201, 202, or 409": () => ok,
  });
}
