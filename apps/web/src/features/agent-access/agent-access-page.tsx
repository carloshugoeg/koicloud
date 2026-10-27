import { useState } from "react";
import {
  useAgentAccessQuery,
  useRotateAgentPasswordMutation,
  useToggleAgentAccessMutation,
  type AgentAccess,
} from "@/api/hooks/agent-access";
import { ApiError, problemToMessage } from "@/lib/errors";
import { buildAgentSnippet, SNIPPET_CLIENTS, type SnippetClientId } from "@/features/agent-access/snippets";

type SecretPhase = { phase: "sealed" } | { phase: "revealed"; password: string } | { phase: "dismissed" };

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

function agentDisabledCopy() {
  return problemToMessage({ code: "agent_disabled", message: "agent_disabled" });
}

export function AgentAccessPage() {
  const accessQuery = useAgentAccessQuery();
  const rotate = useRotateAgentPasswordMutation();
  const toggle = useToggleAgentAccessMutation();
  const [secret, setSecret] = useState<SecretPhase>({ phase: "sealed" });
  const [tab, setTab] = useState<SnippetClientId>("claude");
  const [copied, setCopied] = useState<"url" | "password" | "snippet" | null>(null);

  async function copyText(kind: "url" | "password" | "snippet", value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(kind);
    window.setTimeout(() => setCopied(null), 1_200);
  }

  if (accessQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="agent-access-loading">
        <div className="h-10 w-64 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-56 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (accessQuery.isError || !accessQuery.data) {
    const code =
      accessQuery.error instanceof ApiError ? accessQuery.error.problem?.code : undefined;
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="agent-access-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(accessQuery.error)}</p>
          {code ? <p className="mt-1 font-mono text-xs text-ink-faint">{code}</p> : null}
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void accessQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const access = accessQuery.data;
  const password = secret.phase === "revealed" ? secret.password : null;
  const snippet = buildAgentSnippet(tab, { url: access.url, slug: access.slug, password });
  const actionError = rotate.error ?? toggle.error;
  const actionCode = actionError instanceof ApiError ? actionError.problem?.code : undefined;

  return (
    <AgentAccessCard
      access={access}
      password={password}
      snippet={snippet}
      tab={tab}
      copied={copied}
      pendingRotate={rotate.isPending}
      pendingToggle={toggle.isPending}
      actionMessage={actionError ? problemToMessage(actionError) : null}
      actionCode={actionCode}
      onTab={setTab}
      onRotate={() => {
        rotate.mutate(undefined, {
          onSuccess: (data) => {
            setSecret({ phase: "revealed", password: data.password });
          },
        });
      }}
      onHide={() => setSecret({ phase: "dismissed" })}
      onToggle={() => toggle.mutate(!access.enabled)}
      onCopy={(kind, value) => void copyText(kind, value)}
    />
  );
}

function AgentAccessCard({
  access,
  password,
  snippet,
  tab,
  copied,
  pendingRotate,
  pendingToggle,
  actionMessage,
  actionCode,
  onTab,
  onRotate,
  onHide,
  onToggle,
  onCopy,
}: {
  access: AgentAccess;
  password: string | null;
  snippet: string;
  tab: SnippetClientId;
  copied: "url" | "password" | "snippet" | null;
  pendingRotate: boolean;
  pendingToggle: boolean;
  actionMessage: string | null;
  actionCode: string | undefined;
  onTab: (tab: SnippetClientId) => void;
  onRotate: () => void;
  onHide: () => void;
  onToggle: () => void;
  onCopy: (kind: "url" | "password" | "snippet", value: string) => void;
}) {
  const disabledNote = !access.enabled || actionCode === "agent_disabled";

  return (
    <div className="space-y-5" data-testid="agent-access">
      <div>
        <h2 className="font-display text-3xl text-ink">Acceso agente</h2>
        <p className="mt-1 text-sm text-ink-muted">
          URL MCP y slug. La contraseña aparece una sola vez después de rotarla.
        </p>
      </div>

      <section className="rounded-md border border-line bg-paper p-5" data-testid="agent-access-card">
        <dl className="grid gap-3 font-mono text-sm text-ink md:grid-cols-2">
          <div>
            <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Slug</dt>
            <dd data-testid="agent-slug">{access.slug}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Estado</dt>
            <dd data-testid="agent-enabled">{access.enabled ? "habilitado" : "deshabilitado"}</dd>
          </div>
          <div className="md:col-span-2">
            <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">URL</dt>
            <dd className="break-all" data-testid="agent-url">
              {access.url}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-[0.14em] text-ink-muted">Rotada</dt>
            <dd data-testid="agent-rotated-at">{formatStamp(access.rotated_at)}</dd>
          </div>
        </dl>

        <div className="mt-4 flex flex-wrap gap-2">
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-turquoise-700"
            onClick={() => onCopy("url", access.url)}
            data-testid="copy-agent-url"
          >
            {copied === "url" ? "URL copiada" : "Copiar URL"}
          </button>
          <button
            type="button"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:opacity-60"
            disabled={pendingRotate}
            onClick={onRotate}
            data-testid="rotate-agent-password"
          >
            {pendingRotate ? "Rotando…" : "Rotar contraseña"}
          </button>
          <button
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
            disabled={pendingToggle}
            onClick={onToggle}
            data-testid="toggle-agent-access"
          >
            {access.enabled ? "Desactivar acceso" : "Activar acceso"}
          </button>
        </div>

        {password ? (
          <div className="mt-4 rounded-sm bg-marigold px-4 py-3 text-ink" data-testid="agent-password-band">
            <p className="text-xs uppercase tracking-[0.14em]">Contraseña de un solo uso</p>
            <p className="mt-1 break-all font-mono text-sm" data-testid="agent-password">
              {password}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                className="h-9 rounded-sm bg-ink px-4 text-sm font-medium text-bone-raised"
                onClick={() => onCopy("password", password)}
                data-testid="copy-agent-password"
              >
                {copied === "password" ? "Contraseña copiada" : "Copiar contraseña"}
              </button>
              <button
                type="button"
                className="h-9 rounded-sm border border-ink/30 bg-marigold px-4 text-sm font-medium"
                onClick={onHide}
                data-testid="hide-agent-password"
              >
                Ocultar
              </button>
            </div>
          </div>
        ) : (
          <p className="mt-4 text-sm text-ink-muted" data-testid="agent-password-hidden">
            La contraseña no se muestra. Rotá para verla una vez.
          </p>
        )}

        {disabledNote ? (
          <p className="mt-4 border-l-[3px] border-marigold pl-3 text-sm text-ink" data-testid="agent-disabled-note">
            {agentDisabledCopy()}
            {actionCode ? <span className="mt-1 block font-mono text-xs text-ink-faint">{actionCode}</span> : null}
          </p>
        ) : null}

        {actionMessage && actionCode !== "agent_disabled" ? (
          <p className="mt-4 border-l-[3px] border-danger pl-3 text-sm text-ink" data-testid="agent-action-error">
            {actionMessage}
            {actionCode ? <span className="mt-1 block font-mono text-xs text-ink-faint">{actionCode}</span> : null}
          </p>
        ) : null}
      </section>

      <section className="rounded-md border border-line bg-bone-raised p-5" data-testid="agent-snippets">
        <div role="tablist" aria-label="Clientes del agente" className="flex flex-wrap gap-2">
          {SNIPPET_CLIENTS.map((client) => {
            const selected = tab === client.id;
            return (
              <button
                key={client.id}
                type="button"
                role="tab"
                aria-selected={selected}
                className={
                  selected
                    ? "h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised"
                    : "h-9 rounded-sm border border-line-control bg-bone px-4 text-sm font-medium text-ink"
                }
                onClick={() => onTab(client.id)}
              >
                {client.label}
              </button>
            );
          })}
        </div>
        <pre
          className="mt-4 overflow-x-auto rounded-sm bg-ink p-4 font-mono text-xs text-bone-raised"
          data-testid="agent-snippet"
          tabIndex={0}
          role="region"
          aria-label="Snippet de conexión del agente"
        >
          {snippet}
        </pre>
        <button
          type="button"
          className="mt-3 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-turquoise-700"
          onClick={() => onCopy("snippet", snippet)}
          data-testid="copy-agent-snippet"
        >
          {copied === "snippet" ? "Snippet copiado" : "Copiar snippet"}
        </button>
      </section>
    </div>
  );
}
