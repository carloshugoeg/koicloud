import { formatLandingPrice } from "@/features/landing/format-landing-price";

describe("formatLandingPrice", () => {
  it("renders Micro as $5/mes", () => {
    expect(
      formatLandingPrice({ id: "micro", unit_price: 5, billing_model: "monthly" }),
    ).toBe("$5/mes");
  });

  it("renders Pro as $0.02/h", () => {
    expect(
      formatLandingPrice({ id: "pro", unit_price: 0.02, billing_model: "hourly" }),
    ).toBe("$0.02/h");
  });

  it("renders Sandbox as Gratis", () => {
    expect(
      formatLandingPrice({ id: "sandbox", unit_price: 0, billing_model: "monthly" }),
    ).toBe("Gratis");
  });
});
