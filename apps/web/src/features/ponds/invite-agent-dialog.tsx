import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import type { components } from "@/api/schema";
import {
  useCreatePondTempAccessMutation,
  useListPondTempAccess,
  useRevokePondTempAccessMutation,
} from "@/api/hooks/ponds";
import { ModalDialog } from "@/components/modal-dialog";
import { InviteAgentQr } from "@/features/ponds/invite-agent-qr";
import {
  buildInviteConsoleSnippet,
  INVITE_CONSOLE_CLIENTS,
  type InviteConsoleClientId,
} from "@/features/ponds/invite-console-snippets";
import { problemToMessage } from "@/lib/errors";

type PondTempAccessOut = components["schemas"]["PondTempAccessOut"];
type PondTempAccessSecretOut = components["schemas"]["PondTempAccessSecretOut"];

type InviteAgentDialogProps = {
  pondId: string;
  returnFocusRef: RefObject<HTMLElement | null>;
  onClose: () => void;
};

function isUsable(token: PondTempAccessOut, now = Date.now()) {
  if (token.revoked_at) return false;
  return Date.parse(token.expires_at) > now;
}

function defaultExpiresAt() {
  return new Date(Date.now() + 60 * 60 * 1000).toISOString();
}

export function InviteAgentDialog({ pondId, returnFocusRef, onClose }: InviteAgentDialogProps) {
  const listQuery = useListPondTempAccess(pondId);
  const createMutation = useCreatePondTempAccessMutation(pondId);
  const revokeMutation = useRevokePondTempAccessMutation(pondId);
  const [secret, setSecret] = useState<PondTempAccessSecretOut | null>(null);
  const [revoked, setRevoked] = useState(false);
  const [tab, setTab] = useState<InviteConsoleClientId>("claude_code");
  const generateRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  const activeToken = useMemo(() => {
    const tokens = listQuery.data ?? [];
    return tokens.find((token) => isUsable(token)) ?? null;
  }, [listQuery.data]);

  const display = useMemo(() => {
    if (secret) {
      return {
        id: secret.id,
        url: secret.url,
        slug: secret.slug,
        password: secret.password as string | null,
      };
    }
    if (activeToken && !revoked) {
      return {
        id: activeToken.id,
        url: activeToken.url,
        slug: activeToken.slug,
        password: null as string | null,
      };
    }
    return null;
  }, [secret, activeToken, revoked]);

  const snippet = display
    ? buildInviteConsoleSnippet(tab, {
        url: display.url,
        slug: display.slug,
        password: display.password,
      })
    : "";

  useEffect(() => {
    if (display || revoked) {
      closeRef.current?.focus();
    }
  }, [display, revoked]);

  async function handleGenerate() {
    setRevoked(false);
    try {
      const created = await createMutation.mutateAsync({ expires_at: defaultExpiresAt() });
      setSecret(created);
    } catch {
      // surfaced below via createMutation.error
    }
  }

  async function handleRevoke() {
    const tokenId = display?.id;
    if (!tokenId) return;
    try {
      await revokeMutation.mutateAsync(tokenId);
      setSecret(null);
      setRevoked(true);
    } catch {
      // surfaced below
    }
  }

  const error =
    createMutation.isError
      ? problemToMessage(createMutation.error)
      : revokeMutation.isError
        ? problemToMessage(revokeMutation.error)
        : listQuery.isError
          ? problemToMessage(listQuery.error)
          : null;

  return (
    <ModalDialog
      titleId="invite-agent-title"
      onClose={onClose}
      returnFocusRef={returnFocusRef}
      data-testid="invite-agent-dialog"
      initialFocusRef={generateRef}
      className="dialog-veil fixed inset-0 z-50 flex items-center justify-center p-4"
      panelClassName="relative z-10 flex max-h-[90vh] w-full max-w-lg flex-col overflow-hidden rounded-md border border-line-control bg-bone-raised shadow-dialog"
      closeLabel="Cerrar fondo del diálogo"
    >
      <div className="h-1 bg-turquoise-700" />
      <div className="space-y-4 overflow-y-auto p-5">
        <div className="flex items-start justify-between gap-3">
          <h3 id="invite-agent-title" className="font-display text-2xl text-ink">
            Invitar agente
          </h3>
          <button
            ref={closeRef}
            type="button"
            className="h-9 rounded-sm border border-line-control bg-bone-raised px-3 text-sm font-medium text-ink focus:shadow-focus"
            onClick={onClose}
            data-testid="close-invite-agent"
          >
            Cerrar
          </button>
        </div>
        <p className="text-sm text-ink-muted">
          Generá un link temporal con contraseña para Claude Code, Cursor CLI o Codex CLI. La
          contraseña solo se muestra al crearla.
        </p>

        {error ? (
          <p className="text-sm text-danger" data-testid="invite-agent-error">
            {error}
          </p>
        ) : null}

        {revoked ? (
          <div
            className="rounded-sm border border-danger bg-danger-soft px-3 py-2 text-sm text-ink"
            data-testid="invite-agent-revoked"
          >
            Credencial revocada. La autenticación MCP con ese link y contraseña falla a partir de
            ahora.
          </div>
        ) : null}

        {!display && !revoked ? (
          <button
            ref={generateRef}
            type="button"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint focus:shadow-focus"
            onClick={() => void handleGenerate()}
            disabled={createMutation.isPending}
            data-testid="generate-invite-agent"
          >
            {createMutation.isPending ? "Generando…" : "Generar link temporal"}
          </button>
        ) : null}

        {display ? (
          <div className="space-y-4" data-testid="invite-agent-active">
            <dl className="grid gap-3 text-sm">
              <div>
                <dt className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
                  Link MCP
                </dt>
                <dd
                  className="mt-1 break-all font-mono text-sm text-ink"
                  data-testid="invite-agent-url"
                >
                  {display.url}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
                  Slug
                </dt>
                <dd className="mt-1 font-mono text-sm text-ink" data-testid="invite-agent-slug">
                  {display.slug}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
                  Contraseña
                </dt>
                <dd className="mt-1">
                  {display.password ? (
                    <span
                      className="font-mono text-sm text-ink"
                      data-testid="invite-agent-password"
                    >
                      {display.password}
                    </span>
                  ) : (
                    <span className="text-sm text-ink-muted" data-testid="invite-agent-password-hidden">
                      Oculta. Solo se mostró al generar el link.
                    </span>
                  )}
                </dd>
              </div>
            </dl>

            <div>
              <p className="mb-2 text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
                Código QR del enlace
              </p>
              <InviteAgentQr url={display.url} />
            </div>

            <section data-testid="invite-agent-snippets">
              <div role="tablist" aria-label="Agentes de consola" className="flex flex-wrap gap-2">
                {INVITE_CONSOLE_CLIENTS.map((client) => {
                  const selected = tab === client.id;
                  return (
                    <button
                      key={client.id}
                      type="button"
                      role="tab"
                      aria-selected={selected}
                      className={
                        selected
                          ? "h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised focus:shadow-focus"
                          : "h-9 rounded-sm border border-line-control bg-bone px-4 text-sm font-medium text-ink focus:shadow-focus"
                      }
                      onClick={() => setTab(client.id)}
                    >
                      {client.label}
                    </button>
                  );
                })}
              </div>
              <pre
                className="mt-4 max-h-48 overflow-auto rounded-sm border border-line bg-paper p-3 font-mono text-xs text-ink"
                data-testid="invite-agent-snippet"
                tabIndex={0}
                role="region"
                aria-label="Instrucciones para pegar en el agente"
              >
                {snippet}
              </pre>
            </section>

            <button
              type="button"
              className="h-9 rounded-sm border border-danger bg-bone-raised px-4 text-sm font-medium text-danger focus:shadow-focus disabled:border-line-control disabled:text-ink-faint"
              onClick={() => void handleRevoke()}
              disabled={revokeMutation.isPending}
              data-testid="revoke-invite-agent"
            >
              {revokeMutation.isPending ? "Revocando…" : "Revocar acceso"}
            </button>
          </div>
        ) : null}
      </div>
    </ModalDialog>
  );
}
