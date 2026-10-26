import { ApiError } from "@/lib/errors";
import {
  confirmSearch,
  controlsAfter,
  formatCountdown,
  parseConfirmLocation,
  type ConfirmationProposal,
} from "@/features/confirm/proposal";

const SUMMARY = "Se creará el pond 'inventario-demo'. Expira en 5 min.";
const TOKEN = "conf_create_pond_demo";
const EXPIRES_AT = new Date("2026-12-01T18:30:00.000Z");

function wire(token = TOKEN, summary = SUMMARY, expiresAt = EXPIRES_AT) {
  return {
    status: "confirmation_required" as const,
    token,
    summary,
    expires_at: expiresAt.toISOString(),
    next: {
      cli_example: `koicloud confirm ${token}`,
      confirm_url: `/api/v1/confirm/${token}`,
    },
  };
}

function readyProposal(): ConfirmationProposal {
  const arrival = parseConfirmLocation({
    search: `?token=${TOKEN}&summary=${encodeURIComponent(SUMMARY)}&expires_at=${encodeURIComponent(EXPIRES_AT.toISOString())}`,
    state: null,
  });
  if (arrival.kind !== "ready") {
    throw new Error("fixture did not parse");
  }
  return arrival.proposal;
}

describe("confirmation proposal", () => {
  it("roundtrips a summary with spaces and quotes through the query string", () => {
    const proposal = readyProposal();
    const again = parseConfirmLocation({
      search: confirmSearch(proposal),
      state: null,
    });

    expect(again).toEqual({ kind: "ready", proposal });
    if (again.kind !== "ready") {
      return;
    }
    expect(again.proposal.summary).toBe(SUMMARY);
    expect(again.proposal.summary).toContain("'inventario-demo'");
    expect(again.proposal.expiresAt.toISOString()).toBe(EXPIRES_AT.toISOString());
  });

  it("rejects a partial query even when state holds a full payload", () => {
    expect(
      parseConfirmLocation({
        search: `?token=${TOKEN}`,
        state: wire(),
      }),
    ).toEqual({ kind: "invalid", reason: "malformed" });
  });

  it("marks disagreeing query and state tokens as disputed", () => {
    const proposal = readyProposal();
    expect(
      parseConfirmLocation({
        search: confirmSearch(proposal),
        state: wire("conf_other_token_1"),
      }),
    ).toEqual({ kind: "invalid", reason: "disputed" });
  });

  it("keeps a ready proposal when query and state name the same instant", () => {
    const proposal = readyProposal();
    expect(
      parseConfirmLocation({
        search: confirmSearch(proposal),
        state: wire(),
      }),
    ).toEqual({ kind: "ready", proposal });
  });

  it("reads state only when the query has none of the proposal keys", () => {
    const proposal = readyProposal();
    expect(parseConfirmLocation({ search: "", state: wire() })).toEqual({
      kind: "ready",
      proposal,
    });
    expect(parseConfirmLocation({ search: "", state: null })).toEqual({
      kind: "invalid",
      reason: "missing",
    });
    expect(parseConfirmLocation({ search: "?pond=1", state: { from: "/login" } })).toEqual({
      kind: "invalid",
      reason: "malformed",
    });
  });

  it("formats the countdown by ceiling to the next whole second", () => {
    const expiresAt = new Date("2026-12-01T00:00:00.000Z");
    expect(formatCountdown(expiresAt, new Date(expiresAt.getTime() - 90_200))).toEqual({
      text: "01:31",
      expired: false,
    });
    expect(formatCountdown(expiresAt, expiresAt)).toEqual({ text: "00:00", expired: true });
    expect(formatCountdown(expiresAt, new Date(expiresAt.getTime() + 5))).toEqual({
      text: "00:00",
      expired: true,
    });
    expect(formatCountdown(expiresAt, new Date(expiresAt.getTime() - 120 * 60_000))).toEqual({
      text: "120:00",
      expired: false,
    });
  });

  it("disables buttons from the catalog code, and from the clock only when the request did not land", () => {
    const notFound = new ApiError({
      code: "confirmation_not_found",
      message: "confirmation_not_found",
    });
    const expired = new ApiError({
      code: "confirmation_expired",
      message: "confirmation_expired",
    });
    const mismatch = new ApiError({
      code: "confirmation_action_mismatch",
      message: "confirmation_action_mismatch",
    });
    const quota = new ApiError({
      code: "quota_exceeded",
      message: "quota_exceeded",
    });
    const unreachable = new ApiError(null);

    expect(controlsAfter(null, false)).toEqual({ confirmEnabled: true, discardEnabled: true });
    expect(controlsAfter(null, true)).toEqual({ confirmEnabled: false, discardEnabled: true });
    expect(controlsAfter(new TypeError("fetch failed"), false)).toEqual({
      confirmEnabled: true,
      discardEnabled: true,
    });
    expect(controlsAfter(new TypeError("fetch failed"), true)).toEqual({
      confirmEnabled: false,
      discardEnabled: true,
    });
    expect(controlsAfter(unreachable, false)).toEqual({
      confirmEnabled: true,
      discardEnabled: true,
    });
    expect(controlsAfter(notFound, true)).toEqual({
      confirmEnabled: false,
      discardEnabled: false,
    });
    expect(controlsAfter(expired, false)).toEqual({
      confirmEnabled: false,
      discardEnabled: true,
    });
    expect(controlsAfter(mismatch, false)).toEqual({
      confirmEnabled: false,
      discardEnabled: false,
    });
    expect(controlsAfter(quota, false)).toEqual({
      confirmEnabled: false,
      discardEnabled: false,
    });
  });
});
