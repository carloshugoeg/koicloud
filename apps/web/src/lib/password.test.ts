import { describe, expect, it } from "vitest";
import { isPasswordLongEnough, MIN_PASSWORD_LENGTH, passwordMinHelp } from "@/lib/password";

describe("password shared minimum", () => {
  it("exports a single minimum of 10 for register and reset", () => {
    expect(MIN_PASSWORD_LENGTH).toBe(10);
    expect(passwordMinHelp()).toBe("Mínimo 10 caracteres.");
    expect(isPasswordLongEnough("123456789")).toBe(false);
    expect(isPasswordLongEnough("1234567890")).toBe(true);
  });
});
