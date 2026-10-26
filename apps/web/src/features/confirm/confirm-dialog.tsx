import { useEffect, useId, useRef, useState } from "react";
import { confirmCopy, type ConfirmView } from "@/features/confirm/proposal";

type ConfirmDialogProps = {
  view: Extract<ConfirmView, { kind: "dialog" }>;
  onConfirm: () => void;
  onDiscard: () => void;
  onDismiss: () => void;
};

export function ConfirmDialog({ view, onConfirm, onDiscard, onDismiss }: ConfirmDialogProps) {
  const [copied, setCopied] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();

  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    confirmRef.current?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        onDismiss();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) {
        return;
      }
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) {
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [onDismiss]);

  async function copyToken() {
    try {
      await navigator.clipboard.writeText(view.proposal.token);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="dialog-veil absolute inset-0 border-0"
        aria-label="Cerrar"
        tabIndex={-1}
        onClick={onDismiss}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-busy={view.pending !== null}
        data-testid="confirm-dialog"
        className="relative z-10 w-full min-w-0 max-w-lg overflow-hidden rounded-md border border-line-control bg-bone-raised shadow-dialog"
      >
        <div className="h-2 bg-marigold" data-testid="confirm-band" />
        <div className="space-y-4 p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
                {confirmCopy.overline}
              </p>
              <h2 id={titleId} className="mt-1 font-display text-2xl text-ink">
                {confirmCopy.title}
              </h2>
            </div>
            <div className="text-right">
              <p className="text-xs text-ink-muted">{confirmCopy.countdownLabel}</p>
              <p
                className="font-mono text-2xl tabular-nums text-warn"
                data-testid="confirm-countdown"
              >
                {view.countdown}
              </p>
            </div>
          </div>

          <p className="text-base leading-6 text-ink" data-testid="confirm-summary">
            {view.proposal.summary}
          </p>
          <p className="text-sm text-ink-muted">{confirmCopy.help}</p>

          <div className="flex flex-wrap items-center justify-between gap-2 rounded-sm border border-line bg-paper px-3 py-2">
            <p className="min-w-0 break-all font-mono text-xs text-ink" data-testid="confirm-token">
              {view.proposal.token}
            </p>
            <button
              type="button"
              className="h-9 shrink-0 rounded-sm px-3 text-sm font-medium text-turquoise-700 focus-visible:outline-none focus-visible:shadow-focus"
              onClick={() => {
                void copyToken();
              }}
            >
              {copied ? confirmCopy.copied : confirmCopy.copyToken}
            </button>
          </div>

          {view.failure ? (
            <div className="border-l-[3px] border-danger pl-3" role="alert" data-testid="confirm-failure">
              <p className="text-sm text-ink">{view.failure.message}</p>
              {view.failure.code ? (
                <p className="mt-1 font-mono text-xs text-ink-faint">{view.failure.code}</p>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center justify-end gap-3 border-t border-line px-5 py-4">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:outline-none focus-visible:shadow-focus disabled:border-line disabled:bg-bone-sunk disabled:text-ink-faint"
            disabled={!view.discardEnabled}
            onClick={onDiscard}
          >
            {view.pending === "discard" ? confirmCopy.discarding : confirmCopy.discard}
          </button>
          <button
            ref={confirmRef}
            type="button"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus-visible:outline-none focus-visible:shadow-focus disabled:bg-bone-sunk disabled:text-ink-faint"
            disabled={!view.confirmEnabled}
            onClick={onConfirm}
          >
            {view.pending === "confirm" ? confirmCopy.confirming : confirmCopy.confirm}
          </button>
        </div>
      </div>
    </div>
  );
}
