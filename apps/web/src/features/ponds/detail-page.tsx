import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGetConnection, useGetPond } from "@/api/hooks/ponds";
import { ApiError, problemToMessage } from "@/lib/errors";
import { pondStateMeta } from "@/features/ponds/pond-state";

const MASK = "••••••••";

export function PondDetailPage() {
  const { pondId = "" } = useParams();
  const pondQuery = useGetPond(pondId || undefined);
  const connectionQuery = useGetConnection(pondId || undefined);
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  if (pondQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="pond-detail-loading">
        <div className="h-10 w-64 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-56 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (pondQuery.isError) {
    const code =
      pondQuery.error instanceof ApiError ? pondQuery.error.problem?.code : undefined;
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="pond-detail-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(pondQuery.error)}</p>
          {code ? <p className="mt-1 font-mono text-xs text-ink-faint">{code}</p> : null}
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void pondQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const pond = pondQuery.data;
  if (!pond) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="pond-detail-empty">
        <h2 className="font-display text-2xl text-ink">Sin datos del pond</h2>
        <p className="mt-2 text-sm text-ink-muted">Volvé al listado e intentá de nuevo.</p>
        <Link
          to="/app/ponds"
          className="mt-5 inline-flex h-9 items-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
        >
          Ver ponds
        </Link>
      </div>
    );
  }

  const meta = pondStateMeta(pond.observed_state);
  const connection = connectionQuery.data;
  const connectionPending = connectionQuery.isPending;
  const connectionError = connectionQuery.isError;

  async function copyUri() {
    if (!connection?.uri) return;
    await navigator.clipboard.writeText(connection.uri);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_200);
  }

  return (
    <div className="space-y-5" data-testid="pond-detail">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-3xl text-ink">{pond.name}</h2>
            <span
              className={`inline-flex items-center gap-1 rounded-sm px-2 py-0.5 text-xs font-medium ${meta.badgeClass}`}
              data-testid="pond-status-badge"
            >
              <span aria-hidden>{meta.glyph}</span>
              {meta.label}
            </span>
          </div>
          <p className="mt-1 text-sm text-ink-muted">
            PostgreSQL {pond.engine_version} · plan {pond.plan_id} · nodo {pond.node_id}
          </p>
          <nav className="mt-3 flex flex-wrap gap-3 text-sm">
            <span className="font-medium text-ink">Resumen</span>
            <Link className="text-turquoise-700" to={`/app/ponds/${pond.id}/backups`}>
              Respaldos
            </Link>
            <Link className="text-turquoise-700" to={`/app/ponds/${pond.id}/console`}>
              Consola
            </Link>
          </nav>
        </div>
      </div>

      <section className="rounded-md border border-line bg-paper p-5" data-testid="connection-card">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-display text-xl text-ink">Cadena de conexión</h3>
            <p className="text-sm text-ink-muted">Host, puerto, usuario, base y URI. Contraseña oculta por defecto.</p>
          </div>
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-turquoise-700 disabled:text-ink-faint"
            disabled={!connection?.uri || connectionPending}
            onClick={() => void copyUri()}
            data-testid="copy-uri"
          >
            {copied ? "URI copiada" : "Copiar URI"}
          </button>
        </div>

        {connectionPending ? (
          <div className="mt-4 h-32 animate-pulse rounded-sm bg-bone-sunk" />
        ) : null}

        {connectionError ? (
          <div className="mt-4 border-l-[3px] border-danger pl-3 text-sm text-ink">
            {problemToMessage(connectionQuery.error)}
          </div>
        ) : null}

        {connection ? (
          <dl className="mt-4 grid gap-3 font-mono text-sm text-ink md:grid-cols-2">
            <div>
              <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Host</dt>
              <dd data-testid="conn-host">{connection.host}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Puerto</dt>
              <dd data-testid="conn-port">{connection.port}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Usuario</dt>
              <dd data-testid="conn-user">{connection.username}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Base</dt>
              <dd data-testid="conn-db">{connection.database}</dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Contraseña</dt>
              <dd className="flex flex-wrap items-center gap-3">
                <span data-testid="conn-password">{revealed ? connection.password : MASK}</span>
                <button
                  type="button"
                  className="text-xs font-medium text-turquoise-700"
                  onClick={() => setRevealed((v) => !v)}
                  data-testid="reveal-password"
                >
                  {revealed ? "Ocultar" : "Revelar"}
                </button>
              </dd>
            </div>
            <div className="md:col-span-2">
              <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">URI</dt>
              <dd className="break-all" data-testid="conn-uri">
                {revealed
                  ? connection.uri
                  : `postgresql://${connection.username}:${MASK}@${connection.host}:${connection.port}/${connection.database}`}
              </dd>
            </div>
          </dl>
        ) : null}
      </section>
    </div>
  );
}
