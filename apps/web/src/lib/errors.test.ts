import { ApiError, problemToMessage } from "@/lib/errors";

describe("problemToMessage", () => {
  it("maps catalogued codes to spanish copy", () => {
    expect(
      problemToMessage({
        code: "quota_exceeded",
        message: "ignored",
        request_id: "req_01",
      }),
    ).toBe("Alcanzaste el máximo de ponds de tu plan.");
  });

  it("preserves ApiError instances", () => {
    const error = new ApiError({
      code: "pond_not_found",
      message: "No encontramos ese pond.",
      request_id: "req_02",
    });

    expect(problemToMessage(error)).toBe("No encontramos ese pond.");
  });

  it("returns a network fallback for fetch-style failures", () => {
    expect(problemToMessage(new TypeError("fetch failed"))).toBe(
      "No pudimos conectar con el control plane.",
    );
  });

  it("falls back to server messages when a code is unknown to the client", () => {
    expect(
      problemToMessage({
        code: "unmapped_code",
        message: "Mensaje remoto",
        request_id: "req_03",
      }),
    ).toBe("Mensaje remoto");
  });
});
