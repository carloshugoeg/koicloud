const labels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  timed_out: "Timed out",
  agent_unreachable: "Agent unreachable",
};

export const title = "Restore job today";

export const state = (v: { phase: string; agent: string; screen: string; ticks: number }) => {
  if (v.phase === "queued" && v.agent === "down" && v.ticks >= 3) return "Agent unreachable";
  if (v.phase !== "queued" && v.screen === "queued") return `${labels[v.phase]}, screen still says queued`;
  return labels[v.phase];
};

export const group = (v: { phase: string; agent: string; screen: string; ticks: number }) => {
  const label = state(v);
  if (label === "Succeeded") return "done";
  if (
    label.includes("queued") ||
    label === "Failed" ||
    label === "Timed out" ||
    label === "Agent unreachable"
  ) {
    return "broken";
  }
  if (label === "Running") return "working";
  return "waiting";
};

export const colors = {
  waiting: "tan",
  working: "blue",
  done: "teal",
  broken: "orange",
};

export const step = (
  action: string,
  from: { phase: string; agent: string; screen: string; ticks: number },
  to: { phase: string; agent: string; screen: string; ticks: number },
) => {
  if (action === "Done" || action === "Stuck") return state(from) === state(to) ? null : "time passes";
  if (action === "Advance") return "time passes";
  if (action === "Claim") return "the node claims the job";
  if (action === "FinishOk") return "the restore finishes";
  if (action === "FinishFail") return "the restore fails";
  if (action === "TimeOut") return "the job sits too long";
  if (action === "GiveUp") return "the agent stays silent";
  return null;
};
