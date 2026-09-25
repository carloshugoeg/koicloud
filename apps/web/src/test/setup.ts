import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { useAuthStore } from "@/lib/auth-store";
import { server } from "@/mocks/server";

const NativeRequest = globalThis.Request;

class JSDOMRequest extends NativeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    const resolvedInput =
      typeof input === "string" && input.startsWith("/")
        ? new URL(input, window.location.origin).toString()
        : input;
    const resolvedInit =
      input instanceof NativeRequest && init
        ? ({ ...init, duplex: "half" } as RequestInit)
        : init;
    super(resolvedInput, resolvedInit);
  }
}

globalThis.Request = JSDOMRequest;

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

beforeEach(() => {
  useAuthStore.getState().clearSession();
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
