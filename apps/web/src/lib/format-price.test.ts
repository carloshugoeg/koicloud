import { describe, expect, it } from "vitest";
import { formatPrice, formatPricePeriod, formatPriceWithPeriod } from "@/lib/format-price";

describe("formatPrice", () => {
  it("formats monthly amounts with 4 decimals", () => {
    expect(formatPrice({ unit_price: 5, currency: "USD" })).toBe("USD 5.0000");
  });

  it("formats zero as USD 0.0000", () => {
    expect(formatPrice({ unit_price: 0, currency: "USD" })).toBe("USD 0.0000");
  });

  it("formats Pro hourly as USD 0.0200 (never USD 0.00)", () => {
    expect(formatPrice({ unit_price: 0.02, currency: "USD" })).toBe("USD 0.0200");
    expect(formatPrice({ unit_price: 0.02, currency: "USD" })).not.toBe("USD 0.00");
  });

  it("keeps four decimals for fractional monthly prices", () => {
    expect(formatPrice({ unit_price: 7.5, currency: "USD" })).toBe("USD 7.5000");
  });
});

describe("formatPricePeriod", () => {
  it("labels monthly catalog periods", () => {
    expect(
      formatPricePeriod({ billing_model: "monthly", validity_minutes: 43_200 }),
    ).toBe("/ mes");
  });

  it("labels hourly catalog periods", () => {
    expect(
      formatPricePeriod({ billing_model: "hourly", validity_minutes: 43_200 }),
    ).toBe("/ hora");
  });

  it("labels short sandbox validity", () => {
    expect(
      formatPricePeriod({ billing_model: "monthly", validity_minutes: 10 }),
    ).toBe("/ 10 min");
  });
});

describe("formatPriceWithPeriod", () => {
  it("joins Pro hourly catalog price and period", () => {
    expect(
      formatPriceWithPeriod({
        unit_price: 0.02,
        currency: "USD",
        billing_model: "hourly",
        validity_minutes: 43_200,
      }),
    ).toBe("USD 0.0200 / hora");
  });
});
