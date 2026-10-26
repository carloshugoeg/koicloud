import type { components } from "@/api/schema";
import { ApiError, problemToMessage } from "@/lib/errors";

declare const ConfirmationTokenBrand: unique symbol;

export type ConfirmationToken = string & {
  readonly [ConfirmationTokenBrand]: "ConfirmationToken";
};

export type ConfirmationProposal = {
  token: ConfirmationToken;
  summary: string;
  expiresAt: Date;
};

export type ConfirmArrival =
  | { kind: "ready"; proposal: ConfirmationProposal }
  | { kind: "invalid"; reason: "missing" | "malformed" | "disputed" };

export type ConfirmFailure = {
  message: string;
  code: string | null;
  confirmEnabled: boolean;
  discardEnabled: boolean;
};

export type ConfirmView =
  | { kind: "invalid"; reason: "missing" | "malformed" | "disputed" }
  | {
      kind: "dialog";
      proposal: ConfirmationProposal;
      countdown: string;
      expired: boolean;
      pending: "confirm" | "discard" | null;
      failure: ConfirmFailure | null;
      confirmEnabled: boolean;
      discardEnabled: boolean;
    };

type WireConfirmation = components["schemas"]["ConfirmationRequiredResponse"];

const TOKEN_PATTERN = /^[A-Za-z0-9_-]{8,128}$/;
const SUMMARY_MAX = 400;

function asToken(value: string): ConfirmationToken | null {
  if (!TOKEN_PATTERN.test(value)) {
    return null;
  }
  return value as ConfirmationToken;
}

function parseExpiresAt(value: string): Date | null {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

function proposalFromParts(
  tokenRaw: string,
  summaryRaw: string,
  expiresRaw: string,
): ConfirmationProposal | null {
  const token = asToken(tokenRaw.trim());
  const summary = summaryRaw.trim();
  const expiresAt = parseExpiresAt(expiresRaw);
  if (!token || !summary || summary.length > SUMMARY_MAX || !expiresAt) {
    return null;
  }
  return { token, summary, expiresAt };
}

function readWire(state: unknown): ConfirmationProposal | null {
  if (typeof state !== "object" || state === null) {
    return null;
  }
  const wire = state as Partial<WireConfirmation>;
  if (wire.status !== "confirmation_required") {
    return null;
  }
  if (typeof wire.token !== "string" || typeof wire.summary !== "string" || typeof wire.expires_at !== "string") {
    return null;
  }
  if (typeof wire.next !== "object" || wire.next === null) {
    return null;
  }
  return proposalFromParts(wire.token, wire.summary, wire.expires_at);
}

function sameProposal(a: ConfirmationProposal, b: ConfirmationProposal): boolean {
  return (
    a.token === b.token &&
    a.summary === b.summary &&
    a.expiresAt.getTime() === b.expiresAt.getTime()
  );
}

export function confirmSearch(proposal: ConfirmationProposal): string {
  const params = new URLSearchParams();
  params.set("token", proposal.token);
  params.set("summary", proposal.summary);
  params.set("expires_at", proposal.expiresAt.toISOString());
  return params.toString();
}

export function parseConfirmLocation(input: {
  search: string;
  state: unknown;
}): ConfirmArrival {
  const params = new URLSearchParams(input.search.startsWith("?") ? input.search.slice(1) : input.search);
  const hasQueryKey =
    params.has("token") || params.has("summary") || params.has("expires_at");

  if (hasQueryKey) {
    const token = params.get("token") ?? "";
    const summary = params.get("summary") ?? "";
    const expires = params.get("expires_at") ?? "";
    const fromQuery = proposalFromParts(token, summary, expires);
    if (!fromQuery) {
      return { kind: "invalid", reason: "malformed" };
    }
    const fromState = readWire(input.state);
    if (fromState && !sameProposal(fromQuery, fromState)) {
      return { kind: "invalid", reason: "disputed" };
    }
    return { kind: "ready", proposal: fromQuery };
  }

  const fromState = readWire(input.state);
  if (fromState) {
    return { kind: "ready", proposal: fromState };
  }
  return { kind: "invalid", reason: "missing" };
}

export function formatCountdown(
  expiresAt: Date,
  now: Date,
): { text: string; expired: boolean } {
  const remainingMs = expiresAt.getTime() - now.getTime();
  if (remainingMs <= 0) {
    return { text: "00:00", expired: true };
  }
  const totalSeconds = Math.ceil(remainingMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return {
    text: `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`,
    expired: false,
  };
}

export function controlsAfter(
  error: unknown,
  expiredLocally: boolean,
): { confirmEnabled: boolean; discardEnabled: boolean } {
  if (error instanceof ApiError && error.problem?.code) {
    const code = error.problem.code;
    if (code === "confirmation_expired") {
      return { confirmEnabled: false, discardEnabled: true };
    }
    if (
      code === "confirmation_not_found" ||
      code === "confirmation_action_mismatch"
    ) {
      return { confirmEnabled: false, discardEnabled: false };
    }
    return { confirmEnabled: false, discardEnabled: false };
  }
  if (expiredLocally) {
    return { confirmEnabled: false, discardEnabled: true };
  }
  return { confirmEnabled: true, discardEnabled: true };
}

export function confirmView(input: {
  arrival: ConfirmArrival;
  now: Date;
  pending: "confirm" | "discard" | null;
  error: unknown;
}): ConfirmView {
  if (input.arrival.kind === "invalid") {
    return { kind: "invalid", reason: input.arrival.reason };
  }

  const { proposal } = input.arrival;
  const countdown = formatCountdown(proposal.expiresAt, input.now);
  const controls = controlsAfter(input.error, countdown.expired);
  const confirmEnabled =
    input.pending === null && controls.confirmEnabled && !countdown.expired;
  const discardEnabled = input.pending === null && controls.discardEnabled;

  let failure: ConfirmFailure | null = null;
  if (input.error) {
    const code =
      input.error instanceof ApiError ? (input.error.problem?.code ?? null) : null;
    failure = {
      message: problemToMessage(input.error),
      code,
      confirmEnabled: controls.confirmEnabled,
      discardEnabled: controls.discardEnabled,
    };
  } else if (countdown.expired) {
    failure = {
      message: problemToMessage({
        code: "confirmation_expired",
        message: "confirmation_expired",
        request_id: "local",
      }),
      code: null,
      confirmEnabled: false,
      discardEnabled: true,
    };
  }

  return {
    kind: "dialog",
    proposal,
    countdown: countdown.text,
    expired: countdown.expired,
    pending: input.pending,
    failure,
    confirmEnabled,
    discardEnabled,
  };
}

export const confirmCopy = {
  overline: "Confirmación requerida",
  title: "Tu agente propuso una acción",
  help: "El resumen llegó con este enlace. El servidor ejecuta la acción que guardó con el token.",
  confirm: "Confirmar",
  confirming: "Confirmando…",
  discard: "Descartar",
  discarding: "Descartando…",
  copyToken: "Copiar token",
  copied: "Copiado",
  countdownLabel: "Expira",
  invalidTitle: "Falta una confirmación válida",
  invalidBody: "Abrí el enlace con el token, el resumen y la hora de expiración.",
  disputedBody: "El enlace y la propuesta abierta no coinciden. Pedí una confirmación nueva.",
  back: "Volver a ponds",
  confirmed: "Acción confirmada.",
  discarded: "Propuesta descartada. No se ejecutó nada.",
} as const;
