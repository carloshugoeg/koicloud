import type { Backup } from "@/api/hooks/ponds";

export function formatBytes(size: number): string {
  if (size <= 0) return "—";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

export function shortSha(sha: string): string {
  if (sha.length < 12) return sha;
  return `${sha.slice(0, 4)}…${sha.slice(-4)}`;
}

export function formatWhen(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`;
}

export function kindChipClass(kind: Backup["kind"]): string {
  if (kind === "pre_delete") return "bg-koi-soft text-ink";
  return "bg-bone-sunk text-ink";
}
