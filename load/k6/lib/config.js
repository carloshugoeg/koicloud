import { Counter, Rate, Trend } from "k6/metrics";

// Demo account from README.md. Override with KOI_EMAIL and KOI_PASSWORD.
const README_DEMO_EMAIL = "demo@koicloud.dev";
const README_DEMO_PASSWORD = "Sup3rSegura!2026";

export const RNF01_P95_MS = 500;
export const RNF01_VUS = 20;
export const RNF01_DURATION = "30s";

function positiveInt(name, fallback) {
  const raw = __ENV[name];
  if (!raw) {
    return fallback;
  }
  const value = Number(raw);
  if (!Number.isInteger(value) || value < 1) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

function duration() {
  const raw = __ENV.K6_DURATION || RNF01_DURATION;
  if (!/^\d+(ms|s|m|h)$/.test(raw)) {
    throw new Error("K6_DURATION must look like 30s");
  }
  return raw;
}

function parseOrigin() {
  let url = (__ENV.BASE_URL || "").trim().replace(/\/+$/, "");
  if (!url) {
    throw new Error(
      "BASE_URL is required. Set the API origin, for example http://127.0.0.1:8000.",
    );
  }
  return url.replace(/\/api\/v1$/, "");
}

export const config = {
  origin: parseOrigin(),
  email: __ENV.KOI_EMAIL || README_DEMO_EMAIL,
  password: __ENV.KOI_PASSWORD || README_DEMO_PASSWORD,
  vus: positiveInt("K6_VUS", RNF01_VUS),
  duration: duration(),
};

export function scenarioOptions(step) {
  return {
    vus: config.vus,
    duration: config.duration,
    thresholds: {
      [`${step}_duration`]: [`p(95)<${RNF01_P95_MS}`],
      [`${step}_errors`]: ["rate==0"],
      [`${step}_samples`]: ["count>0"],
    },
    summaryTrendStats: ["avg", "min", "med", "max", "p(90)", "p(95)", "p(99)", "count"],
  };
}

export function scenarioMetrics(step) {
  return {
    duration: new Trend(`${step}_duration`, true),
    errors: new Rate(`${step}_errors`),
    samples: new Counter(`${step}_samples`),
  };
}

export function recordSample(metrics, res, ok) {
  const timing = res && res.timings ? res.timings.duration : null;
  metrics.samples.add(1);
  metrics.errors.add(ok && timing !== null ? 0 : 1);
  if (timing !== null) {
    metrics.duration.add(timing);
  }
}
