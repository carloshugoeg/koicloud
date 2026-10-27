import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const STORE_MEDIA =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/e2e-verify";

export function previewRoot(): string {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
}

function ensureWritableDir(dir: string): boolean {
  try {
    fs.mkdirSync(dir, { recursive: true });
    fs.accessSync(dir, fs.constants.W_OK);
    return true;
  } catch {
    return false;
  }
}

export function resolveMediaDir(): string | null {
  const fromEnv = process.env.KOI_E2E_MEDIA_DIR;
  if (fromEnv && fromEnv.trim()) {
    return ensureWritableDir(fromEnv) ? fromEnv : null;
  }
  return ensureWritableDir(STORE_MEDIA) ? STORE_MEDIA : null;
}

export default function globalSetup(): void {
  const artifacts = path.join(previewRoot(), "artifacts");
  fs.mkdirSync(artifacts, { recursive: true });
  resolveMediaDir();
  fs.writeFileSync(path.join(artifacts, "ui-results.json"), "[]\n");
}
