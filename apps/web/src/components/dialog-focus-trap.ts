export const DIALOG_FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function dialogFocusables(dialog: HTMLElement): HTMLElement[] {
  return Array.from(dialog.querySelectorAll<HTMLElement>(DIALOG_FOCUSABLE)).filter(
    (el) => !el.hasAttribute("disabled") && el.tabIndex !== -1,
  );
}

export function trapDialogTab(event: KeyboardEvent, dialog: HTMLElement): void {
  if (event.key !== "Tab") {
    return;
  }

  const items = dialogFocusables(dialog);
  if (items.length === 0) {
    event.preventDefault();
    return;
  }

  const first = items[0];
  const last = items[items.length - 1];
  const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  if (event.shiftKey) {
    if (active === first || !dialog.contains(active)) {
      event.preventDefault();
      last.focus();
    }
    return;
  }

  if (active === last || !dialog.contains(active)) {
    event.preventDefault();
    first.focus();
  }
}
