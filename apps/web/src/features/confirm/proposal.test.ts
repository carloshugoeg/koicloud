import { describe, expect, it } from "vitest";
import {
  confirmSearch,
  formatCountdown,
  parseConfirmLocation,
  type ConfirmationProposal,
} from "@/features/confirm/proposal";

const expiresAt = new Date("2026-10-26T23:10:00.000Z");

function proposal(): ConfirmationProposal {
  return {
    token: "conf_create_pond_demo" as ConfirmationProposal["token"],
    summary: "Se creará el pond 'inventario-demo'.",
    expiresAt,
  };
}

describe("confirm proposal helpers", () => {
  it("round-trips query params", () => {
    const search = confirmSearch(proposal());
    const arrival = parseConfirmLocation({ search: `?${search}`, state: null });
    expect(arrival.kind).toBe("ready");
    if (arrival.kind !== "ready") return;
    expect(arrival.proposal.token).toBe("conf_create_pond_demo");
    expect(arrival.proposal.summary).toContain("inventario-demo");
    expect(arrival.proposal.expiresAt.toISOString()).toBe(expiresAt.toISOString());
  });

  it("marks a partial query as malformed", () => {
    const arrival = parseConfirmLocation({
      search: "?token=conf_create_pond_demo",
      state: null,
    });
    expect(arrival).toEqual({ kind: "invalid", reason: "malformed" });
  });

  it("marks disputed arrivals when query and state disagree", () => {
    const search = confirmSearch(proposal());
    const arrival = parseConfirmLocation({
      search: `?${search}`,
      state: {
        status: "confirmation_required",
        token: "conf_other_token_xx",
        summary: "Otra propuesta",
        expires_at: expiresAt.toISOString(),
        next: { confirm_url: "/x", cli_example: "koicloud confirm x" },
      },
    });
    expect(arrival).toEqual({ kind: "invalid", reason: "disputed" });
  });

  it("formats countdown and local expiry", () => {
    const now = new Date("2026-10-26T23:09:30.000Z");
    expect(formatCountdown(expiresAt, now)).toEqual({ text: "00:30", expired: false });
    expect(formatCountdown(expiresAt, new Date(expiresAt.getTime() - 90_200))).toEqual({
      text: "01:31",
      expired: false,
    });
    expect(formatCountdown(expiresAt, new Date("2026-10-26T23:10:01.000Z"))).toEqual({
      text: "00:00",
      expired: true,
    });
  });
});
