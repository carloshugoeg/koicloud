export const title = "KoiCloud system (Level 1)";
const P: Record<string, string> = { none: "No pond", provisioning: "Provisioning", running: "Online", stopped: "Stopped", failed: "Failed", deleting: "Deleting", deleted: "Deleted" };
export const state = (v: any) => ({
  Account: `${v.session === "in" ? "Logged in" : "Logged out"}${v.jwt ? ", access live" : ""}${v.status === "suspended" ? ", suspended" : ""}`,
  Agent: v.agentOn ? "Agent on" : "Agent off",
  Pond: P[v.pond],
});
const S: Record<string, string> = { UserLogsIn: "you log in", UserLogsOut: "you log out", TokenExpires: "the 15-min token expires",
  AdminSuspends: "an admin suspends you", AdminReactivates: "an admin reactivates you", UserTogglesAgent: "you toggle agent access",
  ProvisionEnds: "the node finishes provisioning", StopStart: "you stop or start", DeleteEnds: "the node deletes the pond",
  NodeSamples: "the node reports a sample", DayAggregated: "daily metering runs" };
export const step = (a: string, f: any, t: any) => {
  if (S[a]) return S[a];
  const who = t.loggedOutCall !== f.loggedOutCall || t.suspendedCall !== f.suspendedCall || t.agentBeyondOwner !== f.agentBeyondOwner ? " (should be refused)" : "";
  if (a.startsWith("Creates")) return "a pond is created" + who;
  if (a.startsWith("Deletes")) return "a pond delete is requested" + who;
  if (a.startsWith("Reads")) return "the pond API answers" + who;
  return a;
};
