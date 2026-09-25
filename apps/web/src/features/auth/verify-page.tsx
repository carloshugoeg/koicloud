import { useEffect, useRef } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useVerifyEmailMutation } from "@/api/hooks";
import { AuthErrorBanner, AuthLayout } from "@/features/auth/auth-layout";
import { ApiError } from "@/lib/errors";

export function VerifyPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token")?.trim() ?? "";
  const verifyMutation = useVerifyEmailMutation();
  const consumedTokenRef = useRef<string | null>(null);

  useEffect(() => {
    if (!token || consumedTokenRef.current === token) return;
    consumedTokenRef.current = token;
    verifyMutation.mutate({ token });
  }, [token, verifyMutation]);

  const missingTokenError = !token
    ? new ApiError({
        code: "token_invalid",
        message: "El enlace de verificación no incluye un token válido.",
        request_id: "client_missing_token",
      })
    : null;
  const activeError = verifyMutation.error ?? missingTokenError;

  return (
    <AuthLayout
      overline="E1-02 · Verificar correo"
      subtitle="Confirmación del enlace enviado a tu correo electrónico."
      title="Verificar correo"
      footer={
        <div className="flex flex-wrap items-center gap-3">
          <Link className="font-medium text-turquoise-700" to="/login">Iniciar sesión</Link>
          <span>·</span>
          <Link className="font-medium text-turquoise-700" to="/register">Crear cuenta</Link>
        </div>
      }
    >
      {verifyMutation.isPending ? (
        <section aria-live="polite" className="space-y-3 rounded-md border border-line bg-bone-raised p-5">
          <span className="inline-flex items-center gap-1.5 rounded-sm bg-turquoise-100 px-2 py-1 font-mono text-xs font-medium text-ink">
            <span aria-hidden="true">◐</span>
            <span>Verificando enlace…</span>
          </span>
          <p className="text-sm text-ink-muted">Estamos validando tu token de verificación.</p>
        </section>
      ) : null}

      {verifyMutation.isSuccess ? (
        <section className="space-y-4 rounded-md border border-line bg-bone-raised p-5">
          <span className="inline-flex items-center gap-1.5 rounded-sm bg-green-100 px-2 py-1 font-mono text-xs font-medium text-ink">
            <span aria-hidden="true">●</span>
            <span>email_verified = true</span>
          </span>
          <p className="text-sm leading-6 text-ink">
            Tu correo quedó verificado. Ya puedes iniciar sesión para entrar a tu estanque.
          </p>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
          >
            Continuar a iniciar sesión
          </button>
        </section>
      ) : null}

      {activeError && !verifyMutation.isPending ? (
        <section className="space-y-4">
          <AuthErrorBanner error={activeError} />
          <div className="rounded-md border border-line bg-bone-raised p-4 text-sm text-ink-muted">
            <p>Solicita un nuevo enlace desde el registro o inicia sesión si ya verificaste tu cuenta.</p>
          </div>
        </section>
      ) : null}
    </AuthLayout>
  );
}
