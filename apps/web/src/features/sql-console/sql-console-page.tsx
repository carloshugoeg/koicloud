import { sql } from "@codemirror/lang-sql";
import CodeMirror from "@uiw/react-codemirror";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { PondTabs } from "@/components/pond-tabs";
import { useRunSqlMutation, type SQLMode, type SQLResultResponse } from "@/api/hooks/sql-console";
import { ApiError, problemToMessage } from "@/lib/errors";
import { SqlHistoryPanel } from "@/features/sql-console/sql-history-panel";
import { SqlResults } from "@/features/sql-console/sql-results";
import { sqlEditorChrome, sqlSyntaxHighlight } from "@/features/sql-console/sql-editor-theme";

type Outcome =
  | { kind: "idle" }
  | { kind: "result"; result: SQLResultResponse; mode: SQLMode }
  | { kind: "error"; error: unknown };

export function SqlConsolePage() {
  const { pondId = "" } = useParams();
  const [query, setQuery] = useState("SELECT 1");
  const [mode, setMode] = useState<SQLMode>("read");
  const [outcome, setOutcome] = useState<Outcome>({ kind: "idle" });
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
          <PondTabs pondId={pondId} active="consola" />
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

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_280px]">
        <div className="min-w-0 space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className={`h-8 rounded-sm px-3 text-sm font-medium ${
                mode === "read"
                  ? "bg-turquoise-700 text-bone-raised"
                  : "border border-line-control bg-bone-raised text-ink"
              }`}
              aria-pressed={mode === "read"}
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
              aria-pressed={write}
              onClick={() => setMode("write")}
              data-testid="sql-mode-write"
            >
              Escritura
            </button>
          </div>

          <div
            className={`overflow-hidden rounded-md bg-paper ${
              write ? "border-2 border-koi" : "border border-line"
            }`}
            data-testid="sql-editor"
          >
            {write ? (
              <div
                className="border-b border-koi bg-koi-soft px-3 py-2 text-sm text-ink"
                data-testid="sql-write-warning"
                role="status"
              >
                Modo escritura: las sentencias modifican datos reales.
              </div>
            ) : null}
            <CodeMirror
              value={query}
              height="220px"
              theme={sqlEditorChrome}
              extensions={[sql(), sqlSyntaxHighlight]}
              basicSetup={{ lineNumbers: true, foldGutter: false, syntaxHighlighting: false }}
              onChange={setQuery}
              aria-label="Editor SQL"
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
            <SqlResults result={outcome.result} mode={outcome.mode} />
          ) : null}
        </div>

        <SqlHistoryPanel pondId={pondId} />
      </div>
    </div>
  );
}
