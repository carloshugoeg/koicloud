import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, beforeEach } from "vitest";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser } from "@/mocks/fixtures";
import { resetAdminUsersState, resetAgentAccessState, resetSubscriptionsState } from "@/mocks/handlers";
import { server } from "@/mocks/server";

const INTRO_TOUR_KEY = `koicloud:intro-tour-v1:${demoUser.id}`;

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
  resetAgentAccessState();
  resetAdminUsersState();
  resetSubscriptionsState();
  // Default: tour already done so unrelated suites are not blocked by the overlay.
  window.localStorage.setItem(INTRO_TOUR_KEY, "done");
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  window.localStorage.removeItem(INTRO_TOUR_KEY);
});

afterAll(() => {
  server.close();
});
