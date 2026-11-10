import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const journey = path.dirname(fileURLToPath(import.meta.url));
const api = path.resolve(journey, "../../apps/api");
const homeUv = path.join(process.env.HOME ?? "", ".local/bin/uv");
const uv = fs.existsSync(homeUv) ? homeUv : "uv";

export const seedPath = "/tmp/koi-admin-users-seed.json";

export default function globalSetup() {
  const raw = execFileSync(
    uv,
    [
      "run",
      "python",
      "-c",
      "from tests.admin_users_probe import seed_admin_user_pages; print(seed_admin_user_pages())",
    ],
    { cwd: api, encoding: "utf8" },
  ).trim();
  fs.writeFileSync(seedPath, `${raw}\n`);
}
