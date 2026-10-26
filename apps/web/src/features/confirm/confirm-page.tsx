import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  useConfirmActionMutation,
  useDiscardConfirmationMutation,
} from "@/api/hooks/confirmations";
import { DataStateEmpty } from "@/components/data-state";
import { ConfirmDialog } from "@/features/confirm/confirm-dialog";
import {
  confirmCopy,
  confirmView,
  formatCountdown,
  parseConfirmLocation,
} from "@/features/confirm/proposal";

export function ConfirmPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const confirmMutation = useConfirmActionMutation();
  const discardMutation = useDiscardConfirmationMutation();
  const [now, setNow] = useState(() => new Date());
  const [intent, setIntent] = useState<"confirm" | "discard" | null>(null);

  const arrival = useMemo(
    () => parseConfirmLocation({ search: location.search, state: location.state }),
    [location.search, location.state],
  );

  useEffect(() => {
    if (arrival.kind !== "ready") {
      return;
    }
    const id = window.setInterval(() => setNow(new Date()), 1_000);
    return () => window.clearInterval(id);
  }, [arrival.kind]);

  const error =
    intent === "confirm"
      ? confirmMutation.error
      : intent === "discard"
        ? discardMutation.error
        : confirmMutation.error ?? discardMutation.error;

  const view = confirmView({
    arrival,
    now,
    pending: intent,
    error,
  });

  async function handleConfirm() {
    if (arrival.kind !== "ready" || intent !== null) {
      return;
    }
    if (formatCountdown(arrival.proposal.expiresAt, new Date()).expired) {
      return;
    }
    setIntent("confirm");
    try {
      await confirmMutation.mutateAsync(arrival.proposal.token);
      navigate("/app", {
        replace: true,
        state: { notice: { text: confirmCopy.confirmed } },
      });
    } catch {
      // failure stays on the mutation for confirmView
    } finally {
      setIntent(null);
    }
  }

  async function handleDiscard() {
    if (arrival.kind !== "ready" || intent !== null) {
      return;
    }
    setIntent("discard");
    try {
      await discardMutation.mutateAsync(arrival.proposal.token);
      navigate("/app", {
        replace: true,
        state: { notice: { text: confirmCopy.discarded } },
      });
    } catch {
      // failure stays on the mutation for confirmView
    } finally {
      setIntent(null);
    }
  }

  if (view.kind === "invalid") {
    const description =
      view.reason === "disputed" ? confirmCopy.disputedBody : confirmCopy.invalidBody;
    return (
      <div className="py-6" data-testid="confirm-invalid">
        <DataStateEmpty
          title={confirmCopy.invalidTitle}
          description={description}
          action={
            <Link
              to="/app"
              className="inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
            >
              {confirmCopy.back}
            </Link>
          }
        />
      </div>
    );
  }

  return (
    <ConfirmDialog
      view={view}
      onConfirm={() => void handleConfirm()}
      onDiscard={() => void handleDiscard()}
      onDismiss={() => navigate("/app")}
    />
  );
}
