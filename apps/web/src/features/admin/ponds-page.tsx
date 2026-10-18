import { useMemo, useState } from "react";
import { useAdminPondsQuery, type AdminPond } from "@/api/hooks/admin";
import { MoreResultsNote } from "@/features/admin/more-results-note";
import { ApiError, problemToMessage } from "@/lib/errors";
import { POND_STATE_META, pondStateMeta } from "@/features/ponds/pond-state";

type StateFilter = "all" | AdminPond["observed_state"];

const POND_STATE_OPTIONS = Object.entries(POND_STATE_META) as [
  AdminPond["observed_state"],
  (typeof POND_STATE_META)[AdminPond["observed_state"]],
][];

export function AdminPondsPage() {
  const pondsQuery = useAdminPondsQuery();
  const [ownerFilter, setOwnerFilter] = useState("");
  const [stateFilter, setStateFilter] = useState<StateFilter>("all");

  const ponds = useMemo(() => {
    const rows = pondsQuery.data?.ponds ?? [];
    const needle = ownerFilter.trim().toLowerCase();
    return rows.filter((pond) => {
      if (stateFilter !== "all" && pond.observed_state !== stateFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return pond.owner_email.toLowerCase().includes(needle) || pond.name.toLowerCase().includes(needle);
    });
  }, [pondsQuery.data?.ponds, ownerFilter, stateFilter]);

  if (pondsQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="admin-ponds-loading">
        <div className="h-10 w-56 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-64 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (pondsQuery.isError) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="admin-ponds-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(pondsQuery.error)}</p>
          <p className="mt-1 font-mono text-xs text-ink-faint">
            {pondsQuery.error instanceof ApiError ? pondsQuery.error.problem?.code : "error"}
          </p>
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void pondsQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const pondsHaveMore = Boolean(pondsQuery.data?.next_cursor);

  return (
    <div className="space-y-4" data-testid="admin-ponds-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap gap-2" data-testid="admin-ponds-filters">
          <label className="text-xs text-ink-muted">
            Dueño / nombre
            <input
              className="mt-1 block h-9 w-52 rounded-sm border border-line-control bg-bone-raised px-3 text-sm"
              value={ownerFilter}
              onChange={(event) => setOwnerFilter(event.target.value)}
            />
          </label>
          <label className="text-xs text-ink-muted">
            Estado
            <select
              className="mt-1 block h-9 rounded-sm border border-line-control bg-bone-raised px-3 text-sm"
              value={stateFilter}
              onChange={(event) => setStateFilter(event.target.value as StateFilter)}
            >
              <option value="all">Todos</option>
              {POND_STATE_OPTIONS.map(([state, meta]) => (
                <option key={state} value={state}>
                  {meta.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {ponds.length === 0 ? (
        <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="admin-ponds-empty">
          <p className="text-sm text-ink-muted">No hay ponds con ese filtro.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-line bg-bone-raised">
          <table className="w-full min-w-[760px] border-collapse text-sm">
            <thead className="bg-bone-sunk text-left text-xs uppercase tracking-[0.12em] text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Pond</th>
                <th className="px-4 py-3 font-medium">Dueño</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium">Nodo</th>
                <th className="px-4 py-3 font-medium">Puerto</th>
                <th className="px-4 py-3 font-medium">Plan</th>
              </tr>
            </thead>
            <tbody>
              {ponds.map((pond) => {
                const meta = pondStateMeta(pond.observed_state);
                return (
                  <tr key={pond.id} className="border-t border-line" data-testid={`admin-pond-row-${pond.id}`}>
                    <td className="px-4 py-3 font-medium">{pond.name}</td>
                    <td className="px-4 py-3 font-mono text-xs">{pond.owner_email}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-sm px-2 py-1 text-xs ${meta.badgeClass}`}>
                        {meta.glyph} {meta.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">{pond.node_id}</td>
                    <td className="px-4 py-3 font-mono text-xs">{pond.host_port}</td>
                    <td className="px-4 py-3 font-mono text-xs">{pond.plan_id}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {pondsHaveMore ? <MoreResultsNote /> : null}
    </div>
  );
}
