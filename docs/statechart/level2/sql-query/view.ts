export const title = "Consulta SQL";

export const state = (v: { screen: string }) => {
  if (v.screen === "idle") return "Idle";
  if (v.screen === "running") return "Running";
  if (v.screen === "success") return "Success";
  if (v.screen === "error") return "Error";
  return "Read-only rejected";
};

export const step = (action: string) => {
  if (action === "Click") return "you click Ejecutar";
  if (action === "RowsComeBack") return "the pond returns the rows";
  if (action === "SqlFails") return "the pond reports an error";
  if (action === "ReadOnlyRejects") return "read mode rejects the write";
  return null;
};

export const group = (v: { screen: string }) => {
  if (v.screen === "success") return "ok";
  if (v.screen === "error" || v.screen === "rejected") return "bad";
  if (v.screen === "running") return "busy";
  return "wait";
};

export const colors = {
  ok: "teal",
  bad: "orange",
  busy: "yellow",
  wait: "tan",
};
