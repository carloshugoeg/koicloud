const LOGGED_OUT_KEY = "koi_logged_out";

export function markLoggedOut() {
  window.localStorage.setItem(LOGGED_OUT_KEY, "pending");
}

export function settleLoggedOut() {
  if (window.localStorage.getItem(LOGGED_OUT_KEY) === null) {
    return;
  }
  window.localStorage.setItem(LOGGED_OUT_KEY, "settled");
}

export function isLoggedOut() {
  const value = window.localStorage.getItem(LOGGED_OUT_KEY);
  return value === "pending" || value === "settled";
}

export function logoutNeedsRetry() {
  return window.localStorage.getItem(LOGGED_OUT_KEY) === "pending";
}

export function clearLoggedOut() {
  window.localStorage.removeItem(LOGGED_OUT_KEY);
}
