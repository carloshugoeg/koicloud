import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { argvForSpawn, runPlan } from "./run.mjs";
import {
  PlanError,
  checkPreviewUrl,
  childEnv,
  initialState,
  parsePlan,
  redact,
  reduce,
} from "./reduce.mjs";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const planPath = path.join(repoRoot, "scripts/pregate/plan.json");
const policy = {
  denyHosts: ["localhost", "127.0.0.1", "::1", "0.0.0.0"],
  requireHttps: true,
  requireHostSuffix: ".vercel.app",
};

function shellPlan(steps, extra = {}) {
  return {
    version: 1,
    browserPath: "e2e/.browsers",
    preview: policy,
    forbiddenEnvKeys: ["VITE_ENABLE_MOCKS", "VERCEL_ENV"],
    inheritEnv: ["PATH", "HOME"],
    redactEnvKeys: ["KOI_GATE_ADMIN_PASSWORD"],
    steps,
    ...extra,
  };
}

async function readPlan() {
  return JSON.parse(await readFile(planPath, "utf8"));
}

test("parsePlan resolves the shared browser path and the suite ports", async () => {
  const plan = parsePlan(await readPlan(), repoRoot);
  const browsers = path.resolve(repoRoot, "e2e/.browsers");
  assert.equal(plan.browserPath, browsers);
  const chromium = plan.steps.find((step) => step.id === "playwright-chromium");
  assert.equal(chromium.env.PLAYWRIGHT_BROWSERS_PATH, browsers);
  const group = plan.steps.find((step) => step.kind === "parallel");
  assert.equal(group.env.PLAYWRIGHT_BROWSERS_PATH, browsers);
  assert.equal(group.env.CI, "true");
  const ports = new Map(group.members.flatMap((member) => member.locks.map((lock) => [member.id, lock.port])));
  const pondConfig = await readFile(path.join(repoRoot, "e2e/pond-lifecycle/playwright.config.ts"), "utf8");
  const dialogConfig = await readFile(path.join(repoRoot, "e2e/dialog-viewport/playwright.config.ts"), "utf8");
  assert.match(pondConfig, /--port 5173\b/);
  assert.match(dialogConfig, /const port = 5174;/);
  assert.equal(ports.get("e2e-pond-lifecycle"), 5173);
  assert.equal(ports.get("e2e-dialog-viewport"), 5174);
  const preview = group.members.find((member) => member.id === "e2e-preview-login");
  assert.equal(preview.preview, true);
  assert.equal(preview.argv.includes("--grep"), false);
  assert.equal(JSON.stringify(plan).includes("$browserPath"), false);
});

test("parsePlan rejects a plan that cannot be run", async () => {
  const raw = await readPlan();
  assert.throws(() => parsePlan({ ...raw, version: 2 }, repoRoot), PlanError);
  assert.throws(() => parsePlan({ ...raw, steps: [] }, repoRoot), PlanError);
  const second = structuredClone(raw);
  second.steps.push(structuredClone(raw.steps.at(-1)));
  second.steps.at(-1).id = "e2e-again";
  assert.throws(() => parsePlan(second, repoRoot), /one parallel group/);
  const dup = structuredClone(raw);
  dup.steps[1].id = dup.steps[0].id;
  assert.throws(() => parsePlan(dup, repoRoot), /duplicate id/);
  const emptyArgv = structuredClone(raw);
  emptyArgv.steps[0].argv = [];
  assert.throws(() => parsePlan(emptyArgv, repoRoot), /argv/);
  const grep = structuredClone(raw);
  const preview = grep.steps.at(-1).members.find((member) => member.preview);
  preview.argv = ["npx", "playwright", "test", "--grep", "admin"];
  assert.throws(() => parsePlan(grep, repoRoot), /--grep/);
  const mocks = structuredClone(raw);
  mocks.steps[0].env = { VITE_ENABLE_MOCKS: "true" };
  assert.throws(() => parsePlan(mocks, repoRoot), /VITE_ENABLE_MOCKS/);
  const clash = structuredClone(raw);
  for (const member of clash.steps.at(-1).members) {
    member.locks = [{ kind: "tcp", port: 5173 }];
  }
  assert.throws(() => parsePlan(clash, repoRoot), /5173/);
  const emptyGroup = structuredClone(raw);
  emptyGroup.steps.at(-1).members = [];
  assert.throws(() => parsePlan(emptyGroup, repoRoot), /members/);
});

test("reduce fail-fast skips later steps and waits for the parallel group", () => {
  const plan = parsePlan(
    shellPlan([
      { kind: "serial", id: "first", title: "First", cwd: ".", argv: ["node", "-e", "process.exit(0)"] },
      { kind: "serial", id: "second", title: "Second", cwd: ".", argv: ["node", "-e", "process.exit(0)"] },
      {
        kind: "parallel",
        id: "group",
        title: "Group",
        env: {},
        members: [
          { id: "left", title: "Left", cwd: ".", argv: ["node", "-v"], locks: [{ kind: "tcp", port: 5173 }] },
          { id: "right", title: "Right", cwd: ".", argv: ["node", "-v"], locks: [{ kind: "tcp", port: 5174 }] },
        ],
      },
    ]),
    repoRoot,
  );
  let state = initialState();
  let step = reduce(plan, state, { type: "begin" });
  assert.equal(step.spawn[0].id, "first");
  state = reduce(plan, step.state, { type: "exited", id: "first", code: 4 }).state;
  assert.equal(state.phase, "failed");
  assert.equal(state.code, 4);
  assert.deepEqual(state.skipped, ["second", "group", "left", "right"]);
  assert.deepEqual(reduce(plan, state, { type: "begin" }).spawn, []);

  state = initialState();
  state = reduce(plan, state, { type: "begin" }).state;
  state = reduce(plan, state, { type: "exited", id: "first", code: 0 }).state;
  state = reduce(plan, state, { type: "begin" }).state;
  state = reduce(plan, state, { type: "exited", id: "second", code: 0 }).state;
  const started = reduce(plan, state, { type: "begin" });
  const original = started.state.pending;
  const mid = reduce(plan, started.state, { type: "exited", id: "left", code: 1 });
  assert.equal(original.has("left"), true);
  assert.equal(mid.spawn.length, 0);
  assert.equal(mid.state.phase, "parallel");
  const done = reduce(plan, mid.state, { type: "exited", id: "right", code: 0 });
  assert.equal(done.state.phase, "failed");
  assert.equal(done.state.code, 1);
  assert.deepEqual(done.state.skipped, []);
  assert.throws(() => reduce(plan, started.state, { type: "begin" }), PlanError);
});

test("checkPreviewUrl and childEnv keep production and localhost out", () => {
  assert.equal(checkPreviewUrl("https://koicloud-web.vercel.app/login", policy), null);
  assert.match(checkPreviewUrl("http://koicloud-web.vercel.app", policy), /https/);
  assert.match(checkPreviewUrl("https://localhost/app", policy), /denied/);
  assert.match(checkPreviewUrl("https://127.0.0.1", policy), /denied/);
  assert.match(checkPreviewUrl("https://example.com", policy), /\.vercel\.app/);
  assert.match(checkPreviewUrl("not a url", policy), /not a URL/);

  const plan = parsePlan(
    shellPlan(
      [
        {
          kind: "parallel",
          id: "e2e",
          title: "Playwright",
          env: {},
          members: [
            {
              id: "preview",
              title: "Preview",
              cwd: ".",
              argv: ["node", "-e", "process.exit(0)"],
              locks: [],
              preview: true,
            },
          ],
        },
      ],
      {
        inheritEnv: ["PATH", "VITE_ENABLE_MOCKS", "VERCEL_ENV", "PLAYWRIGHT_BASE_URL"],
      },
    ),
    repoRoot,
  );
  const command = plan.steps[0].members[0];
  const parent = {
    PATH: "/usr/bin",
    VITE_ENABLE_MOCKS: "true",
    VERCEL_ENV: "production",
    PLAYWRIGHT_BASE_URL: "http://127.0.0.1:5173",
    KOI_GATE_ADMIN_PASSWORD: "secret-value",
  };
  const blocked = childEnv(plan, parent, command, {});
  assert.equal(blocked.ok, false);
  const open = childEnv(plan, { PATH: "/usr/bin", VITE_ENABLE_MOCKS: "true", VERCEL_ENV: "production" }, command, {});
  assert.equal(open.ok, true);
  assert.equal(open.env.PATH, "/usr/bin");
  assert.equal("VITE_ENABLE_MOCKS" in open.env, false);
  assert.equal("VERCEL_ENV" in open.env, false);
  assert.equal("PLAYWRIGHT_BASE_URL" in open.env, false);
  const allowed = childEnv(
    plan,
    { PLAYWRIGHT_BASE_URL: "https://branch.vercel.app" },
    command,
    {},
  );
  assert.equal(allowed.ok, true);
  assert.equal(allowed.env.PLAYWRIGHT_BASE_URL, "https://branch.vercel.app");
  const poisoned = childEnv(plan, {}, { ...command, env: { VERCEL_ENV: "preview" } }, {});
  assert.equal(poisoned.ok, false);
});

test("redact replaces secret values and ignores empty ones", () => {
  assert.equal(redact("login secret-value ok", ["", "secret-value"]), "login [redacted] ok");
  assert.equal(redact("untouched", [""]), "untouched");
});

test("runPlan stops before a later sentinel and redacts child output", async () => {
  const sentinel = path.join(repoRoot, "scripts/pregate/fixtures/sentinel-did-run");
  await rm(sentinel, { force: true });
  const lines = [];
  const original = console.log;
  console.log = (...parts) => {
    lines.push(parts.join(" "));
  };
  try {
    const code = await runPlan(path.join(repoRoot, "scripts/pregate/fixtures/fail-fast.json"), process.env);
    assert.equal(code, 3);
    assert.equal(existsSync(sentinel), false);
    const text = lines.join("\n");
    assert.match(text, /pregate fail boom exit 3/);
    assert.match(text, /pregate skipped sentinel/);
    assert.equal(text.includes("sentinel-did-run"), false);

    const directory = await mkdtemp(path.join(tmpdir(), "pregate-"));
    const secret = "gate-admin-secret-do-not-print";
    const fixture = path.join(directory, "plan.json");
    await writeFile(
      fixture,
      JSON.stringify(
        shellPlan(
          [
            {
              kind: "parallel",
              id: "e2e",
              title: "Playwright",
              env: {},
              members: [
                {
                  id: "e2e-preview-login",
                  title: "preview-login",
                  cwd: ".",
                  argv: ["node", "-e", "console.log(process.env.KOI_GATE_ADMIN_PASSWORD || 'none')"],
                  locks: [],
                  preview: true,
                },
              ],
            },
          ],
          {
            inheritEnv: ["PATH", "KOI_GATE_ADMIN_PASSWORD"],
            redactEnvKeys: ["KOI_GATE_ADMIN_PASSWORD"],
          },
        ),
      ),
    );
    lines.length = 0;
    const parent = { ...process.env, KOI_GATE_ADMIN_PASSWORD: secret };
    delete parent.KOI_GATE_ADMIN_EMAIL;
    const previewCode = await runPlan(fixture, parent);
    assert.equal(previewCode, 0);
    const previewText = lines.join("\n");
    assert.match(previewText, /KOI_GATE_ADMIN_EMAIL missing/);
    assert.match(previewText, /KOI_GATE_ADMIN_PASSWORD set/);
    assert.match(previewText, /\[redacted\]/);
    assert.equal(previewText.includes(secret), false);
    assert.equal(previewText.includes("--grep-invert"), false);
    await rm(directory, { recursive: true, force: true });
  } finally {
    console.log = original;
  }
});

test("argvForSpawn skips gate admin when KOI_GATE_ADMIN_* are missing", () => {
  const spawnSpec = { argv: ["npx", "playwright", "test"] };
  const preview = { preview: true };
  const without = argvForSpawn(spawnSpec, preview, {});
  assert.deepEqual(without, ["npx", "playwright", "test", "--grep-invert", "gate admin login"]);
  const withAdmin = argvForSpawn(spawnSpec, preview, {
    KOI_GATE_ADMIN_EMAIL: "demo@example.com",
    KOI_GATE_ADMIN_PASSWORD: "x",
  });
  assert.deepEqual(withAdmin, ["npx", "playwright", "test"]);
  const pond = argvForSpawn(spawnSpec, { preview: false }, {});
  assert.deepEqual(pond, ["npx", "playwright", "test"]);
});

test("node can see PATH for the fixture commands", () => {
  const seen = spawnSync("node", ["-e", "process.exit(0)"], { encoding: "utf8" });
  assert.equal(seen.status, 0);
});
