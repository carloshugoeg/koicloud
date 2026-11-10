export const title = "Invitar agente dialog";

/** Reader labels for the pond-detail invite dialog. */
export const state = (v) => {
  if (v.ui === "closed") return "Closed";
  if (v.ui === "open_idle") return "Dialog open";
  if (v.ui === "open_created") return "Password shown once";
  if (v.ui === "open_revisit") return "Subsequent view (password hidden)";
  if (v.ui === "open_revoked") {
    if (v.lastMcpAuth === "denied") return "Revoked (MCP auth fails)";
    return "Revoked";
  }
  return v.ui;
};

export const step = (action, _from, to) => {
  switch (action) {
    case "OpenIdle":
      return "open Invitar agente";
    case "OpenRevisit":
      return "reopen with active token";
    case "Close":
      return "close dialog";
    case "Generate":
      return "generate link + password";
    case "Revoke":
      return "revoke token";
    case "McpAuthOk":
      return "MCP auth succeeds [token usable]";
    case "McpAuthDenied":
      return "MCP auth fails [token invalid]";
    case "Done":
      return null;
    default:
      return action;
  }
};

export const group = (v) => {
  if (v.ui === "open_revoked" || v.lastMcpAuth === "denied") return "denied";
  if (v.ui === "open_created") return "reveal";
  if (v.ui === "open_revisit") return "working";
  if (v.ui === "open_idle") return "waiting";
  return "idle";
};

export const colors = {
  idle: "tan",
  waiting: "yellow",
  reveal: "teal",
  working: "teal",
  denied: "orange",
};
