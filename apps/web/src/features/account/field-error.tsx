import { ApiError, problemToMessage } from "@/lib/errors";

export function FieldError({ error }: { error: unknown }) {
  if (!error) return null;
  const code = error instanceof ApiError ? error.problem?.code : undefined;
  return (
    <div
      role="alert"
      className="rounded-sm border border-danger border-l-4 bg-bone-raised px-3 py-2 text-sm text-danger"
    >
      <p className="font-medium">{problemToMessage(error)}</p>
      {code ? <p className="mt-1 font-mono text-xs text-ink-muted">{code}</p> : null}
    </div>
  );
}
