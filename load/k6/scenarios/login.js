import { check } from "k6";
import { recordSample, scenarioMetrics, scenarioOptions } from "../lib/config.js";
import { hasAccessToken, postLogin } from "../lib/session.js";

const metrics = scenarioMetrics("login");

export const options = scenarioOptions("login");

export default function () {
  const res = postLogin("login");
  const ok = hasAccessToken(res);
  recordSample(metrics, res, ok);
  check(res, {
    "login 200 with access_token": () => ok,
  });
}
