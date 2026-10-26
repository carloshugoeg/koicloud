import type { components } from "@/api/schema";

type SubscriptionOut = components["schemas"]["SubscriptionOut"];

export type SubscriptionPhase =
  | "pending_payment"
  | "active"
  | "scheduled_cancel"
  | "canceled"
  | "expired"
  | "past_due";

export interface SubscriptionPhaseMeta {
  label: string;
  glyph: string;
  badgeClass: string;
}

export const PHASE_META: Record<SubscriptionPhase, SubscriptionPhaseMeta> = {
  pending_payment: {
    label: "Pago pendiente",
    glyph: "◌",
    badgeClass: "bg-bone-sunk text-ink",
  },
  active: {
    label: "Activa",
    glyph: "●",
    badgeClass: "bg-green-100 text-ink",
  },
  scheduled_cancel: {
    label: "Se cancela al corte",
    glyph: "◐",
    badgeClass: "bg-turquoise-100 text-ink",
  },
  canceled: {
    label: "Cancelada",
    glyph: "✕",
    badgeClass: "bg-bone-sunk text-ink",
  },
  expired: {
    label: "Vencida",
    glyph: "✕",
    badgeClass: "bg-bone-sunk text-ink",
  },
  past_due: {
    label: "Con atraso",
    glyph: "✕",
    badgeClass: "bg-danger-soft text-danger",
  },
};

export function subscriptionPhase(sub: SubscriptionOut): SubscriptionPhase {
  if (sub.status === "active" && sub.cancel_at_period_end) {
    return "scheduled_cancel";
  }
  return sub.status;
}

export function subscriptionPhaseMeta(sub: SubscriptionOut): SubscriptionPhaseMeta {
  return PHASE_META[subscriptionPhase(sub)];
}
