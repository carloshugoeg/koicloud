import { useRef, useState } from "react";
import { InviteAgentDialog } from "@/features/ponds/invite-agent-dialog";

type InviteAgentButtonProps = {
  pondId: string;
  disabled?: boolean;
};

export function InviteAgentButton({ pondId, disabled = false }: InviteAgentButtonProps) {
  const [open, setOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-turquoise-700 focus:shadow-focus disabled:border-line-control disabled:text-ink-faint"
        data-testid="open-invite-agent"
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        Invitar agente
      </button>
      {open ? (
        <InviteAgentDialog
          pondId={pondId}
          returnFocusRef={buttonRef}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </>
  );
}
