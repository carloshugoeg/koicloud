import type { ReactNode } from "react";
import { ApiError, problemToMessage } from "@/lib/errors";

function errorCode(error: unknown): string {
  if (error instanceof ApiError) {
    return error.problem?.code ?? "error";
  }

  if (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { problem?: { code?: unknown } }).problem?.code === "string"
  ) {
    return (error as { problem: { code: string } }).problem.code;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string"
  ) {
    return (error as { code: string }).code;
  }

  return "error";
}

export interface DataStateLoadingProps {
  /** Number of skeleton blocks under the title bar. */
  blocks?: number;
  testId?: string;
}

/** Skeleton loading for listados — never a full-page spinner (§6.5). */
export function DataStateLoading({
  blocks = 3,
  testId = "data-state-loading",
}: DataStateLoadingProps) {
  return (
    <div className="space-y-4" data-testid={testId} role="status" aria-busy="true" aria-label="Cargando">
      <div className="data-skeleton h-10 w-48 rounded-sm" />
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: Math.min(blocks, 4) }, (_, i) => (
          <div key={i} className="data-skeleton h-28 rounded-md border border-line" />
        ))}
      </div>
      {blocks > 4 ? (
        <div className="data-skeleton h-40 rounded-md border border-line" />
      ) : null}
    </div>
  );
}

export interface DataStateEmptyProps {
  title: string;
  description: string;
  action: ReactNode;
  /** empty = 240×160 · notFound = 320×200 (§7.3). */
  pondSize?: "empty" | "notFound";
  testId?: string;
}

/** Empty listado with one pond + primary CTA (§6.5 / §7.3). */
export function DataStateEmpty({
  title,
  description,
  action,
  pondSize = "empty",
  testId = "data-state-empty",
}: DataStateEmptyProps) {
  const isLarge = pondSize === "notFound";

  return (
    <div
      className="rounded-md border border-line bg-bone-raised p-8 text-center"
      data-testid={testId}
    >
      <div
        className={[
          "pond-water-panel data-state-empty__pond mx-auto mb-4",
          isLarge ? "data-state-empty__pond--lg" : "",
        ].join(" ")}
        aria-hidden
      >
        <div className={isLarge ? "koi--x2" : "koi"} />
      </div>
      <h2 className="font-display text-2xl text-ink">{title}</h2>
      <p className="mt-2 text-sm text-ink-muted">{description}</p>
      <div className="mt-5 flex flex-wrap justify-center gap-3">{action}</div>
    </div>
  );
}

export interface DataStateErrorProps {
  error: unknown;
  onRetry: () => void;
  testId?: string;
}

/** Error band + Reintentar + raw code in mono (§6.5). */
export function DataStateError({
  error,
  onRetry,
  testId = "data-state-error",
}: DataStateErrorProps) {
  return (
    <div
      className="rounded-md border border-line bg-bone-raised p-5"
      data-testid={testId}
      role="alert"
    >
      <div className="border-l-[3px] border-danger pl-3">
        <p className="text-sm text-ink">{problemToMessage(error)}</p>
        <p className="mt-1 font-mono text-xs text-ink-faint">{errorCode(error)}</p>
      </div>
      <button
        type="button"
        className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink transition-colors duration-instant ease-brand-out hover:border-turquoise-700"
        onClick={onRetry}
      >
        Reintentar
      </button>
    </div>
  );
}

export interface DataStateSessionBootProps {
  testId?: string;
  label?: string;
}

/**
 * Arranque de sesión — estanque quieto 160×120, solo nado sin deriva (§6.5 / §7.3).
 * Única carga a pantalla completa permitida.
 */
export function DataStateSessionBoot({
  testId = "data-state-session-boot",
  label = "Iniciando sesión…",
}: DataStateSessionBootProps) {
  return (
    <div
      className="flex min-h-screen flex-col items-center justify-center gap-4 bg-bone px-4"
      data-testid={testId}
      role="status"
      aria-busy="true"
      aria-label={label}
    >
      <div className="pond-water-panel data-state-session-boot__pond" aria-hidden>
        <div className="koi data-state-session-boot__koi" />
      </div>
      <p className="text-sm text-ink-muted">{label}</p>
    </div>
  );
}
