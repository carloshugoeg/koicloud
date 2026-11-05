import { useState } from "react";
import type { Pond, PondSchema, PondTable } from "@/api/hooks/ponds";
import { usePondSchema } from "@/api/hooks/ponds";
import { ApiError, problemToMessage } from "@/lib/errors";

type PondTableExplorerProps = {
  pond: Pond;
};

type SchemaView =
  | { kind: "pond_not_running" }
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "empty" }
  | { kind: "ready"; tables: PondTable[] }
  | { kind: "error"; message: string; code?: string };

function deriveSchemaView(
  pond: Pick<Pond, "observed_state">,
  query: {
    isFetched: boolean;
    isFetching: boolean;
    isError: boolean;
    error: unknown;
    data: PondSchema | undefined;
  },
): SchemaView {
  if (pond.observed_state !== "running") {
    return { kind: "pond_not_running" };
  }
  if (query.isFetching && !query.data) {
    return { kind: "loading" };
  }
  if (query.isError && !query.isFetching) {
    const code = query.error instanceof ApiError ? query.error.problem?.code : undefined;
    return { kind: "error", message: problemToMessage(query.error), code };
  }
  if (!query.isFetched) {
    return { kind: "idle" };
  }
  const tables = query.data?.tables ?? [];
  if (tables.length === 0) {
    return { kind: "empty" };
  }
  return { kind: "ready", tables };
}

function statusText(view: SchemaView, fetching: boolean): string {
  if (fetching) return "Cargando tablas…";
  switch (view.kind) {
    case "idle":
      return "Pulsá Recargar para listar las tablas.";
    case "empty":
      return "Sin tablas en el esquema.";
    case "ready":
      return `${view.tables.length} tablas cargadas.`;
    case "error":
      return "No se pudo cargar el esquema.";
    case "pond_not_running":
      return "El pond no está en ejecución.";
    case "loading":
      return "Cargando tablas…";
  }
}

export function PondTableExplorer({ pond }: PondTableExplorerProps) {
  const schemaQuery = usePondSchema(pond.id);
  const view = deriveSchemaView(pond, schemaQuery);
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(() => new Set());
  const canReload = pond.observed_state === "running" && !schemaQuery.isFetching;

  const tables = view.kind === "ready" ? view.tables : [];
  const liveStatus = statusText(view, schemaQuery.isFetching);

  function toggleTable(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  async function onReload() {
    if (pond.observed_state !== "running") return;
    await schemaQuery.reload();
  }

  return (
    <section
      className="rounded-md border border-line bg-paper p-5"
      data-testid="pond-tables"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-xl text-ink">Tablas</h3>
          <p className="text-sm text-ink-muted">
            Esquema de la pond. Recargar lee de nuevo el catálogo.
          </p>
        </div>
        <button
          type="button"
          className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-turquoise-700 disabled:text-ink-faint"
          data-testid="pond-tables-reload"
          aria-busy={schemaQuery.isFetching || undefined}
          disabled={!canReload}
          onClick={() => void onReload()}
        >
          {schemaQuery.isFetching ? "Cargando…" : "Recargar"}
        </button>
      </div>

      <p
        className="sr-only"
        data-testid="pond-tables-status"
        aria-live="polite"
      >
        {liveStatus}
      </p>

      {view.kind === "pond_not_running" ? (
        <p
          className="mt-4 text-sm text-ink-muted"
          data-testid="pond-tables-not-running"
        >
          El pond no está en ejecución. Arrancalo para explorar tablas.
        </p>
      ) : null}

      {view.kind === "idle" ? (
        <p className="mt-4 text-sm text-ink-muted" data-testid="pond-tables-idle">
          Pulsá Recargar para listar las tablas.
        </p>
      ) : null}

      {view.kind === "loading" ? (
        <div
          className="mt-4 h-24 animate-pulse rounded-sm bg-bone-sunk"
          data-testid="pond-tables-loading"
          role="status"
          aria-busy="true"
          aria-label="Cargando tablas"
        />
      ) : null}

      {view.kind === "empty" ? (
        <p className="mt-4 text-sm text-ink-muted" data-testid="pond-tables-empty">
          Esta pond aún no tiene tablas
        </p>
      ) : null}

      {view.kind === "error" ? (
        <div
          className="mt-4 rounded-md border border-line bg-bone-raised p-4"
          data-testid="pond-tables-error"
          role="alert"
        >
          <div className="border-l-[3px] border-danger pl-3">
            <p className="text-sm text-ink">{view.message}</p>
            {view.code ? (
              <p className="mt-1 font-mono text-xs text-ink-muted">{view.code}</p>
            ) : null}
          </div>
          <button
            type="button"
            className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink"
            onClick={() => void onReload()}
          >
            Reintentar
          </button>
        </div>
      ) : null}

      {view.kind === "ready" ? (
        <ul className="mt-4 space-y-2" data-testid="pond-tables-list">
          {tables.map((table) => {
            const open = expanded.has(table.name);
            return (
              <li
                key={table.name}
                className="rounded-sm border border-line bg-bone-raised"
                data-testid="pond-tables-table"
                data-table-name={table.name}
              >
                <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
                  <button
                    type="button"
                    className="flex min-w-0 items-center gap-2 text-left text-sm font-medium text-ink"
                    data-testid="pond-tables-expand"
                    aria-expanded={open}
                    onClick={() => toggleTable(table.name)}
                  >
                    <span aria-hidden className="font-mono text-ink-muted">
                      {open ? "▾" : "▸"}
                    </span>
                    <span className="truncate font-mono">{table.name}</span>
                  </button>
                  <span
                    className="tabular-nums text-sm text-ink-muted"
                    data-testid="pond-tables-estimated-rows"
                  >
                    {table.estimated_rows}
                  </span>
                </div>
                {open ? (
                  <div className="border-t border-line px-3 py-2" data-testid="pond-tables-columns">
                    <table className="w-full text-left text-sm">
                      <thead className="bg-bone-sunk text-xs uppercase tracking-[0.08em] text-ink-muted">
                        <tr>
                          <th className="px-2 py-1 font-medium">Columna</th>
                          <th className="px-2 py-1 font-medium">Tipo</th>
                          <th className="px-2 py-1 font-medium">Nulo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {table.columns.map((col) => (
                          <tr key={col.name} className="border-t border-line">
                            <td className="px-2 py-1 font-mono text-ink">{col.name}</td>
                            <td className="px-2 py-1 font-mono text-ink-muted">{col.type}</td>
                            <td className="px-2 py-1 text-ink-muted">
                              {col.nullable ? "Sí" : "No"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : null}
    </section>
  );
}
