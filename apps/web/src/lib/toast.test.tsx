import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ToastHost } from "@/lib/toast-host";
import { toast } from "@/lib/toast";

function stubReducedMotion(reduced: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduced && query.includes("prefers-reduced-motion"),
    media: query,
    onchange: null,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    addListener: () => undefined,
    removeListener: () => undefined,
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

describe("ToastHost", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("keeps an empty aria-live host in the DOM", () => {
    stubReducedMotion(false);
    render(<ToastHost />);

    const host = screen.getByTestId("toast-host");
    expect(host).toBeInTheDocument();
    expect(host).toHaveAttribute("aria-live", "polite");
    expect(host).toBeEmptyDOMElement();
    expect(screen.queryByTestId("toast")).not.toBeInTheDocument();
  });

  it("removes the toast after 1.2s", () => {
    vi.useFakeTimers();
    stubReducedMotion(false);
    render(<ToastHost />);

    act(() => {
      toast({ tone: "ok", message: "URI copiada" });
    });

    const node = screen.getByTestId("toast");
    expect(node).toHaveTextContent("URI copiada");
    expect(node.className).toContain("transition-opacity");

    act(() => {
      vi.advanceTimersByTime(1199);
    });
    expect(screen.getByTestId("toast")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.queryByTestId("toast")).not.toBeInTheDocument();
  });

  it("keeps the 1.2s lifetime when motion is reduced", () => {
    vi.useFakeTimers();
    stubReducedMotion(true);
    render(<ToastHost />);

    act(() => {
      toast({ tone: "danger", message: "No encontramos ese pond." });
    });

    const node = screen.getByTestId("toast");
    expect(node.className).not.toContain("transition");

    act(() => {
      vi.advanceTimersByTime(1200);
    });
    expect(screen.queryByTestId("toast")).not.toBeInTheDocument();
  });
});
