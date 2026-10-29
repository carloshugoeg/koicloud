import { afterEach, describe, expect, it, vi } from "vitest";
import { formatExpires } from "@/features/ponds/format-expires";

describe("formatExpires", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders a dash when the server sent no expiry", () => {
    expect(formatExpires(null)).toEqual({ label: "—" });
    expect(formatExpires(undefined)).toEqual({ label: "—" });
    expect(formatExpires("not-a-date")).toEqual({ label: "—" });
  });

  it("uses Guatemala calendar days and an absolute title", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-22T18:00:00Z"));

    expect(formatExpires("2026-09-29T20:00:00Z")).toEqual({
      label: "en 7 d",
      title: "2026-09-29 14:00",
    });
    expect(formatExpires("2026-09-22T20:00:00Z")).toEqual({
      label: "hoy",
      title: "2026-09-22 14:00",
    });
    expect(formatExpires("2026-09-22T12:00:00Z")).toEqual({
      label: "vencido",
      title: "2026-09-22 06:00",
    });
  });

  it("counts the next Guatemala day as one day even inside 24 hours", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-09-23T05:30:00Z"));

    expect(formatExpires("2026-09-23T06:30:00Z").label).toBe("en 1 d");
  });
});
