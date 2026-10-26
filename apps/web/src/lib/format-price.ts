import type { components } from "@/api/schema";

export type PlanPriceFields = Pick<
  components["schemas"]["PlanOut"],
  "unit_price" | "currency" | "billing_model" | "validity_minutes"
>;

/** Shared catalog price formatter — never hard-code plan amounts in UI. */
export function formatPrice(plan: Pick<PlanPriceFields, "unit_price" | "currency">): string {
  const amount = formatUnitAmount(plan.unit_price);
  return `${plan.currency} ${amount}`;
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

/** Checkout invoice preview from catalog unit_price (IVA 12% included in total). */
export function invoicePreviewFromPlan(
  plan: Pick<PlanPriceFields, "unit_price" | "billing_model">,
): { subtotal: string; iva: string; total: string } {
  if (plan.billing_model === "hourly" || plan.unit_price <= 0) {
    return { subtotal: "0.0000", iva: "0.0000", total: "0.0000" };
  }
  const total = plan.unit_price;
  const subtotal = total / 1.12;
  const iva = total - subtotal;
  return {
    subtotal: subtotal.toFixed(4),
    iva: iva.toFixed(4),
    total: total.toFixed(4),
  };
}

function formatUnitAmount(value: number): string {
  if (Number.isInteger(value)) {
    return String(value);
  }
  const fixed = value.toFixed(4);
  return fixed.replace(/\.?0+$/, "");
}
