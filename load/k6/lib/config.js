export function baseUrl() {
  const url = __ENV.BASE_URL;
  if (!url) {
    throw new Error("BASE_URL is required (e.g. http://127.0.0.1:8000 or https://demo.example)");
  }
  return url.replace(/\/$/, "");
}

export function demoCredentials() {
  return {
    email: __ENV.KOI_EMAIL || "demo@koicloud.dev",
    password: __ENV.KOI_PASSWORD || "Sup3rSegura!2026",
  };
}

/** RNF-01: p95 < 500 ms at 20 VUs. Do not relax. */
export const rnf01Thresholds = {
  http_req_duration: ["p(95)<500"],
  http_req_failed: ["rate<0.01"],
};

export const twentyVu = {
  vus: 20,
  duration: "30s",
};
