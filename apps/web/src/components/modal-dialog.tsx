import {
  useEffect,
  useRef,
  type ReactNode,
  type RefObject,
} from "react";

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export type ModalDialogProps = {
  titleId: string;
  onClose: () => void;
  returnFocusRef: RefObject<HTMLElement | null>;
  children: ReactNode;
  "data-testid"?: string;
  initialFocusRef?: RefObject<HTMLElement | null>;
  className?: string;
  panelClassName?: string;
  closeLabel?: string;
};

export function ModalDialog({
  titleId,
  onClose,
  returnFocusRef,
  children,
  "data-testid": testId,
  initialFocusRef,
  className = "fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4",
  panelClassName = "relative z-10 w-full max-w-md overflow-hidden rounded-md border border-line bg-bone-raised shadow-dialog",
  closeLabel = "Cerrar fondo del diálogo",
}: ModalDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);

  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }

    const preferred = initialFocusRef?.current;
    if (preferred) {
      preferred.focus();
    } else {
      const first = dialog.querySelector<HTMLElement>(FOCUSABLE);
      first?.focus();
    }

    const returnTarget = returnFocusRef.current;

    function focusables(): HTMLElement[] {
      if (!dialogRef.current) return [];
      return Array.from(dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => !el.hasAttribute("disabled") && el.tabIndex !== -1,
      );
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const items = focusables();
      if (items.length === 0) {
        event.preventDefault();
        return;
      }

      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (active === first || !dialogRef.current?.contains(active)) {
          event.preventDefault();
          last.focus();
        }
      } else if (active === last || !dialogRef.current?.contains(active)) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      returnTarget?.focus();
    };
  }, [returnFocusRef, initialFocusRef]);

  return (
    <div className={className}>
      <button
        type="button"
        className="absolute inset-0 border-0 bg-transparent"
        aria-label={closeLabel}
        tabIndex={-1}
        onClick={() => onCloseRef.current()}
      />
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={panelClassName}
        data-testid={testId}
      >
        {children}
      </div>
    </div>
  );
}
