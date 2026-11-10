import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RestoreJobBanner } from "@/features/ponds/restore-job-banner";

async function loadJobErrorSentence() {
  const modPath = "@/features/ponds/" + "job-error-text";
  const mod = await import(/* @vite-ignore */ modPath);
  return mod.jobErrorSentence as (lastError: string) => string;
}

describe("jobErrorSentence", () => {
  it("returns only the Spanish sentence, without a restore_failed prefix", async () => {
    const jobErrorSentence = await loadJobErrorSentence();
    expect(jobErrorSentence("restore_failed: No se pudo restaurar el pond.")).toBe(
      "No se pudo restaurar el pond.",
    );
  });

  it("returns only the Spanish sentence for backup_failed", async () => {
    const jobErrorSentence = await loadJobErrorSentence();
    expect(jobErrorSentence("backup_failed: No se pudo crear el respaldo.")).toBe(
      "No se pudo crear el respaldo.",
    );
  });

  it("leaves a bare code unchanged when there is no sentence", async () => {
    const jobErrorSentence = await loadJobErrorSentence();
    expect(jobErrorSentence("backup_not_found")).toBe("backup_not_found");
  });
});

describe("RestoreJobBanner", () => {
  it("shows the Spanish sentence without the restore_failed prefix", () => {
    render(
      <RestoreJobBanner
        jobId="job-1"
        job={{
          attempts: 1,
          claimed_at: "2026-11-06T12:00:00Z",
          completed_at: "2026-11-06T12:00:01Z",
          created_at: "2026-11-06T12:00:00Z",
          id: "job-1",
          last_error: "restore_failed: No se pudo restaurar el pond.",
          node_id: "node-1",
          pond_id: "pond-1",
          status: "failed",
          type: "restore_pond",
        }}
        readFailed={false}
        onRetry={() => undefined}
      />,
    );
    expect(screen.getByText("No se pudo restaurar el pond.", { exact: true })).toBeTruthy();
    expect(screen.queryByText(/restore_failed:/)).toBeNull();
  });
});
