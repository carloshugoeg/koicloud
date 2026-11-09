export const title = "Pond temporary access";

/** Reader labels: issued / active / expired / revoked plus denials demos hit. */
export const state = (v) => {
  if (v.phase === "expired") {
    if (v.attempt === "use_after_expiry") return "Expired (use denied)";
    return "Expired";
  }
  if (v.phase === "revoked") {
    if (v.attempt === "use_after_revoke") return "Revoked (use denied)";
    return "Revoked";
  }
  if (v.phase === "issued") {
    if (v.passwordOk === false) return "Issued (wrong password)";
    return "Issued";
  }
  if (v.passwordOk === false) return "Active (wrong password)";
  if (v.lastTool === "denied" && v.toolKind === "forbidden") {
    return "Active (create/delete denied)";
  }
  if (v.lastTool === "denied" && v.toolKind === "other_pond") {
    return "Active (wrong pond denied)";
  }
  return "Active";
};

export const step = (action, _from, to) => {
  switch (action) {
    case "Revoke":
      return "presenter revokes";
    case "Expire":
      return "expires_at passes";
    case "UseOk":
      return "audience authenticates";
    case "WrongPassword":
      return "wrong password";
    case "RetryPassword":
      return "correct password again";
    case "UseAfterExpiry":
      return "use after expiry [401]";
    case "UseAfterRevoke":
      return "use after revoke [401]";
    case "WrongPasswordTerminal":
      return null;
    case "PickAllowedTool":
    case "PickForbiddenTool":
    case "PickOtherPond":
    case "RunToolUnauthed":
    case "Done":
      return null;
    case "ResetPondMatch":
      return "back to pinned pond";
    case "RunTool":
      if (to.lastTool === "ok") return "allowed tool on pinned pond";
      if (to.toolKind === "forbidden") return "create/delete pond [denied]";
      if (to.toolKind === "other_pond") return "other pond [denied]";
      return "tool denied";
    default:
      return action;
  }
};

export const group = (v) => {
  if (v.phase === "expired" || v.phase === "revoked") return "ended";
  if (v.passwordOk === false) return "denied";
  if (v.lastTool === "denied") return "denied";
  if (v.lastAuth === "ok" && v.phase === "active") return "working";
  return "waiting";
};

export const colors = {
  waiting: "tan",
  working: "yellow",
  denied: "orange",
  ended: "pink",
};
