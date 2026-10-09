import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { usePlansQuery, useUsageQuery } from "@/api/hooks";
import { usePondsQuery, type Pond } from "@/api/hooks/ponds";
import { problemToMessage } from "@/lib/errors";
import { pondStateMeta } from "@/features/ponds/pond-state";

const FREE_CELLS = 10;

function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime();
  if (Number.isNaN(ms) || ms < 0) return iso;
  const minutes = Math.floor(ms / 60_000);
  if (minutes < 1) return "hace un momento";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `hace ${hours} h`;
  const days = Math.floor(hours / 24);
  return `hace ${days} d`;
}

function connectionLabel(pond: Pond): string {
  if (pond.observed_state !== "running") return "—";
  return `puerto ${pond.host_port}`;
}

function planLabel(ponds: Pond[], planNames: Map<string, string>): string {
  if (ponds.length === 0) return "—";
  const counts = new Map<string, number>();
  for (const pond of ponds) {
    counts.set(pond.plan_id, (counts.get(pond.plan_id) ?? 0) + 1);
  }
  let top = ponds[0].plan_id;
  let topCount = 0;
  for (const [id, count] of counts) {
    if (count > topCount) {
      top = id;
      topCount = count;
    }
  }
  return planNames.get(top) ?? top;
}

function diffFlashIds(prev: Pond[] | undefined, next: Pond[] | undefined): Set<string> {
  const changed = new Set<string>();
  if (!prev || !next) return changed;
  const prevById = new Map(prev.map((pond) => [pond.id, pond.observed_state]));
  for (const pond of next) {
    const before = prevById.get(pond.id);
    if (before !== undefined && before !== pond.observed_state) {
      changed.add(pond.id);
    }
  }
  return changed;
}

export function DashboardPage() {
  const pondsQuery = usePondsQuery();
  const plansQuery = usePlansQuery();
  const usageQuery = useUsageQuery();
  const [flashIds, setFlashIds] = useState<Set<string>>(() => new Set());
  const [pondsSnapshot, setPondsSnapshot] = useState<Pond[] | undefined>(undefined);

  if (pondsQuery.data !== pondsSnapshot) {
    const changed = diffFlashIds(pondsSnapshot, pondsQuery.data);
    setPondsSnapshot(pondsQuery.data);
    if (changed.size > 0) {
      setFlashIds(changed);
    }
  }

  useEffect(() => {
    if (flashIds.size === 0) return;
    const timer = window.setTimeout(() => setFlashIds(new Set()), 600);
    return () => window.clearTimeout(timer);
  }, [flashIds]);

  const ponds = pondsQuery.data ?? [];

  if (pondsQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="ponds-loading">
        <div className="h-10 w-48 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="h-28 animate-pulse rounded-md border border-line bg-bone-sunk" />
          ))}
        </div>
        <div className="h-40 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (pondsQuery.isError) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="ponds-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(pondsQuery.error)}</p>
          <p className="mt-1 font-mono text-xs text-ink-faint">
            {(pondsQuery.error as { problem?: { code?: string } })?.problem?.code ?? "error"}
          </p>
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink hover:border-turquoise-700"
          onClick={() => void pondsQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  if (ponds.length === 0) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="ponds-empty">
        <div className="mx-auto mb-4 koi" aria-hidden />
        <h2 className="font-display text-2xl text-ink">Todavía no tenés ponds</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Creá el primero para ver la rejilla del estanque y el estado observado.
        </p>
        <Link
          to="/app/ponds/new"
          className="mt-5 inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900"
        >
          Crear pond
        </Link>
      </div>
    );
  }

  const running = ponds.filter((p) => p.observed_state === "running").length;
  const stopped = ponds.filter((p) => p.observed_state === "stopped").length;
  const failed = ponds.filter((p) => p.observed_state === "failed").length;
  const planNames = new Map((plansQuery.data ?? []).map((p) => [p.id, p.name]));
  const usageHours = usageQuery.data?.total_instance_hours;
  const storageGbHours = usageQuery.data?.total_storage_gb_hours;

  return (
    <div className="space-y-6" data-testid="ponds-dashboard">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="font-display text-3xl text-ink">Tus ponds</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Estado observado del nodo, no el deseado. Se actualiza cada 4 segundos mientras haya trabajos en curso.
          </p>
        </div>
        <Link
          to="/app/ponds/new"
          className="inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900"
        >
          Crear pond
        </Link>
      </div>

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <Kpi
          label="Ponds en línea"
          value={`${running}`}
          unit={`de ${ponds.length}`}
          delta={`${stopped} detenido · ${failed} con fallas`}
        />
        <Kpi
          label="Plan"
          value={plansQuery.isPending ? "…" : planLabel(ponds, planNames)}
          delta={plansQuery.isError ? "No se pudo cargar GET /plans" : "Heredado de la suscripción"}
        />
        <Kpi
          label="Uso del mes"
          value={usageQuery.isPending ? "…" : usageHours == null ? "—" : String(usageHours)}
          unit={usageHours == null ? undefined : "h"}
          delta={usageQuery.isError ? "No se pudo cargar GET /usage" : "instance_hours del mes"}
        />
        <Kpi
          label="Almacenamiento"
          value={usageQuery.isPending ? "…" : storageGbHours == null ? "—" : String(storageGbHours)}
          unit={storageGbHours == null ? undefined : "GB·h"}
          delta={usageQuery.isError ? "No se pudo cargar GET /usage" : "storage_gb_hours del mes"}
        />
      </div>

      <div className="rounded-md border border-line bg-bone-raised p-5">
        <h3 className="font-display text-xl text-ink">Rejilla del estanque</h3>
        <p className="mt-1 text-sm text-ink-muted">Una celda por pond, color por estado.</p>
        <div className="pond-grid mt-4" role="list" aria-label="Rejilla del estanque">
          {ponds.map((pond) => {
            const meta = pondStateMeta(pond.observed_state);
            return (
              <i
                key={pond.id}
                role="listitem"
                title={`${pond.name}: ${meta.label}`}
                className={`pond-cell ${meta.cellClass}`}
                data-state={pond.observed_state}
              />
            );
          })}
          {Array.from({ length: Math.max(0, FREE_CELLS - ponds.length) }, (_, i) => (
            <i key={`free-${i}`} className="pond-cell pond-cell--free" title="Cupo libre" />
          ))}
        </div>
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink-muted">
          <span>En línea</span>
          <span>Aprovisionando</span>
          <span>Detenido</span>
          <span>Con fallas</span>
          <span>Cupo libre</span>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border border-line">
        <table className="w-full min-w-[720px] border-collapse text-sm">
          <thead className="bg-bone-sunk text-left text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
            <tr>
              <th className="border-b border-line-control px-3 py-2">Nombre</th>
              <th className="border-b border-line-control px-3 py-2">Estado</th>
              <th className="border-b border-line-control px-3 py-2">Conexión</th>
              <th className="border-b border-line-control px-3 py-2">Plan</th>
              <th className="border-b border-line-control px-3 py-2">Creado</th>
              <th className="border-b border-line-control px-3 py-2 text-right">Acción</th>
            </tr>
          </thead>
          <tbody>
            {ponds.map((pond) => {
              const meta = pondStateMeta(pond.observed_state);
              const flash = flashIds.has(pond.id);
              return (
                <tr
                  key={pond.id}
                  data-pond-id={pond.id}
                  data-flash={flash ? "true" : "false"}
                  className={`min-h-row border-b border-line hover:bg-bone-raised ${flash ? "pond-row-flash" : ""}`}
                >
                  <td className="px-3 py-2 font-medium text-ink">{pond.name}</td>
                  <td className="px-3 py-2">
                    <span
                      className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${meta.badgeClass}`}
                    >
                      <span aria-hidden>{meta.glyph}</span>
                      {meta.label}
                    </span>
                  </td>
                  <td className="px-3 py-2 font-mono text-xs text-ink">
                    {connectionLabel(pond)}
                  </td>
                  <td className="px-3 py-2">
                    <span className="rounded-sm bg-bone-sunk px-2 py-0.5 text-xs font-medium text-ink">
                      {pond.plan_id}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-ink-muted">{formatRelative(pond.created_at)}</td>
                  <td className="px-3 py-2 text-right">
                    <Link
                      to={`/app/ponds/${pond.id}`}
                      className="text-sm font-medium text-turquoise-700 hover:text-turquoise-900"
                    >
                      Abrir
                    </Link>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="flex justify-between border-t border-line bg-bone px-3 py-2 text-xs text-ink-muted">
          <span>{ponds.length} ponds</span>
          <span className="font-mono">GET /ponds</span>
        </div>
      </div>
    </div>
  );
}

function Kpi({
  label,
  value,
  unit,
  delta,
}: {
  label: string;
  value: string;
  unit?: string;
  delta: string;
}) {
  return (
    <div className="rounded-md border border-line bg-bone-raised p-4">
      <p className="text-xs font-medium uppercase tracking-[0.18em] text-ink-muted">{label}</p>
      <p className="mt-1 font-display text-4xl tabular-nums text-ink">
        {value}
        {unit ? <span className="ml-1 text-lg text-ink-muted">{unit}</span> : null}
      </p>
      <p className="mt-1 text-xs text-ink-muted">{delta}</p>
    </div>
  );
}
