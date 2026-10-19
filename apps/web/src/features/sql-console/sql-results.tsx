import type { SQLMode, SQLResultResponse } from "@/api/hooks/sql-console";

function cellView(value: unknown) {
  if (value === null || value === undefined) {
    return { text: "NULL", className: "italic text-ink-faint" };
  }
  if (typeof value === "object") {
    return { text: JSON.stringify(value), className: "text-ink" };
  }
  return { text: String(value), className: "text-ink" };
}

export function SqlResults({
  result,
  mode,
}: {
  result: SQLResultResponse;
  mode: SQLMode;
}) {
  return (
    <section className="rounded-md border border-line bg-paper" data-testid="sql-results">
      <div className="overflow-x-auto">
        <table className="min-w-full text-left font-mono text-sm">
          <thead className="sticky top-0 bg-bone-sunk text-ink-muted">
            <tr>
              {result.columns.map((column, columnIndex) => (
                <th key={columnIndex} className="px-3 py-2 font-medium">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-t border-line">
                {row.map((cell, cellIndex) => {
                  const view = cellView(cell);
                  return (
                    <td key={cellIndex} className={`px-3 py-2 ${view.className}`}>
                      {view.text}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div
        className="flex flex-wrap gap-3 border-t border-line px-3 py-2 font-mono text-xs text-ink-muted"
        data-testid="sql-results-meta"
      >
        <span>{result.row_count} filas</span>
        <span>{result.duration_ms} ms</span>
        <span>modo {mode}</span>
        <span>truncated = {String(result.truncated)}</span>
      </div>
      {result.truncated ? (
        <p
          className="border-t border-line px-3 py-2 text-xs text-warn"
          data-testid="sql-truncated"
        >
          Mostrando {result.row_count} filas. El resultado está truncado.
        </p>
      ) : null}
    </section>
  );
}
