import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  useRunSqlMutation,
  useSqlHistoryQuery,
  type SQLMode,
  type SQLResultResponse,
} from "@/api/hooks/sql-console";
import { ApiError, problemToMessage } from "@/lib/errors";

type Outcome =
  | { kind: "idle" }
  | { kind: "result"; result: SQLResultResponse; mode: SQLMode }
  | { kind: "error"; error: unknown };

function formatStamp(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat("es-GT", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(date);
}

function cellText(value: unknown) {
  if (value === null || value === undefined) {
    return "NULL";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function SqlConsolePage() {
  const { pondId = "" } = useParams();
  const [query, setQuery] = useState("SELECT 1");
  const [mode, setMode] = useState<SQLMode>("read");
  const [outcome, setOutcome] = useState<Outcome>({ kind: "idle" });

  const historyQuery = useSqlHistoryQuery(pondId || undefined);
  const runSql = useRunSqlMutation(pondId);

  const write = mode === "write";

  function run() {
    if (!pondId || !query.trim()) {
      return;
    }
    runSql.mutate(
      { query, mode },
      {
        onSuccess: (result) => setOutcome({ kind: "result", result, mode }),
        onError: (error) => setOutcome({ kind: "error", error }),
      },
    );
  }

  return (
    <div className="space-y-5" data-testid="sql-console">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-ink">Consola SQL</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Lectura por defecto. El historial es de tus consultas en este pond.
          </p>
          <nav className="mt-3 flex flex-wrap gap-3 text-sm">
            <Link className="text-turquoise-700" to={`/app/ponds/${pondId}`}>
              Resumen
            </Link>
            <span className="font-medium text-ink">Consola</span>
            <Link className="text-turquoise-700" to={`/app/ponds/${pondId}/backups`}>
              Respaldos
            </Link>
          </nav>
        </div>
        <button
          type="button"
          className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:opacity-60"
          disabled={!pondId || runSql.isPending || !query.trim()}
          onClick={run}
          data-testid="sql-run"
        >
          {runSql.isPending ? "Ejecutando…" : "Ejecutar"}
        </button>
      </div>

      <div className="grid gap-5 lg:grid-cols-[1fr_280px]">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={`h-8 rounded-sm px-3 text-sm font-medium ${
                mode === "read"
                  ? "bg-turquoise-700 text-bone-raised"
                  : "border border-line-control bg-bone-raised text-ink"
              }`}
              onClick={() => setMode("read")}
              data-testid="sql-mode-read"
            >
              Lectura
            </button>
            <button
              type="button"
              className={`h-8 rounded-sm px-3 text-sm font-medium ${
                write
                  ? "bg-koi text-bone-raised"
                  : "border border-line-control bg-bone-raised text-ink"
              }`}
              onClick={() => setMode("write")}
              data-testid="sql-mode-write"
            >
              Escritura
            </button>
          </div>

          {write ? (
            <div
              className="rounded-sm border border-koi bg-koi-soft px-3 py-2 text-sm text-ink"
              data-testid="sql-write-warning"
              role="status"
            >
              Modo escritura: las sentencias modifican datos reales.
            </div>
          ) : null}

          <div
            className={`overflow-hidden rounded-md border bg-paper ${
              write ? "border-2 border-koi" : "border-line"
            }`}
            data-testid="sql-editor"
          >
            <CodeMirror
              value={query}
              height="220px"
              extensions={[sql()]}
              basicSetup={{ lineNumbers: true, foldGutter: false }}
              onChange={setQuery}
              className="text-sm"
            />
          </div>

          {outcome.kind === "error" ? (
            <div
              className="rounded-md border border-line bg-bone-raised p-4"
              data-testid="sql-error"
              role="alert"
            >
              <div className="border-l-[3px] border-danger pl-3">
                <p className="text-sm text-ink">{problemToMessage(outcome.error)}</p>
                {outcome.error instanceof ApiError && outcome.error.problem?.code ? (
                  <p className="mt-1 font-mono text-xs text-ink-faint">
                    {outcome.error.problem.code}
                  </p>
                ) : null}
              </div>
            </div>
          ) : null}

          {outcome.kind === "result" ? (
            <section
              className="rounded-md border border-line bg-paper"
              data-testid="sql-results"
            >
              <div className="overflow-x-auto">
                <table className="min-w-full text-left font-mono text-sm">
                  <thead className="sticky top-0 bg-bone-sunk text-ink-muted">
                    <tr>
                      {outcome.result.columns.map((column) => (
                        <th key={column} className="px-3 py-2 font-medium">
                          {column}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {outcome.result.rows.map((row, rowIndex) => (
                      <tr key={rowIndex} className="border-t border-line">
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} className="px-3 py-2 text-ink">
                            {cellText(cell)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div
                className="flex flex-wrap gap-3 border-t border-line px-3 py-2 font-mono text-xs text-ink-muted"
                data-testid="sql-results-meta"
              >
                <span>{outcome.result.row_count} filas</span>
                <span>{outcome.result.duration_ms} ms</span>
                <span>modo {outcome.mode}</span>
                <span>truncated = {String(outcome.result.truncated)}</span>
              </div>
              {outcome.result.truncated ? (
                <p
                  className="border-t border-line bg-bone-sunk px-3 py-2 text-xs text-ink"
                  data-testid="sql-truncated"
                >
                  Resultado truncado: se muestran como máximo 1000 filas.
                </p>
              ) : null}
            </section>
          ) : null}
        </div>

        <aside
          className="rounded-md border border-line bg-bone-raised p-4"
          data-testid="sql-history"
        >
          <h3 className="font-display text-lg text-ink">Historial</h3>
          <p className="mt-1 text-xs text-ink-muted">Tus últimas consultas en este pond.</p>

          {historyQuery.isPending ? (
            <div className="mt-4 h-24 animate-pulse rounded-sm bg-bone-sunk" />
          ) : null}

          {historyQuery.isError ? (
            <p className="mt-4 text-sm text-ink">{problemToMessage(historyQuery.error)}</p>
          ) : null}

          {historyQuery.data ? (
            <ul className="mt-4 space-y-3">
              {historyQuery.data.events.length === 0 ? (
                <li className="text-sm text-ink-muted">Aún no hay consultas.</li>
              ) : (
                historyQuery.data.events.map((event) => (
                  <li
                    key={event.id}
                    className="rounded-sm border border-line bg-paper px-3 py-2"
                    data-testid="sql-history-item"
                  >
                    <p className="truncate font-mono text-xs text-ink" title={event.query_truncated}>
                      {event.query_truncated}
                    </p>
                    <p className="mt-1 flex flex-wrap gap-2 font-mono text-[11px] text-ink-faint">
                      <span>{formatStamp(event.executed_at)}</span>
                      <span>{event.mode}</span>
                      <span>{event.duration_ms} ms</span>
                      <span>{event.row_count} filas</span>
                    </p>
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </aside>
      </div>
    </div>
  );
}
