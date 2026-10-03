import { type FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useResetPasswordMutation } from "@/api/hooks";
import { AuthErrorBanner, AuthField, AuthLayout } from "@/features/auth/auth-layout";
import { ApiError } from "@/lib/errors";

export function ResetPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token")?.trim() ?? "";
  const resetMutation = useResetPasswordMutation();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<ApiError | null>(null);

  const missingTokenError = !token
    ? new ApiError({
        code: "token_invalid",
        message: "El enlace de restablecimiento no incluye un token válido.",
        request_id: "client_missing_reset_token",
      })
    : null;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLocalError(null);
    if (!token) return;
    if (password !== confirmPassword) {
      setLocalError(
        new ApiError({
          code: "password_too_weak",
          message: "Las contraseñas no coinciden.",
          request_id: "client_password_mismatch",
        }),
      );
      return;
    }
    try {
      await resetMutation.mutateAsync({ token, new_password: password });
    } catch {
      // Handled via resetMutation.error
    }
  }

  if (resetMutation.isSuccess) {
    return (
      <AuthLayout
        overline="E1-04 · Restablecer contraseña"
        subtitle="Tu contraseña quedó actualizada."
        title="Contraseña actualizada"
        footer={
          <p>
            <Link className="font-medium text-turquoise-700" to="/login">
              Ir a iniciar sesión
            </Link>
          </p>
        }
      >
        <section className="space-y-4 rounded-md border border-line bg-bone-raised p-5">
          <span className="inline-flex items-center gap-1.5 rounded-sm bg-green-100 px-2 py-1 font-mono text-xs font-medium text-ink">
            <span aria-hidden="true">●</span>
            <span>password_reset = true</span>
          </span>
          <p className="text-sm leading-6 text-ink">
            El token se consumió. Ya podés iniciar sesión con la contraseña nueva.
          </p>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900"
          >
            Continuar a iniciar sesión
          </button>
        </section>
      </AuthLayout>
    );
  }

  const activeError = resetMutation.error ?? localError ?? missingTokenError;
  const tokenFailed =
    activeError instanceof ApiError &&
    (activeError.problem?.code === "token_invalid" || activeError.problem?.code === "token_expired");

  return (
    <AuthLayout
      overline="E1-04 · Restablecer contraseña"
      subtitle="Elegí una contraseña nueva. El enlace vence en 1 hora y es de un solo uso."
      title="Restablecer contraseña"
      footer={
        <div className="flex flex-wrap items-center gap-3">
          <Link className="font-medium text-turquoise-700" to="/forgot">
            Solicitar otro enlace
          </Link>
          <span>·</span>
          <Link className="font-medium text-turquoise-700" to="/login">
            Iniciar sesión
          </Link>
        </div>
      }
    >
      {tokenFailed && !resetMutation.isPending ? (
        <section className="space-y-4">
          <AuthErrorBanner error={activeError} />
          <div className="rounded-md border border-line bg-bone-raised p-4 text-sm text-ink-muted">
            <p>El enlace ya no sirve. Pedí uno nuevo desde recuperación de acceso.</p>
            <div className="pt-3">
              <Link
                className="inline-flex h-9 items-center justify-center rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900"
                to="/forgot"
              >
                Volver a recuperar acceso
              </Link>
            </div>
          </div>
        </section>
      ) : (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <AuthErrorBanner error={activeError} />
          <AuthField
            id="reset-password"
            label="Nueva contraseña"
            name="new_password"
            type={showPassword ? "text" : "password"}
            required
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••"
            help="Mínimo 8 caracteres."
            suffix={
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-1.5 rounded-sm px-2 py-1 text-xs font-medium text-turquoise-700 hover:bg-bone"
              >
                {showPassword ? "Ocultar" : "Mostrar"}
              </button>
            }
          />
          <AuthField
            id="reset-password-confirm"
            label="Confirmar contraseña"
            name="confirm_password"
            type={showPassword ? "text" : "password"}
            required
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="••••••••••"
          />
          <button
            type="submit"
            disabled={resetMutation.isPending || !token}
            className="h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint"
          >
            {resetMutation.isPending ? "Guardando…" : "Guardar contraseña"}
          </button>
        </form>
      )}
    </AuthLayout>
  );
}
