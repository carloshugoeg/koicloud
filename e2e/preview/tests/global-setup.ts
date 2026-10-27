import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const STORE_MEDIA =
  "/cursor/stores/bc-5a36cfa5-6bb5-4b3c-accc-c974d8337634/media/e2e-verify";

export function previewRoot(): string {
  return path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
}

export default function globalSetup(): void {
  const artifacts = path.join(previewRoot(), "artifacts");
  fs.mkdirSync(artifacts, { recursive: true });
  const media = process.env.KOI_E2E_MEDIA_DIR ?? STORE_MEDIA;
  fs.mkdirSync(media, { recursive: true });
  fs.writeFileSync(path.join(artifacts, "ui-results.json"), "[]\n");
}
