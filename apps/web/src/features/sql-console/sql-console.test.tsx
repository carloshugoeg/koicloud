import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { vi } from "vitest";
import { AppProviders } from "@/app/providers";
import { appRoutes } from "@/app/router";
import { useAuthStore } from "@/lib/auth-store";
import { demoUser, fixtures } from "@/mocks/fixtures";
import { server } from "@/mocks/server";

vi.mock("@uiw/react-codemirror", () => ({
  default: function MockCodeMirror({
    value,
    onChange,
  }: {
    value: string;
    onChange?: (value: string) => void;
  }) {
    return (
      <textarea
        aria-label="SQL editor"
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
      />
    );
  },
}));

vi.mock("@codemirror/lang-sql", () => ({
  sql: () => [],
}));

const POND_ID = fixtures.pond.id;

function renderConsole(entry = `/app/ponds/${POND_ID}/consola`) {
  useAuthStore.setState({
    session: {
      accessToken: "access_demo_token",
      refreshToken: "refresh_demo_token",
      user: demoUser,
    },
  });

  const router = createMemoryRouter(appRoutes, { initialEntries: [entry] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>,
  );
}

describe("W2-07 Consola SQL", () => {
  it("runs SELECT and shows columns, rows, and meta", async () => {
    const user = userEvent.setup();
    renderConsole();

    expect(await screen.findByTestId("sql-console")).toBeInTheDocument();
    expect(await screen.findAllByTestId("sql-history-item")).not.toHaveLength(0);

    await user.click(screen.getByTestId("sql-run"));

    expect(await screen.findByTestId("sql-results")).toBeInTheDocument();
    expect(screen.getByText("?column?")).toBeInTheDocument();
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByTestId("sql-results-meta")).toHaveTextContent("1 filas");
    expect(screen.getByTestId("sql-results-meta")).toHaveTextContent("4 ms");
    expect(screen.getByTestId("sql-results-meta")).toHaveTextContent("truncated = false");
  });

  it("defaults to read and shows write warning before execute", async () => {
    const user = userEvent.setup();
    renderConsole(`/app/ponds/${POND_ID}/console`);

    await screen.findByTestId("sql-console");
    expect(screen.queryByTestId("sql-write-warning")).not.toBeInTheDocument();

    await user.click(screen.getByTestId("sql-mode-write"));
    expect(screen.getByTestId("sql-write-warning")).toHaveTextContent(
      "Modo escritura: las sentencias modifican datos reales.",
    );
  });

  it("shows catalog message for sql_readonly_violation", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/sql`, () =>
        HttpResponse.json(
          {
            code: "sql_readonly_violation",
            message: "write in read",
            request_id: "req_sql_ro",
          },
          { status: 400 },
        ),
      ),
    );

    renderConsole();
    await screen.findByTestId("sql-console");
    await user.click(screen.getByTestId("sql-run"));

    expect(await screen.findByTestId("sql-error")).toHaveTextContent(
      "La consulta intenta escribir datos en modo lectura.",
    );
    expect(screen.getByTestId("sql-error")).toHaveTextContent("sql_readonly_violation");
  });

  it("shows truncated footer when the API marks truncated", async () => {
    const user = userEvent.setup();
    server.use(
      http.post(`*/api/v1/ponds/${POND_ID}/sql`, () =>
        HttpResponse.json(fixtures.sqlResultTruncated),
      ),
    );

    renderConsole();
    await screen.findByTestId("sql-console");
    await user.click(screen.getByTestId("sql-run"));

    await waitFor(() => {
      expect(screen.getByTestId("sql-truncated")).toBeInTheDocument();
    });
    expect(screen.getByTestId("sql-results-meta")).toHaveTextContent("truncated = true");
  });
});
