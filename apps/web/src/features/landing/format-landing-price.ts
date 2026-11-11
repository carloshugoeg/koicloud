import type { PlanOut } from "@/api/hooks";

/** Marketing price on the public landing. Keeps invoices on formatPrice (4 decimals). */
export function formatLandingPrice(
  plan: Pick<PlanOut, "id" | "unit_price" | "billing_model">,
): string {
  if (plan.id === "sandbox" || Number(plan.unit_price) === 0) {
    return "Gratis";
  }

  const amount = Number(plan.unit_price);
  const pretty =
    Number.isInteger(amount) || amount === Math.trunc(amount)
      ? String(Math.trunc(amount))
      : amount.toFixed(2).replace(/\.?0+$/, "");

  if (plan.billing_model === "hourly") {
    return `$${pretty}/h`;
  }

  return `$${pretty}/mes`;
}
