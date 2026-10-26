import type { components } from "@/api/schema";

type PlanPrice = Pick<
  components["schemas"]["PlanOut"],
  "postpaid" | "price_monthly_usd" | "validity_minutes"
>;

const DAY_MINUTES = 24 * 60;

function formatUsd(amount: number): string {
  const text = Number.isInteger(amount) ? String(amount) : amount.toFixed(2);
  return `$${text}`;
}

/** Monthly money from the plan, or Pospago when the API has no monthly rate. */
export function formatPrice(plan: PlanPrice): string {
  if (plan.postpaid && plan.price_monthly_usd === 0) {
    return "Pospago";
  }
  return formatUsd(plan.price_monthly_usd);
}

/** Period label that the API can support. Null when there is nothing honest to say. */
export function formatPeriod(plan: PlanPrice): string | null {
  if (plan.postpaid && plan.price_monthly_usd === 0) {
    return null;
  }
  if (
    plan.price_monthly_usd === 0 &&
    plan.validity_minutes > 0 &&
    plan.validity_minutes < DAY_MINUTES
  ) {
    return `${plan.validity_minutes} min`;
  }
  if (plan.price_monthly_usd === 0) {
    return null;
  }
  return "al mes";
}
