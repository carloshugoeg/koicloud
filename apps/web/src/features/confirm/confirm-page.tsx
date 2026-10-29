import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  useConfirmActionMutation,
  useDiscardConfirmationMutation,
} from "@/api/hooks";
import { DataStateEmpty } from "@/components/data-state";
import { ConfirmDialog } from "@/features/confirm/confirm-dialog";
import {
  confirmCopy,
  confirmView,
  formatCountdown,
  parseConfirmLocation,
  type ConfirmArrival,
} from "@/features/confirm/proposal";

export function ConfirmPage() {
  const location = useLocation();
  const arrival = useMemo(
    () => parseConfirmLocation({ search: location.search, state: location.state }),
    [location.search, location.state],
  );
  const proposalKey =
    arrival.kind === "ready"
      ? `${arrival.proposal.token}\0${arrival.proposal.summary}\0${arrival.proposal.expiresAt.toISOString()}`
      : `invalid:${arrival.reason}`;

  return <ConfirmSession key={proposalKey} arrival={arrival} />;
}

function ConfirmSession({ arrival }: { arrival: ConfirmArrival }) {
  const navigate = useNavigate();
  const confirmAction = useConfirmActionMutation();
  const discardConfirmation = useDiscardConfirmationMutation();
  const [now, setNow] = useState(() => new Date());
  const [intent, setIntent] = useState<"confirm" | "discard" | null>(null);
  const intentRef = useRef<"confirm" | "discard" | null>(null);

  useEffect(() => {
    if (arrival.kind !== "ready") {
      return;
    }
    const timer = window.setInterval(() => {
      setNow(new Date());
    }, 1000);
    return () => {
      window.clearInterval(timer);
    };
  }, [arrival.kind]);

  const onDismiss = useCallback(() => {
    navigate("/app");
  }, [navigate]);

  async function run(kind: "confirm" | "discard") {
    if (intentRef.current !== null || arrival.kind !== "ready") {
      return;
    }
    if (kind === "confirm" && formatCountdown(arrival.proposal.expiresAt, new Date()).expired) {
      setNow(new Date());
      return;
    }
    intentRef.current = kind;
    setIntent(kind);
    const token = arrival.proposal.token;
    if (kind === "confirm") {
      discardConfirmation.reset();
    } else {
      confirmAction.reset();
    }
    try {
      if (kind === "confirm") {
        await confirmAction.mutateAsync(token);
        navigate("/app", {
          replace: true,
          state: { notice: { text: confirmCopy.confirmed } },
        });
      } else {
        await discardConfirmation.mutateAsync(token);
        navigate("/app", {
          replace: true,
          state: { notice: { text: confirmCopy.discarded } },
        });
      }
    } catch {
      return;
    } finally {
      intentRef.current = null;
      setIntent(null);
    }
  }

  if (arrival.kind === "invalid") {
    return (
      <DataStateEmpty
        title={confirmCopy.invalidTitle}
        description={
          arrival.reason === "disputed" ? confirmCopy.disputedBody : confirmCopy.invalidBody
        }
        testId="confirm-invalid"
        action={
          <Link
            className="inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900 focus-visible:outline-none focus-visible:shadow-focus"
            to="/app"
          >
            {confirmCopy.back}
          </Link>
        }
      />
    );
  }

  const view = confirmView({
    arrival,
    now,
    pending: intent,
    error: confirmAction.error ?? discardConfirmation.error,
  });
  if (view.kind !== "dialog") {
    return null;
  }

  return (
    <ConfirmDialog
      view={view}
      onConfirm={() => {
        void run("confirm");
      }}
      onDiscard={() => {
        void run("discard");
      }}
      onDismiss={onDismiss}
    />
  );
}
