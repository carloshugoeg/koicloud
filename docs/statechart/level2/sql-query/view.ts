export const title = "Consulta SQL";

export const state = (v: { screen: string; truncated: boolean }) => {
  if (v.screen === "idle") return "Idle";
  if (v.screen === "confirming") return "Confirm write";
  if (v.screen === "running") return "Running";
  if (v.screen === "success" && v.truncated) return "Truncated";
  if (v.screen === "success") return "Success";
  if (v.screen === "error") return "Error";
  if (v.screen === "timeout") return "Timeout";
  if (v.screen === "unavailable") return "Node unavailable";
  return "Read-only rejected";
};

export const step = (action: string) => {
  if (action === "ClickRead") return "you click Ejecutar [read]";
  if (action === "OpenWriteConfirm") return "you click Ejecutar [write]";
  if (action === "CancelWrite") return "you cancel or press Esc";
  if (action === "ConfirmWrite") return "you confirm the write";
  if (action === "RowsComeBack") return "the pond returns the rows";
  if (action === "RowCap") return "the pond hits the row cap";
  if (action === "UserSqlError") return "the pond rejects the SQL";
  if (action === "TimedOut") return "the pond times out";
  if (action === "NodeDown") return "the node is unavailable";
  if (action === "ReadOnlyRejects") return "read mode rejects the write";
  return null;
};

export const group = (v: { screen: string }) => {
  if (v.screen === "success") return "ok";
  if (v.screen === "error" || v.screen === "rejected" || v.screen === "timeout" || v.screen === "unavailable") {
    return "bad";
  }
  if (v.screen === "running" || v.screen === "confirming") return "busy";
  return "wait";
};

export const colors = {
  ok: "teal",
  bad: "orange",
  busy: "yellow",
  wait: "tan",
};
