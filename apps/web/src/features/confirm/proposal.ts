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
const PROPOSAL_QUERY_KEYS = ["token", "summary", "expires_at"] as const;

const EXPIRED_CONTROLS = { confirmEnabled: false, discardEnabled: true };
const TERMINAL_CONTROLS = { confirmEnabled: false, discardEnabled: false };
const OPEN_CONTROLS = { confirmEnabled: true, discardEnabled: true };

const CODE_CONTROLS: Record<string, { confirmEnabled: boolean; discardEnabled: boolean }> = {
  confirmation_expired: EXPIRED_CONTROLS,
};

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
  locallyExpired: "La propuesta parece vencida.",
  invalidTitle: "Falta una confirmación válida",
  invalidBody: "Abrí el enlace con el token, el resumen y la hora de expiración.",
  disputedBody: "El enlace y la propuesta abierta no coinciden. Pedí una confirmación nueva.",
  back: "Volver a ponds",
  confirmed: "Acción confirmada.",
  discarded: "Propuesta descartada. No se ejecutó nada.",
} as const;

export function confirmSearch(proposal: ConfirmationProposal): string {
  const params = new URLSearchParams();
  params.set("token", proposal.token);
  params.set("summary", proposal.summary);
  params.set("expires_at", proposal.expiresAt.toISOString());
  return `?${params.toString()}`;
}

export function parseConfirmLocation(input: {
  search: string;
  state: unknown;
}): ConfirmArrival {
  const params = new URLSearchParams(input.search);
  const queryTouched = PROPOSAL_QUERY_KEYS.some((key) => params.has(key));

  if (queryTouched) {
    const fromQuery = proposalFromParts(
      params.get("token") ?? "",
      params.get("summary") ?? "",
      new Date(params.get("expires_at") ?? ""),
    );
    if (!fromQuery) {
      return { kind: "invalid", reason: "malformed" };
    }
    const fromState = proposalFromState(input.state);
    if (
      fromState &&
      (fromState.token !== fromQuery.token ||
        fromState.summary !== fromQuery.summary ||
        fromState.expiresAt.getTime() !== fromQuery.expiresAt.getTime())
    ) {
      return { kind: "invalid", reason: "disputed" };
    }
    return { kind: "ready", proposal: fromQuery };
  }

  const fromState = proposalFromState(input.state);
  if (input.state == null) {
    return { kind: "invalid", reason: "missing" };
  }
  if (!fromState) {
    return { kind: "invalid", reason: "malformed" };
  }
  return { kind: "ready", proposal: fromState };
}

export function formatCountdown(
  expiresAt: Date,
  now: Date,
): { text: string; expired: boolean } {
  const remaining = expiresAt.getTime() - now.getTime();
  if (!Number.isFinite(remaining) || remaining <= 0) {
    return { text: "00:00", expired: true };
  }
  const totalSeconds = Math.ceil(remaining / 1000);
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
  const code = catalogCode(error);
  if (code) {
    return CODE_CONTROLS[code] ?? TERMINAL_CONTROLS;
  }
  if (expiredLocally) {
    return EXPIRED_CONTROLS;
  }
  return OPEN_CONTROLS;
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

  const countdown = formatCountdown(input.arrival.proposal.expiresAt, input.now);
  const controls = controlsAfter(input.error, countdown.expired);
  const busy = input.pending !== null;
  const confirmEnabled = !busy && controls.confirmEnabled && !countdown.expired;
  const discardEnabled = !busy && controls.discardEnabled;
  const described = describeFailure(input.error, countdown.expired);

  return {
    kind: "dialog",
    proposal: input.arrival.proposal,
    countdown: countdown.text,
    expired: countdown.expired,
    pending: input.pending,
    failure: described
      ? { ...described, confirmEnabled, discardEnabled }
      : null,
    confirmEnabled,
    discardEnabled,
  };
}

function catalogCode(error: unknown): string | null {
  if (error instanceof ApiError && error.problem?.code) {
    return error.problem.code;
  }
  return null;
}

function describeFailure(
  error: unknown,
  expiredLocally: boolean,
): { message: string; code: string | null } | null {
  const code = catalogCode(error);
  if (code) {
    return { message: problemToMessage(error), code };
  }
  if (error != null) {
    return { message: problemToMessage(error), code: null };
  }
  if (expiredLocally) {
    return { message: confirmCopy.locallyExpired, code: null };
  }
  return null;
}

function proposalFromParts(
  token: string,
  summary: string,
  expiresAt: Date,
): ConfirmationProposal | null {
  const trimmed = summary.trim();
  if (
    !TOKEN_PATTERN.test(token) ||
    trimmed.length === 0 ||
    trimmed.length > SUMMARY_MAX ||
    !Number.isFinite(expiresAt.getTime())
  ) {
    return null;
  }
  return {
    token: token as ConfirmationToken,
    summary: trimmed,
    expiresAt,
  };
}

function proposalFromState(state: unknown): ConfirmationProposal | null {
  if (!isWireConfirmation(state)) {
    return null;
  }
  return proposalFromParts(state.token, state.summary, new Date(state.expires_at));
}

function isWireConfirmation(state: unknown): state is WireConfirmation {
  if (typeof state !== "object" || state === null) {
    return false;
  }
  const record = state as Record<string, unknown>;
  if (record.status !== "confirmation_required") {
    return false;
  }
  if (typeof record.token !== "string" || typeof record.summary !== "string") {
    return false;
  }
  if (typeof record.expires_at !== "string") {
    return false;
  }
  const next = record.next;
  if (typeof next !== "object" || next === null) {
    return false;
  }
  const step = next as Record<string, unknown>;
  return typeof step.cli_example === "string" && typeof step.confirm_url === "string";
}
