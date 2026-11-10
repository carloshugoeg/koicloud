export const title = "Console MCP connect";

/** Reader labels for paste → auth → pond-pinned → tool outcomes. */
export const state = (v) => {
  if (v.session === "bare") return "No credentials";
  if (v.session === "pasted") return "Link pasted";
  if (v.session === "auth_failed") return "Auth failed";
  if (v.lastTool === "ok") return "Pond-pinned (read ok)";
  if (v.lastTool === "denied" && v.toolKind === "forbidden") {
    return "Pond-pinned (forbidden denied)";
  }
  if (v.lastTool === "denied" && v.toolKind === "other_pond") {
    return "Pond-pinned (off-pond denied)";
  }
  if (v.lastTool === "denied") return "Pond-pinned (tool denied)";
  return "Pond-pinned";
};

export const step = (action, _from, to) => {
  switch (action) {
    case "PasteLinkPassword":
      return "paste link + password";
    case "AuthSucceed":
      return "auth succeeds";
    case "AuthFail":
      return "auth fails [401]";
    case "RepasteCorrect":
      return "paste correct password";
    case "PickAllowed":
    case "PickForbidden":
    case "PickOtherPond":
    case "Done":
      return null;
    case "CallToolUnauthed":
      return "call tool before auth [denied]";
    case "CallTool":
      if (to.lastTool === "ok") return "whoami or get_pond [ok]";
      if (to.toolKind === "forbidden") return "forbidden tool [denied]";
      if (to.toolKind === "other_pond") return "other pond [denied]";
      return "tool denied";
    default:
      return action;
  }
};

export const group = (v) => {
  if (v.session === "auth_failed") return "denied";
  if (v.lastTool === "denied") return "denied";
  if (v.session === "pond_pinned" && v.lastAuth === "ok") return "working";
  if (v.session === "pasted") return "waiting";
  return "idle";
};

export const colors = {
  idle: "tan",
  waiting: "yellow",
  working: "teal",
  denied: "orange",
};
