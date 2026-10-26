import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ToastHost } from "@/components/toast-host";
import { pushToast, resetToasts } from "@/lib/toast";

afterEach(() => {
  vi.useRealTimers();
  resetToasts();
});

describe("ToastHost", () => {
  it("shows a toast for 1200 ms and then removes it", () => {
    vi.useFakeTimers();
    render(<ToastHost />);

    act(() => {
      pushToast({ title: "URI copiada", detail: "La contraseña va incluida.", tone: "ok" });
    });

    expect(screen.getByTestId("toast")).toHaveTextContent("URI copiada");
    expect(screen.getByText("La contraseña va incluida.")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1199);
    });
    expect(screen.getByText("URI copiada")).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(screen.queryByTestId("toast")).not.toBeInTheDocument();
  });
});
