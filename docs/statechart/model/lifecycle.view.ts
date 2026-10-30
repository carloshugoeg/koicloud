const L: Record<string, string> = { none: "Not created", provisioning: "Provisioning", running: "Online (En línea)",
  stopping: "Stopping", stopped: "Stopped (Detenido)", starting: "Starting", backing_up: "Backing up",
  restoring: "Restoring", deleting: "Deleting", deleted: "Deleted", failed: "Failed (Con fallas)" };
export const title = "KoiCloud pond lifecycle";
export const state = (v: any) => L[v.obs];
export const group = (v: any) => (v.jobs === 1 ? "busy" : v.obs === "failed" ? "error" : v.obs === "deleted" ? "gone" : "idle");
export const colors = { busy: "blue", error: "orange", gone: "purple", idle: "teal" };
const T: Record<string, string> = {
  "none>provisioning": "you create a pond", "provisioning>running": "the node finishes provisioning",
  "provisioning>failed": "provisioning fails", "failed>provisioning": "you press Reintentar",
  "running>stopping": "you press Detener (red, confirm)", "stopping>stopped": "the pond stops", "stopping>failed": "the stop fails",
  "stopped>starting": "you press Iniciar", "starting>running": "the pond starts", "starting>failed": "the start fails",
  "running>backing_up": "you press Respaldar ahora", "backing_up>running": "the backup ends (ok or failed row)",
  "running>restoring": "you restore a backup", "stopped>restoring": "you restore a backup", "failed>restoring": "you restore a backup", "restoring>running": "the restore finishes", "restoring>failed": "the restore fails",
  "running>deleting": "you delete (pre_delete backup)", "stopped>deleting": "you delete (pre_delete backup)",
  "failed>deleting": "you delete (pre_delete backup)", "deleting>deleted": "the pond is deleted" };
export const step = (_a: string, f: any, t: any) => T[`${f.obs}>${t.obs}`] ?? null;
