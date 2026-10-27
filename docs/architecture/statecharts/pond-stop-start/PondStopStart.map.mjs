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
    case "provisioning":
      return "Aprovisionando…";
    default:
      return String(v.phase);
  }
};

export const group = (v) => {
  if (v.phase === "error") return "error";
  if (v.phase === "stopping" || v.phase === "starting" || v.phase === "provisioning") {
    return "in-flight";
  }
  return "steady";
};

export const colors = {
  steady: "teal",
  "in-flight": "orange",
  error: "pink",
};

export const step = (action) => {
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
    case "Retry":
      return "retry (existing)";
    case "ProvisionOk":
      return "create/start ok";
    case "ProvisionFailed":
      return "create/start failed";
    case "Idle":
      return null;
    default:
      return action;
  }
};
