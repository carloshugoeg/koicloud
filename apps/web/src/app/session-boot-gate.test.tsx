import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SessionBootGate } from "@/app/session-boot-gate";

describe("SessionBootGate — boot frame (CA3)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders DataStateSessionBoot before handing off to children", async () => {
    let flushFrame: FrameRequestCallback | null = null;
    vi.stubGlobal("requestAnimationFrame", (cb: FrameRequestCallback) => {
      flushFrame = cb;
      return 1;
    });
    vi.stubGlobal("cancelAnimationFrame", () => undefined);

    render(
      <SessionBootGate skipBoot={false}>
        <div data-testid="app-after-boot">listo</div>
      </SessionBootGate>,
    );

    expect(screen.getByTestId("data-state-session-boot")).toBeInTheDocument();
    expect(screen.getByText("Iniciando sesión…")).toBeInTheDocument();
    expect(screen.queryByTestId("app-after-boot")).not.toBeInTheDocument();

    act(() => {
      flushFrame?.(0);
    });

    expect(await screen.findByTestId("app-after-boot")).toBeInTheDocument();
    expect(screen.queryByTestId("data-state-session-boot")).not.toBeInTheDocument();
  });
});
