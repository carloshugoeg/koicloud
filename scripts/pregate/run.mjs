import { execFileSync, spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { childEnv, initialState, parsePlan, PlanError, redact, reduce } from "./reduce.mjs";

const here = path.dirname(fileURLToPath(import.meta.url));

export function repoRootFromHere() {
  return path.resolve(here, "../..");
}

function lookup(plan, id) {
  for (const step of plan.steps) {
    if (step.kind === "serial" && step.id === id) {
      return { command: step, groupEnv: {} };
    }
    if (step.kind === "parallel") {
      const member = step.members.find((item) => item.id === id);
      if (member) {
        return { command: member, groupEnv: step.env };
      }
    }
  }
  throw new PlanError(`missing command ${id}`);
}

function eachCommand(plan) {
  const commands = [];
  for (const step of plan.steps) {
    if (step.kind === "serial") {
      commands.push({ command: step, groupEnv: {} });
    } else {
      for (const member of step.members) {
        commands.push({ command: member, groupEnv: step.env });
      }
    }
  }
  return commands;
}

function secretValues(plan, parent) {
  return plan.redactEnvKeys
    .map((key) => parent[key])
    .filter((value) => typeof value === "string");
}

function attach(stream, prefix, secrets) {
  if (!stream) {
    return;
  }
  let pending = "";
  stream.setEncoding("utf8");
  stream.on("data", (chunk) => {
    pending += String(chunk).replaceAll("\r", "\n");
    const lines = pending.split("\n");
    pending = lines.pop() ?? "";
    for (const line of lines) {
      console.log(prefix + redact(line, secrets));
    }
  });
  stream.on("end", () => {
    if (pending.length > 0) {
      console.log(prefix + redact(pending, secrets));
    }
  });
}

function announce(spawnSpec, parent) {
  const email = typeof parent.KOI_GATE_ADMIN_EMAIL === "string" && parent.KOI_GATE_ADMIN_EMAIL.length > 0;
  const password = typeof parent.KOI_GATE_ADMIN_PASSWORD === "string" && parent.KOI_GATE_ADMIN_PASSWORD.length > 0;
  console.log(
    `pregate ${spawnSpec.id} KOI_GATE_ADMIN_EMAIL ${email ? "set" : "missing"} KOI_GATE_ADMIN_PASSWORD ${password ? "set" : "missing"}`,
  );
}

function runChild(spawnSpec, plan, parent, secrets, repoRoot, live) {
  const { command, groupEnv } = lookup(plan, spawnSpec.id);
  const built = childEnv(plan, parent, command, groupEnv);
  if (!built.ok) {
    console.error(`pregate plan ${built.error}`);
    return Promise.resolve({ id: spawnSpec.id, code: 2 });
  }
  if (command.preview) {
    announce(spawnSpec, parent);
  }
  console.log(`pregate start ${spawnSpec.id}`);
  console.log(`pregate cwd ${spawnSpec.cwd}`);
  console.log(`pregate argv ${spawnSpec.argv.join(" ")}`);
  return new Promise((resolve) => {
    const child = spawn(spawnSpec.argv[0], spawnSpec.argv.slice(1), {
      cwd: path.resolve(repoRoot, spawnSpec.cwd),
      env: built.env,
      shell: false,
      detached: true,
      stdio: ["ignore", "pipe", "pipe"],
    });
    live.add(child);
    let settled = false;
    const finish = (code) => {
      if (settled) {
        return;
      }
      settled = true;
      live.delete(child);
      resolve({ id: spawnSpec.id, code });
    };
    attach(child.stdout, spawnSpec.prefix, secrets);
    attach(child.stderr, spawnSpec.prefix, secrets);
    child.on("error", () => finish(127));
    child.on("close", (code) => finish(code === null || code === undefined ? 1 : code));
  });
}

function killLive(live) {
  for (const child of live) {
    if (!child.pid) {
      continue;
    }
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      try {
        child.kill("SIGTERM");
      } catch {
        // The child already exited.
      }
    }
  }
}

function printMemberLines(members, results) {
  for (const member of members) {
    const result = results.find((item) => item.id === member.id);
    const code = result ? result.code : 1;
    if (code === 0) {
      console.log(`pregate   pass ${member.id}`);
    } else {
      console.log(`pregate   fail ${member.id} exit ${code}`);
    }
  }
}

function withRepository(parent) {
  if (typeof parent.GITHUB_REPOSITORY === "string" && parent.GITHUB_REPOSITORY.trim().length > 0) {
    return parent;
  }
  try {
    const url = execFileSync("git", ["remote", "get-url", "origin"], { encoding: "utf8" }).trim();
    const match = /github\.com[:/]([^/]+)\/([^/.\s]+)/.exec(url);
    if (!match) {
      return parent;
    }
    return { ...parent, GITHUB_REPOSITORY: `${match[1]}/${match[2]}` };
  } catch {
    return parent;
  }
}

export async function runPlan(planPath, parent) {
  const repoRoot = repoRootFromHere();
  parent = withRepository(parent);
  let plan;
  try {
    const raw = JSON.parse(readFileSync(planPath, "utf8"));
    plan = parsePlan(raw, repoRoot);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`pregate plan ${message}`);
    return 2;
  }
  for (const { command, groupEnv } of eachCommand(plan)) {
    const built = childEnv(plan, parent, command, groupEnv);
    if (!built.ok) {
      console.error(`pregate plan ${built.error}`);
      return 2;
    }
  }

  const secrets = secretValues(plan, parent);
  const live = new Set();
  let signalled = false;
  const onSignal = () => {
    signalled = true;
    killLive(live);
  };
  process.on("SIGINT", onSignal);
  process.on("SIGTERM", onSignal);

  try {
    let state = initialState();
    while (state.phase === "pending") {
      let began;
      try {
        began = reduce(plan, state, { type: "begin" });
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        console.error(`pregate plan ${message}`);
        return 2;
      }
      state = began.state;
      if (state.phase === "done" || began.spawn.length === 0) {
        break;
      }
      const parallel = state.phase === "parallel";
      const group = parallel ? plan.steps[state.index] : null;
      const results = await Promise.all(
        began.spawn.map((spawnSpec) => runChild(spawnSpec, plan, parent, secrets, repoRoot, live)),
      );
      for (const result of results) {
        try {
          const exited = reduce(plan, state, { type: "exited", id: result.id, code: result.code });
          state = exited.state;
        } catch (error) {
          const message = error instanceof Error ? error.message : String(error);
          console.error(`pregate plan ${message}`);
          return 2;
        }
      }
      if (parallel && group && group.kind === "parallel") {
        if (state.phase === "failed") {
          console.log(`pregate fail ${group.id} exit ${state.code}`);
          printMemberLines(group.members, results);
        } else {
          console.log(`pregate pass ${group.id}`);
          printMemberLines(group.members, results);
        }
      } else {
        const result = results[0];
        if (state.phase === "failed") {
          console.log(`pregate fail ${result.id} exit ${state.code}`);
        } else {
          console.log(`pregate pass ${result.id}`);
        }
      }
      if (state.phase === "failed" && state.skipped.length > 0) {
        console.log(`pregate skipped ${state.skipped.join(" ")}`);
      }
      if (signalled) {
        return 1;
      }
    }
    if (state.phase === "failed") {
      return state.code;
    }
    return 0;
  } finally {
    process.off("SIGINT", onSignal);
    process.off("SIGTERM", onSignal);
  }
}

export function main(argv) {
  void argv;
  const planPath = path.join(repoRootFromHere(), "scripts/pregate/plan.json");
  return runPlan(planPath, process.env);
}

const invoked = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (invoked) {
  main(process.argv.slice(2)).then(
    (code) => {
      process.exit(code);
    },
    (error) => {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`pregate plan ${message}`);
      process.exit(2);
    },
  );
}
