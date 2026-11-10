import type { PondJob } from "@/api/hooks/ponds";
import { jobErrorSentence } from "@/features/ponds/job-error-text";

const COPY = {
  queued: { lead: "Restauración encolada.", glyph: "◌" },
  running: { lead: "Restauración en curso.", glyph: "◐" },
  succeeded: { lead: "Restauración lista.", glyph: "●" },
  failed: { lead: "Restauración con fallas.", glyph: "✕" },
  lost: { lead: "Restauración perdida.", glyph: "✕" },
} as const;

export function RestoreJobBanner({
  jobId,
  job,
  readFailed,
  onRetry,
}: {
  jobId: string;
  job: PondJob | undefined;
  readFailed: boolean;
  onRetry: () => void;
}) {
  if (readFailed) {
    return (
      <div
        className="rounded-md border border-line bg-danger-soft px-4 py-3 text-sm text-ink"
        data-testid="restore-job-error"
        role="alert"
      >
        <p>
          <span aria-hidden>✕</span> No pudimos leer el estado de la restauración.
        </p>
        <button
          type="button"
          className="mt-3 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus:shadow-focus"
          onClick={onRetry}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const status = job?.status ?? "queued";
  const copy = status in COPY ? COPY[status as keyof typeof COPY] : COPY.queued;
  const broken = status === "failed" || status === "lost";
  const tone = broken
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
        <span aria-hidden>{copy.glyph}</span> <span>{copy.lead}</span> Job <span className="font-mono">{jobId}</span>{" "}
        · estado{" "}
        <span
          className={broken ? "font-mono text-danger" : "font-mono"}
          data-testid="restore-job-status"
        >{status}</span>
        .
      </p>
      {broken && job?.last_error ? (
        <p className="mt-1 font-mono text-xs text-ink">{jobErrorSentence(job.last_error)}</p>
      ) : null}
    </div>
  );
}
