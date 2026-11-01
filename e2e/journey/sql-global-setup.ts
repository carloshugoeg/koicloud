import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const journey = path.dirname(fileURLToPath(import.meta.url));
const api = path.resolve(journey, "../../apps/api");
const uv = path.join(process.env.HOME ?? "", ".local/bin/uv");

export const pondIdPath = "/tmp/koi-sql-probe-pond-id";

export default function globalSetup() {
  const pondId = execFileSync(
    uv,
    [
      "run",
      "python",
      "-c",
      "from tests.sql_probe_pond import seed_probe_pond; print(seed_probe_pond().pond_id)",
    ],
    { cwd: api, encoding: "utf8" },
  ).trim();
  fs.writeFileSync(pondIdPath, `${pondId}\n`);
}
