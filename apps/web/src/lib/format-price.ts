import type { components } from "@/api/schema";

export type PlanPriceFields = Pick<
  components["schemas"]["PlanOut"],
  "unit_price" | "currency" | "billing_model" | "validity_minutes"
>;

/** Shared USD formatter — always 4 decimals; never hard-code plan amounts in UI. */
export function formatPrice(
  plan: Pick<PlanPriceFields, "unit_price" | "currency"> | { unit_price: number; currency: "USD" | string },
): string {
  return `${plan.currency} ${Number(plan.unit_price).toFixed(4)}`;
}

/** Period label for plan cards and comparison rows. */
export function formatPricePeriod(
  plan: Pick<PlanPriceFields, "billing_model" | "validity_minutes">,
): string {
  if (plan.billing_model === "hourly") {
    return "/ hora";
  }
  if (plan.validity_minutes > 0 && plan.validity_minutes < 60 * 24) {
    return `/ ${plan.validity_minutes} min`;
  }
  return "/ mes";
}

/** Comparison-table cell: price + period in one string. */
export function formatPriceWithPeriod(plan: PlanPriceFields): string {
  return `${formatPrice(plan)} ${formatPricePeriod(plan)}`;
}
