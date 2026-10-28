import { SNIPPET_CLIENTS, type SnippetClientId } from "@/features/agent-access/snippets";

type AgentSnippetsProps = {
  snippet: string;
  tab: SnippetClientId;
  copied: boolean;
  onTab: (tab: SnippetClientId) => void;
  onCopy: () => void;
};

export function AgentSnippets({ snippet, tab, copied, onTab, onCopy }: AgentSnippetsProps) {
  return (
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
        onClick={onCopy}
        data-testid="copy-agent-snippet"
      >
        {copied ? "Snippet copiado" : "Copiar snippet"}
      </button>
    </section>
  );
}
