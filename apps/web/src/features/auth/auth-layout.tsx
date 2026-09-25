import type { InputHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";
import { ApiError, problemToMessage } from "@/lib/errors";

interface AuthLayoutProps {
  title: string;
  subtitle?: string;
  overline?: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ title, subtitle, overline, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full overflow-x-hidden bg-bone text-ink lg:grid lg:grid-cols-[40%_60%]">
      <aside
        aria-label="Estanque KoiCloud"
        className="pond-water-auth relative flex min-h-[160px] flex-col justify-between overflow-hidden border-b border-line p-5 lg:min-h-screen lg:border-r lg:border-b-0 lg:p-8"
      >
        <Link className="relative z-10 inline-flex w-fit items-center gap-3 rounded-sm bg-bone-raised/95 px-3 py-2 text-ink no-underline shadow-print" to="/">
          <span aria-hidden="true" className="koi-mark-32 shrink-0" />
          <span className="font-display text-2xl font-semibold tracking-tight text-ink">KoiCloud</span>
        </Link>
        <div aria-hidden="true" className="pointer-events-none relative my-4 flex flex-1 items-center justify-center">
          <i className="koi--x2 block" />
        </div>
        <p className="relative z-10 hidden max-w-xs rounded-sm bg-bone-raised/95 px-3 py-2 text-xs leading-5 text-ink-muted shadow-print lg:block">
          PostgreSQL 16 administrado en contenedores dedicados.
        </p>
      </aside>
      <main className="flex min-h-[calc(100vh-160px)] flex-col items-center justify-center px-4 py-8 sm:px-6 lg:min-h-screen lg:px-12">
        <div className="w-full max-w-[400px] space-y-6">
          <header className="space-y-2 border-b border-line pb-4">
            {overline ? <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">{overline}</p> : null}
            <h1 className="font-display text-3xl font-semibold text-ink">{title}</h1>
            {subtitle ? <p className="text-sm leading-5 text-ink-muted">{subtitle}</p> : null}
          </header>
          {children}
          {footer ? <footer className="border-t border-line pt-4 text-sm text-ink-muted">{footer}</footer> : null}
        </div>
      </main>
    </div>
  );
}

interface AuthFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  id: string;
  label: string;
  help?: string;
  suffix?: ReactNode;
}

export function AuthField({ id, label, help, suffix, ...props }: AuthFieldProps) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-medium text-ink-muted" htmlFor={id}>{label}</label>
      <div className="relative flex items-center">
        <input
          id={id}
          className={`h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink focus:border-turquoise-700 ${suffix ? "pr-20" : ""}`}
          {...props}
        />
        {suffix}
      </div>
      {help ? <p className="text-xs leading-4 text-ink-muted">{help}</p> : null}
    </div>
  );
}

export function AuthErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  const message = problemToMessage(error);
  const code = error instanceof ApiError ? error.problem?.code : undefined;

  return (
    <div role="alert" className="rounded-sm border border-danger border-l-4 bg-bone-raised px-3 py-2.5 text-sm text-danger">
      <div className="flex items-start gap-2">
        <span aria-hidden="true" className="font-semibold">✕</span>
        <div className="space-y-1">
          <p className="font-medium text-danger">{message}</p>
          {code ? <p className="font-mono text-xs text-ink-faint">{code}</p> : null}
        </div>
      </div>
    </div>
  );
}
