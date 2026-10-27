import { useState } from "react";
import type { Connection } from "@/api/hooks/ponds";
import { problemToMessage } from "@/lib/errors";

const MASK = "••••••••";

type ConnectionCardProps = {
  connection: Connection | undefined;
  pending: boolean;
  error: unknown;
};

export function ConnectionCard({ connection, pending, error }: ConnectionCardProps) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);

  async function copyUri() {
    if (!connection?.uri) return;
    await navigator.clipboard.writeText(connection.uri);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1_200);
  }

  return (
    <section className="rounded-md border border-line bg-paper p-5" data-testid="connection-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="font-display text-xl text-ink">Cadena de conexión</h3>
          <p className="text-sm text-ink-muted">
            Host, puerto, usuario, base y URI. Contraseña oculta por defecto.
          </p>
        </div>
        <button
          type="button"
          className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-turquoise-700 disabled:text-ink-faint"
          disabled={!connection?.uri || pending}
          onClick={() => void copyUri()}
          data-testid="copy-uri"
        >
          {copied ? "URI copiada" : "Copiar URI"}
        </button>
      </div>

      {pending ? <div className="mt-4 h-32 animate-pulse rounded-sm bg-bone-sunk" /> : null}

      {error ? (
        <div className="mt-4 border-l-[3px] border-danger pl-3 text-sm text-ink">
          {problemToMessage(error)}
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
  );
}
