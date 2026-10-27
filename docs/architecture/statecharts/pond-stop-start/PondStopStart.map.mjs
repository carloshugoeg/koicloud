export const title = "Pond stop / start (CCR 131)";

export const state = (v) => {
  switch (v.phase) {
    case "running":
      return "En línea";
    case "stopping":
      return "Deteniendo…";
    case "stopped":
      return "Detenido";
    case "starting":
      return "Iniciando…";
    case "error":
      return "Con fallas";
    default:
      return String(v.phase);
  }
};

export const group = (v) => {
  if (v.phase === "error") return "error";
  if (v.phase === "stopping" || v.phase === "starting") return "in-flight";
  return "steady";
};

export const colors = {
  steady: "teal",
  "in-flight": "orange",
  error: "pink",
};

export const step = (action, from) => {
  switch (action) {
    case "PostStop":
      return "POST /stop";
    case "StopOk":
      return "job stop ok";
    case "StopFailed":
      return "job stop failed";
    case "PostStart":
      return "POST /start";
    case "StartOk":
      return "job start ok";
    case "StartFailed":
      return "job start failed";
    case "CreateFailed":
      return "job create failed";
    case "RetryStop":
      return "POST /retry [stop_pond]";
    case "RetryStart":
      if (from?.last_fail === "create") return "POST /retry [create_pond]";
      return "POST /retry [start_pond]";
    case "SeedCreateError":
      return null;
    case "Idle":
      return null;
    default:
      return action;
  }
};
