import type { PondObservedState } from "@/api/hooks/ponds";

export interface PondStateMeta {
  label: string;
  badgeClass: string;
  cellClass: string;
  glyph: string;
}

export const POND_STATE_META: Record<PondObservedState, PondStateMeta> = {
  pending: {
    label: "En cola",
    badgeClass: "bg-bone-sunk text-ink",
    cellClass: "bg-bone-sunk border border-line-control",
    glyph: "◌",
  },
  provisioning: {
    label: "Aprovisionando…",
    badgeClass: "bg-turquoise-100 text-ink",
    cellClass: "bg-turquoise-300",
    glyph: "◐",
  },
  running: {
    label: "En línea",
    badgeClass: "bg-green-100 text-ink",
    cellClass: "bg-green-500",
    glyph: "●",
  },
  restoring: {
    label: "Restaurando…",
    badgeClass: "bg-turquoise-100 text-ink",
    cellClass: "bg-turquoise-300",
    glyph: "◐",
  },
  stopped: {
    label: "Detenido",
    badgeClass: "bg-bone-sunk text-ink",
    cellClass: "bg-bone-sunk border border-line-control",
    glyph: "■",
  },
  deleting: {
    label: "Eliminando…",
    badgeClass: "bg-koi-soft text-ink",
    cellClass: "bg-koi-soft",
    glyph: "◐",
  },
  deleted: {
    label: "Eliminado",
    badgeClass: "bg-bone-sunk text-ink-muted",
    cellClass: "bg-bone-sunk border border-line opacity-60",
    glyph: "✕",
  },
  failed: {
    label: "Con fallas",
    badgeClass: "bg-danger-soft text-danger",
    cellClass: "bg-koi",
    glyph: "✕",
  },
};

export function pondStateMeta(state: PondObservedState): PondStateMeta {
  return POND_STATE_META[state];
}
