import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const journey = path.dirname(fileURLToPath(import.meta.url));
const api = path.resolve(journey, "../../apps/api");
const homeUv = path.join(process.env.HOME ?? "", ".local/bin/uv");
const uv = fs.existsSync(homeUv) ? homeUv : "uv";

export const pondIdPath = "/tmp/koi-sql-probe-pond-id";
export const demoUserIdPath = "/tmp/koi-sql-probe-user-id";

export default function globalSetup() {
  const raw = execFileSync(
    uv,
    [
      "run",
      "python",
      "-c",
      "from tests.sql_probe_pond import seed_probe_pond; p=seed_probe_pond(); print(p.pond_id); print(p.user_id)",
    ],
    { cwd: api, encoding: "utf8" },
  ).trim();
  const [pondId, userId] = raw.split(/\r?\n/);
  fs.writeFileSync(pondIdPath, `${pondId}\n`);
  fs.writeFileSync(demoUserIdPath, `${userId}\n`);
}
