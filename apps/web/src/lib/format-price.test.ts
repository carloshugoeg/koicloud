import { describe, expect, it } from "vitest";
import {
  formatPrice,
  formatPricePeriod,
  formatPriceWithPeriod,
  invoicePreviewFromPlan,
} from "@/lib/format-price";

describe("formatPrice", () => {
  it("formats monthly Micro", () => {
    expect(formatPrice({ unit_price: 5, currency: "USD" })).toBe("USD 5");
  });

  it("formats monthly Sandbox zero", () => {
    expect(formatPrice({ unit_price: 0, currency: "USD" })).toBe("USD 0");
  });

  it("formats hourly Pro without showing USD 0.00", () => {
    expect(formatPrice({ unit_price: 0.02, currency: "USD" })).toBe("USD 0.02");
  });

  it("formats fractional monthly amounts from the API", () => {
    expect(formatPrice({ unit_price: 7.5, currency: "USD" })).toBe("USD 7.5");
  });
});

describe("formatPricePeriod", () => {
  it("returns / mes for monthly plans", () => {
    expect(
      formatPricePeriod({ billing_model: "monthly", validity_minutes: 43_200 }),
    ).toBe("/ mes");
  });

  it("returns / hora for hourly plans", () => {
    expect(
      formatPricePeriod({ billing_model: "hourly", validity_minutes: 43_200 }),
    ).toBe("/ hora");
  });

  it("returns minutes for short-lived monthly plans", () => {
    expect(
      formatPricePeriod({ billing_model: "monthly", validity_minutes: 10 }),
    ).toBe("/ 10 min");
  });
});

describe("formatPriceWithPeriod", () => {
  it("combines price and period for comparison rows", () => {
    expect(
      formatPriceWithPeriod({
        unit_price: 0.02,
        currency: "USD",
        billing_model: "hourly",
        validity_minutes: 43_200,
      }),
    ).toBe("USD 0.02 / hora");
  });
});

describe("invoicePreviewFromPlan", () => {
  it("splits IVA for monthly Micro from unit_price", () => {
    expect(invoicePreviewFromPlan({ unit_price: 5, billing_model: "monthly" })).toEqual({
      subtotal: "4.4643",
      iva: "0.5357",
      total: "5.0000",
    });
  });

  it("returns zeros for hourly Pro preview", () => {
    expect(invoicePreviewFromPlan({ unit_price: 0.02, billing_model: "hourly" })).toEqual({
      subtotal: "0.0000",
      iva: "0.0000",
      total: "0.0000",
    });
  });
});
