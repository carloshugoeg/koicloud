import { useState } from "react";
import { problemToMessage } from "@/lib/errors";
import { confirmCopy, type ConfirmView } from "@/features/confirm/proposal";

type ConfirmDialogProps = {
  view: Extract<ConfirmView, { kind: "dialog" }>;
  onConfirm: () => void;
  onDiscard: () => void;
  onDismiss: () => void;
};

export function ConfirmDialog({
  view,
  onConfirm,
  onDiscard,
  onDismiss,
}: ConfirmDialogProps) {
  const [copied, setCopied] = useState(false);

  async function copyToken() {
    try {
      await navigator.clipboard.writeText(view.proposal.token);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1_200);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      data-testid="confirm-dialog"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onDismiss();
        }
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          onDismiss();
        }
      }}
    >
      <div className="w-full max-w-lg rounded-md border border-line-control bg-bone-raised shadow-dialog">
        <div className="h-2 bg-marigold" />
        <div className="space-y-4 p-5">
          <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">
            {confirmCopy.overline}
          </p>
          <h2 id="confirm-dialog-title" className="font-display text-2xl text-ink">
            {confirmCopy.title}
          </h2>
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
              {confirmCopy.countdownLabel}
            </p>
            <p
              className="font-mono text-2xl tabular-nums text-warn"
              data-testid="confirm-countdown"
            >
              {view.countdown}
            </p>
          </div>
          <p className="text-base leading-6 text-ink" data-testid="confirm-summary">
            {view.proposal.summary}
          </p>
          <p className="text-sm text-ink-muted">{confirmCopy.help}</p>
          <div className="flex flex-wrap items-center gap-3">
            <code
              className="font-mono text-xs text-ink break-all"
              data-testid="confirm-token"
            >
              {view.proposal.token}
            </code>
            <button
              type="button"
              className="text-xs font-medium text-turquoise-700 focus-visible:shadow-focus"
              onClick={() => void copyToken()}
            >
              {copied ? confirmCopy.copied : confirmCopy.copyToken}
            </button>
          </div>
          {view.failure ? (
            <div className="border-l-[3px] border-danger pl-3" role="alert">
              <p className="text-sm text-ink">{view.failure.message}</p>
              {view.failure.code ? (
                <p className="mt-1 font-mono text-xs text-ink-faint">{view.failure.code}</p>
              ) : null}
            </div>
          ) : view.expired ? (
            <div className="border-l-[3px] border-danger pl-3" role="alert">
              <p className="text-sm text-ink">
                {problemToMessage({
                  code: "confirmation_expired",
                  message: "confirmation_expired",
                  request_id: "local",
                })}
              </p>
            </div>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-3 border-t border-line px-5 py-4">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:outline-none focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
            onClick={onDiscard}
            disabled={!view.discardEnabled}
            data-testid="confirm-discard"
          >
            {view.pending === "discard" ? confirmCopy.discarding : confirmCopy.discard}
          </button>
          <span className="grow" />
          <button
            type="button"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus-visible:outline-none focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
            onClick={onConfirm}
            disabled={!view.confirmEnabled}
            data-testid="confirm-submit"
          >
            {view.pending === "confirm" ? confirmCopy.confirming : confirmCopy.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
