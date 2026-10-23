import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/errors";
import {
  DataStateEmpty,
  DataStateError,
  DataStateLoading,
  DataStateSessionBoot,
} from "@/components/data-state";

describe("DataState — loading / empty / error / session boot", () => {
  it("renders loading skeletons with busy status", () => {
    render(<DataStateLoading blocks={5} />);

    const status = screen.getByTestId("data-state-loading");
    expect(status).toHaveAttribute("aria-busy", "true");
    expect(status).toHaveAttribute("role", "status");
    expect(status.querySelectorAll(".data-skeleton").length).toBeGreaterThanOrEqual(3);
  });

  it("renders empty state with pond, title, and primary CTA", () => {
    render(
      <MemoryRouter>
        <DataStateEmpty
          title="Todavía no tenés ponds"
          description="Creá el primero para ver la rejilla del estanque."
          action={
            <a
              href="/app/ponds/new"
              className="inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
            >
              Crear pond
            </a>
          }
        />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("data-state-empty")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Todavía no tenés ponds" })).toBeInTheDocument();
    expect(screen.getByText("Creá el primero para ver la rejilla del estanque.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crear pond" })).toHaveAttribute(
      "href",
      "/app/ponds/new",
    );
    expect(document.querySelector(".pond-water-panel")).not.toBeNull();
    expect(document.querySelector(".koi")).not.toBeNull();
  });

  it("renders error state with translated message, code, and Reintentar", async () => {
    const user = userEvent.setup();
    const onRetry = vi.fn();
    const error = new ApiError({
      code: "internal_error",
      message: "boom",
      request_id: "req_test",
    });

    render(<DataStateError error={error} onRetry={onRetry} />);

    expect(screen.getByTestId("data-state-error")).toHaveAttribute("role", "alert");
    expect(
      screen.getByText("Algo salió mal. Revisá los logs e intentá de nuevo."),
    ).toBeInTheDocument();
    expect(screen.getByText("internal_error")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders quiet session-boot pond at 160×120 without drift", () => {
    render(<DataStateSessionBoot />);

    const boot = screen.getByTestId("data-state-session-boot");
    expect(boot).toHaveAttribute("role", "status");
    expect(boot).toHaveAttribute("aria-busy", "true");
    expect(screen.getByText("Iniciando sesión…")).toBeInTheDocument();

    const pond = boot.querySelector(".data-state-session-boot__pond");
    expect(pond).not.toBeNull();
    expect(boot.querySelector(".data-state-session-boot__koi")).not.toBeNull();
  });
});
