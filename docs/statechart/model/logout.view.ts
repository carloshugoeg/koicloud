export const title = "Log out, then a reload";

export const state = (v: {
  screen: string;
  memory: boolean;
  cookie: boolean;
  marker: boolean;
  inflight: boolean;
  askedOut: boolean;
  failed: boolean;
  warned: boolean;
  booted: boolean;
}) => {
  if (v.memory && v.screen === "app" && v.inflight) return "Log out sent";
  if (v.memory && v.screen === "app" && v.askedOut) return "Signed back in";
  if (v.memory && v.screen === "app") return "Signed in";
  if (!v.memory && v.failed && v.cookie && !v.booted) return "Log out failed";
  if (!v.memory && v.failed && v.cookie && v.booted) return "Reloaded, still logged out";
  if (!v.memory && v.failed && !v.cookie) return "Retry cleared the server session";
  if (!v.memory && v.askedOut && v.cookie && !v.failed) return "Reloaded during log out";
  if (!v.memory && v.askedOut && !v.cookie) return "Logged out";
  return "Login";
};

export const group = (v: {
  screen: string;
  memory: boolean;
  failed: boolean;
  askedOut: boolean;
  cookie: boolean;
  inflight: boolean;
}) => {
  if (v.memory && v.askedOut && !v.inflight) return "bug";
  if (v.failed && v.cookie) return "warn";
  if (v.screen === "login") return "auth";
  return "session";
};

export const colors = { session: "teal", auth: "pink", warn: "orange", bug: "purple" };

export const step = (
  action: string,
  from: { cookie: boolean; failed: boolean; marker: boolean; inflight: boolean },
  to: { cookie: boolean; failed: boolean; screen: string; memory: boolean },
) => {
  if (action === "YouPressLogOut") return "you press Log out";
  if (action === "ServerAcceptsLogout") return "the server accepts and clears the cookie";
  if (action === "ServerRejectsLogout") return "the server returns an error and the cookie stays";
  if (action === "YouLogIn") return "you log in";
  if (action === "YouReloadOrOpenUso") {
    if (to.memory) return "you reload or open /app/uso and the refresh signs you in";
    if (from.inflight) return "you reload or open /app/uso while log out is in flight";
    if (from.failed && from.cookie) return "you reload or open /app/uso and stay logged out";
    if (!from.cookie && !to.cookie) return null;
    return "you reload or open /app/uso";
  }
  return action;
};
