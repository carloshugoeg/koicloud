import { describe, expect, it } from "vitest";
import { formatPeriod, formatPrice } from "@/lib/format-price";

const sandbox = {
  postpaid: false,
  price_monthly_usd: 0,
  validity_minutes: 10,
};

const micro = {
  postpaid: false,
  price_monthly_usd: 5,
  validity_minutes: 43_200,
};

const pro = {
  postpaid: true,
  price_monthly_usd: 0,
  validity_minutes: 43_200,
};

describe("formatPrice", () => {
  it("prints monthly dollars from the plan", () => {
    expect(formatPrice(micro)).toBe("$5");
    expect(formatPrice(sandbox)).toBe("$0");
  });

  it("prints Pospago when postpaid has no monthly rate", () => {
    expect(formatPrice(pro)).toBe("Pospago");
    expect(formatPeriod(pro)).toBeNull();
    expect(formatPrice(pro)).not.toMatch(/0\.02/);
  });

  it("keeps a short free window and a monthly period", () => {
    expect(formatPeriod(sandbox)).toBe("10 min");
    expect(formatPeriod(micro)).toBe("al mes");
  });

  it("does not invent an hourly rate for a priced postpaid plan", () => {
    expect(
      formatPrice({ postpaid: true, price_monthly_usd: 12, validity_minutes: 43_200 }),
    ).toBe("$12");
    expect(
      formatPeriod({ postpaid: true, price_monthly_usd: 12, validity_minutes: 43_200 }),
    ).toBe("al mes");
  });
});
