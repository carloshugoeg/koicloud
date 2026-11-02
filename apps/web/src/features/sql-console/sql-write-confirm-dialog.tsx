import type { RefObject } from "react";
import { ModalDialog } from "@/components/modal-dialog";

type SqlWriteConfirmDialogProps = {
  onCancel: () => void;
  onConfirm: () => void;
  returnFocusRef: RefObject<HTMLElement | null>;
};

export function SqlWriteConfirmDialog({
  onCancel,
  onConfirm,
  returnFocusRef,
}: SqlWriteConfirmDialogProps) {
  return (
    <ModalDialog
      titleId="sql-write-confirm-title"
      onClose={onCancel}
      returnFocusRef={returnFocusRef}
      data-testid="sql-write-confirm"
      closeLabel="Cerrar fondo del diálogo"
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      panelClassName="relative z-10 w-full max-w-lg overflow-hidden rounded-md border-2 border-koi bg-bone-raised shadow-dialog"
    >
      <div className="border-b border-koi bg-koi-soft px-5 py-3 text-sm text-ink">
        Modo escritura: las sentencias modifican datos reales.
      </div>
      <div className="space-y-3 p-5">
        <h3 id="sql-write-confirm-title" className="font-display text-2xl text-ink">
          Ejecutar en modo escritura
        </h3>
        <p className="text-sm text-ink">
          Esta sentencia cambia datos del pond. Cancelar no envía nada.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-line px-5 py-4">
        <button
          type="button"
          className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink focus-visible:outline-none focus-visible:shadow-focus"
          onClick={onCancel}
        >
          Cancelar
        </button>
        <span className="grow" />
        <button
          type="button"
          className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus-visible:outline-none focus-visible:shadow-focus"
          onClick={onConfirm}
          data-testid="sql-write-confirm-button"
        >
          Ejecutar escritura
        </button>
      </div>
    </ModalDialog>
  );
}
