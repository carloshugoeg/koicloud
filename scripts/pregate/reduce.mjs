import path from "node:path";

export class PlanError extends Error {
  constructor(message) {
    super(message);
    this.name = "PlanError";
  }
}

const PREVIEW_URL_KEYS = ["PLAYWRIGHT_BASE_URL", "KOI_PUBLIC_BASE_URL"];

function assert(condition, message) {
  if (!condition) {
    throw new PlanError(message);
  }
}

function isPlainObject(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringList(value, label) {
  assert(Array.isArray(value), `${label} must be an array`);
  for (const entry of value) {
    assert(typeof entry === "string" && entry.length > 0, `${label} entries must be non-empty strings`);
  }
  return value;
}

function resolveToken(value, browserPath) {
  assert(typeof value === "string", "env values must be strings");
  return value.split("$browserPath").join(browserPath);
}

function parseEnv(raw, browserPath, label) {
  if (raw === undefined) {
    return {};
  }
  assert(isPlainObject(raw), `${label} env must be an object`);
  const env = {};
  for (const [key, value] of Object.entries(raw)) {
    env[key] = resolveToken(value, browserPath);
  }
  return env;
}

function parseLocks(raw, label) {
  if (raw === undefined) {
    return [];
  }
  assert(Array.isArray(raw), `${label} locks must be an array`);
  return raw.map((lock) => {
    assert(isPlainObject(lock) && lock.kind === "tcp", `${label} locks must be tcp`);
    assert(Number.isInteger(lock.port) && lock.port > 0 && lock.port < 65536, `${label} port is invalid`);
    return { kind: "tcp", port: lock.port };
  });
}

function parseArgv(raw, label, forbiddenFragments) {
  assert(Array.isArray(raw) && raw.length > 0, `${label} argv must be a non-empty array`);
  for (const entry of raw) {
    assert(typeof entry === "string" && entry.length > 0, `${label} argv entries must be non-empty strings`);
    for (const fragment of forbiddenFragments) {
      assert(!entry.includes(fragment), `${label} argv must not include ${fragment}`);
    }
  }
  return raw;
}

function rejectForbiddenEnv(env, forbidden, label) {
  for (const key of forbidden) {
    assert(!(key in env), `${label} sets forbidden env ${key}`);
  }
}

function withinRepo(repoRoot, cwd) {
  assert(typeof cwd === "string" && cwd.length > 0, "cwd must be a non-empty string");
  const abs = path.resolve(repoRoot, cwd);
  const rel = path.relative(repoRoot, abs);
  assert(rel === "" || (!rel.startsWith("..") && !path.isAbsolute(rel)), `cwd escapes the repo: ${cwd}`);
  return cwd;
}

export function parsePlan(raw, repoRoot) {
  assert(isPlainObject(raw), "plan must be an object");
  assert(raw.version === 1, "plan version must be 1");
  assert(typeof raw.browserPath === "string" && raw.browserPath.length > 0, "browserPath is required");
  assert(typeof repoRoot === "string" && repoRoot.length > 0, "repoRoot is required");
  const browserPath = path.resolve(repoRoot, raw.browserPath);
  assert(isPlainObject(raw.preview), "preview policy is required");
  assert(raw.preview.requireHttps === true, "preview.requireHttps must be true");
  assert(raw.preview.requireHostSuffix === ".vercel.app", "preview.requireHostSuffix must be .vercel.app");
  const denyHosts = stringList(raw.preview.denyHosts, "preview.denyHosts");
  const forbiddenEnvKeys = stringList(raw.forbiddenEnvKeys, "forbiddenEnvKeys");
  const inheritEnv = stringList(raw.inheritEnv, "inheritEnv");
  const redactEnvKeys = stringList(raw.redactEnvKeys, "redactEnvKeys");
  assert(Array.isArray(raw.steps) && raw.steps.length > 0, "plan needs at least one step");

  const ids = new Set();
  const ports = new Set();
  let parallelCount = 0;
  const steps = [];

  for (const step of raw.steps) {
    assert(isPlainObject(step), "step must be an object");
    assert(typeof step.id === "string" && step.id.length > 0, "step id is required");
    assert(typeof step.title === "string" && step.title.length > 0, "step title is required");
    assert(!ids.has(step.id), `duplicate id ${step.id}`);
    ids.add(step.id);

    if (step.kind === "serial") {
      assert(!("members" in step), `serial step ${step.id} cannot have members`);
      const env = parseEnv(step.env, browserPath, step.id);
      rejectForbiddenEnv(env, forbiddenEnvKeys, step.id);
      const locks = parseLocks(step.locks, step.id);
      for (const lock of locks) {
        assert(!ports.has(lock.port), `tcp port ${lock.port} is locked more than once`);
        ports.add(lock.port);
      }
      steps.push({
        kind: "serial",
        id: step.id,
        title: step.title,
        cwd: withinRepo(repoRoot, step.cwd),
        argv: parseArgv(step.argv, step.id, []),
        env,
        locks,
        preview: false,
      });
      continue;
    }

    assert(step.kind === "parallel", `unknown step kind for ${step.id}`);
    parallelCount += 1;
    assert(parallelCount === 1, "plan allows one parallel group");
    assert(Array.isArray(step.members) && step.members.length > 0, `${step.id} needs members`);
    const groupEnv = parseEnv(step.env, browserPath, step.id);
    rejectForbiddenEnv(groupEnv, forbiddenEnvKeys, step.id);
    const members = step.members.map((member) => {
      assert(isPlainObject(member), "member must be an object");
      assert(typeof member.id === "string" && member.id.length > 0, "member id is required");
      assert(typeof member.title === "string" && member.title.length > 0, "member title is required");
      assert(!ids.has(member.id), `duplicate id ${member.id}`);
      ids.add(member.id);
      const env = parseEnv(member.env, browserPath, member.id);
      rejectForbiddenEnv(env, forbiddenEnvKeys, member.id);
      const locks = parseLocks(member.locks, member.id);
      for (const lock of locks) {
        assert(!ports.has(lock.port), `tcp port ${lock.port} is locked more than once`);
        ports.add(lock.port);
      }
      const fragments = member.argvMustNotInclude === undefined ? [] : stringList(member.argvMustNotInclude, `${member.id} argvMustNotInclude`);
      return {
        kind: "member",
        id: member.id,
        title: member.title,
        cwd: withinRepo(repoRoot, member.cwd),
        argv: parseArgv(member.argv, member.id, fragments),
        env,
        locks,
        preview: member.preview === true,
      };
    });
    steps.push({
      kind: "parallel",
      id: step.id,
      title: step.title,
      env: groupEnv,
      members,
    });
  }

  return {
    version: 1,
    browserPath,
    preview: {
      denyHosts,
      requireHttps: true,
      requireHostSuffix: ".vercel.app",
    },
    forbiddenEnvKeys,
    inheritEnv,
    redactEnvKeys,
    steps,
  };
}

export function initialState() {
  return { phase: "pending", index: 0 };
}

function skippedAfter(plan, index) {
  const skipped = [];
  for (let cursor = index + 1; cursor < plan.steps.length; cursor += 1) {
    const step = plan.steps[cursor];
    skipped.push(step.id);
    if (step.kind === "parallel") {
      for (const member of step.members) {
        skipped.push(member.id);
      }
    }
  }
  return skipped;
}

function toSpawn(command) {
  return {
    id: command.id,
    title: command.title,
    cwd: command.cwd,
    argv: command.argv,
    env: command.env,
    prefix: `[${command.id}] `,
  };
}

function advance(plan, index) {
  const next = index + 1;
  if (next >= plan.steps.length) {
    return { state: { phase: "done" }, spawn: [] };
  }
  return { state: { phase: "pending", index: next }, spawn: [] };
}

export function reduce(plan, state, event) {
  if (state.phase === "failed" || state.phase === "done") {
    return { state, spawn: [] };
  }
  if (event.type === "begin") {
    assert(state.phase === "pending", "begin is only valid while pending");
    const step = plan.steps[state.index];
    if (!step) {
      return { state: { phase: "done" }, spawn: [] };
    }
    if (step.kind === "serial") {
      return {
        state: { phase: "serial", index: state.index, id: step.id },
        spawn: [toSpawn(step)],
      };
    }
    return {
      state: {
        phase: "parallel",
        index: state.index,
        pending: new Set(step.members.map((member) => member.id)),
        codes: new Map(),
      },
      spawn: step.members.map((member) => toSpawn(member)),
    };
  }
  if (event.type !== "exited") {
    throw new PlanError(`unknown event ${event.type}`);
  }
  if (state.phase === "serial") {
    assert(event.id === state.id, `exit for ${event.id} does not match ${state.id}`);
    if (event.code === 0) {
      return advance(plan, state.index);
    }
    return {
      state: { phase: "failed", code: event.code, skipped: skippedAfter(plan, state.index) },
      spawn: [],
    };
  }
  if (state.phase === "parallel") {
    assert(state.pending.has(event.id), `exit for ${event.id} is not pending`);
    const pending = new Set(state.pending);
    pending.delete(event.id);
    const codes = new Map(state.codes);
    codes.set(event.id, event.code);
    if (pending.size > 0) {
      return {
        state: { phase: "parallel", index: state.index, pending, codes },
        spawn: [],
      };
    }
    const failed = [...codes.values()].some((code) => code !== 0);
    if (!failed) {
      return advance(plan, state.index);
    }
    return {
      state: { phase: "failed", code: 1, skipped: skippedAfter(plan, state.index) },
      spawn: [],
    };
  }
  throw new PlanError(`exit is not valid in phase ${state.phase}`);
}

export function checkPreviewUrl(value, policy) {
  let url;
  try {
    url = new URL(value);
  } catch {
    return `preview URL is not a URL: ${value}`;
  }
  if (policy.requireHttps && url.protocol !== "https:") {
    return `preview URL must be https: ${value}`;
  }
  const host = url.hostname;
  if (policy.denyHosts.includes(host)) {
    return `preview URL host is denied: ${host}`;
  }
  if (!host.endsWith(policy.requireHostSuffix)) {
    return `preview URL host must end with ${policy.requireHostSuffix}: ${host}`;
  }
  return null;
}

export function childEnv(plan, parent, command, groupEnv) {
  for (const key of plan.forbiddenEnvKeys) {
    if (Object.prototype.hasOwnProperty.call(groupEnv, key) || Object.prototype.hasOwnProperty.call(command.env, key)) {
      return { ok: false, error: `plan sets forbidden env ${key}` };
    }
  }
  const env = {};
  for (const key of plan.inheritEnv) {
    const value = parent[key];
    if (typeof value === "string") {
      env[key] = value;
    }
  }
  for (const key of plan.forbiddenEnvKeys) {
    delete env[key];
  }
  Object.assign(env, groupEnv, command.env);
  if (command.preview) {
    for (const key of PREVIEW_URL_KEYS) {
      const value = env[key];
      if (typeof value === "string" && value.length > 0) {
        const problem = checkPreviewUrl(value, plan.preview);
        if (problem) {
          return { ok: false, error: problem };
        }
      }
    }
  }
  return { ok: true, env };
}

export function redact(line, secretValues) {
  const secrets = secretValues
    .filter((value) => typeof value === "string" && value.length > 0)
    .sort((left, right) => right.length - left.length);
  let out = line;
  for (const secret of secrets) {
    if (out.includes(secret)) {
      out = out.split(secret).join("[redacted]");
    }
  }
  return out;
}
