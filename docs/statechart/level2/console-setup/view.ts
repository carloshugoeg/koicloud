export const title = "Rol de la consola";

export const state = (v: { phase: string; rotated: boolean }) => {
  if (v.phase === "pending" && v.rotated) return "Password rotated";
  if (v.phase === "pending") return "Setup pending";
  return "Setup done";
};

export const step = (
  action: string,
  from: { phase: string; rotated: boolean },
  to: { phase: string; rotated: boolean },
) => {
  if (action === "BootTooEarly") return null;
  if (action === "Query") return null;
  if (action === "ServerAccepts" && !from.rotated && to.phase === "done") {
    return "the server accepts the database";
  }
  if (action === "ServerAccepts" && from.rotated && to.phase === "done") {
    return "setup runs once for the new password";
  }
  if (action === "PasswordRotates") return "the password rotates";
  return null;
};

export const group = (v: { phase: string; rotated: boolean }) => {
  if (v.phase === "done") return "ok";
  if (v.rotated) return "busy";
  return "wait";
};

export const colors = {
  ok: "teal",
  busy: "yellow",
  wait: "tan",
};
