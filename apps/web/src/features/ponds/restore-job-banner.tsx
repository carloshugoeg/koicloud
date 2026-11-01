import type { PondJob } from "@/api/hooks/ponds";

const COPY = {
  queued: { lead: "Restauración encolada.", glyph: "◌" },
  running: { lead: "Restauración en curso.", glyph: "◐" },
  succeeded: { lead: "Restauración lista.", glyph: "●" },
  failed: { lead: "Restauración con fallas.", glyph: "✕" },
  lost: { lead: "Restauración perdida.", glyph: "✕" },
} as const;

export function RestoreJobBanner({ jobId, job }: { jobId: string; job: PondJob | undefined }) {
  const status = job?.status ?? "queued";
  const copy = status in COPY ? COPY[status as keyof typeof COPY] : COPY.queued;
  const failed = status === "failed";
  const tone = failed
    ? "border-line bg-danger-soft"
    : status === "succeeded"
      ? "border-line bg-green-100"
      : "border-line bg-turquoise-100";

  return (
    <div
      className={`rounded-md border px-4 py-3 text-sm text-ink ${tone}`}
      data-testid="restore-queued"
      role="status"
    >
      <p>
        <span aria-hidden>{copy.glyph}</span> {copy.lead} Job <span className="font-mono">{jobId}</span>{" "}
        · estado{" "}
        <span
          className={failed ? "font-mono text-danger" : "font-mono"}
          data-testid="restore-job-status"
        >{status}</span>
        .
      </p>
      {failed && job?.last_error ? (
        <p className="mt-1 font-mono text-xs text-ink">{job.last_error}</p>
      ) : null}
    </div>
  );
}
