export const title = "Temp-access SQL auto-confirm";

/** Reader labels for the demo paths that can break. */
export const state = (v) => {
  if (v.phase === "confirm") return "Confirm write (account)";
  if (v.phase === "running") {
    if (v.statement === "long_running") return "Running (long query)";
    if (v.actor === "temp" && v.statement === "safe_write") {
      return "Running (temp auto-confirm)";
    }
    return "Running";
  }
  if (v.phase === "success") return "Success";
  if (v.phase === "blocked") {
    if (v.statement === "privilege") return "Blocked (privilege change)";
    return "Blocked (dangerous SQL)";
  }
  if (v.phase === "timed_out") return "Timed out";
  if (v.phase === "rate_limited") return "Rate limited";
  if (v.actor === "temp") return "Idle (temp actor)";
  return "Idle (account actor)";
};

export const step = (action, from, to) => {
  switch (action) {
    case "PickTemp":
      return "switch to temp actor";
    case "PickAccount":
      return "switch to account actor";
    case "PickSafeWrite":
      return "pick CREATE/INSERT";
    case "PickDangerous":
      return "pick DROP DATABASE / COPY PROGRAM";
    case "PickPrivilege":
      return "pick GRANT / REVOKE / ALTER ROLE";
    case "PickLongRunning":
      return "pick long-running SQL";
    case "PickRead":
      return "pick SELECT";
    case "ResetRateWindow":
      return "rate window resets";
    case "ProposeConfirm":
      return "run_sql write [account → confirm]";
    case "ConfirmWrite":
      return "confirm_action";
    case "CancelConfirm":
      return "cancel confirm";
    case "HitRateLimit":
      return "run_sql [rate limited]";
    case "BlockDangerous":
      return "run_sql [dangerous blocked]";
    case "BlockPrivilege":
      return "run_sql [privilege blocked]";
    case "AutoRunSafeWrite":
      return "run_sql write [temp auto-confirm]";
    case "AutoRunLong":
      return "run_sql [temp long query]";
    case "RunRead":
      return "run_sql read";
    case "AccountBlockDangerous":
      return "run_sql [account blocked]";
    case "Succeed":
      return "rows returned";
    case "Timeout":
      return "statement_timeout aborts";
    case "Ack":
      return "ready again";
    case "Done":
      return null;
    default:
      return action;
  }
};

export const group = (v) => {
  if (v.phase === "success") return "ok";
  if (v.phase === "blocked" || v.phase === "timed_out" || v.phase === "rate_limited") {
    return "denied";
  }
  if (v.phase === "confirm" || v.phase === "running") return "busy";
  return "idle";
};

export const colors = {
  idle: "tan",
  busy: "yellow",
  ok: "teal",
  denied: "orange",
};
