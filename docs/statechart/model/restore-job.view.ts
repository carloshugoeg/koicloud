const labels: Record<string, string> = {
  queued: "Queued",
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
  timed_out: "Timed out",
  agent_unreachable: "Agent unreachable",
};

export const title = "Restore job";

export const state = (v: { phase: string; agent: string; ticks: number }) => {
  if (v.phase === "queued" && v.agent === "down" && v.ticks >= 3) return "Agent unreachable";
  return labels[v.phase];
};

export const group = (v: { phase: string; agent: string; ticks: number }) => {
  const label = state(v);
  if (label === "Succeeded") return "done";
  if (label === "Failed" || label === "Timed out" || label === "Agent unreachable") return "broken";
  if (label === "Running") return "working";
  return "waiting";
};

export const colors = {
  waiting: "tan",
  working: "blue",
  done: "teal",
  broken: "orange",
};

const steps: Record<string, string | null> = {
  Claim: "the node claims the job",
  FinishOk: "the restore finishes",
  FinishFail: "the restore fails",
  TimeOut: "the job sits too long",
  GiveUp: "the agent stays silent",
  Advance: null,
  Done: null,
  Stuck: null,
};

export const step = (
  action: string,
  from: { phase: string; agent: string; ticks: number },
  to: { phase: string; agent: string; ticks: number },
) => {
  if (action === "Advance" || action === "Done" || action === "Stuck") {
    if (state(from) === state(to)) return null;
    return "time passes";
  }
  return steps[action] ?? null;
};
