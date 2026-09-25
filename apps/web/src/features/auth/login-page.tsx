import { type FormEvent, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useLoginMutation } from "@/api/hooks";
import { AuthErrorBanner, AuthField, AuthLayout } from "@/features/auth/auth-layout";

interface LocationStateWithFrom {
  from?: { pathname?: string; search?: string };
}

function resolveNextPath(nextParam: string | null, locationState: unknown): string {
  if (nextParam && nextParam.startsWith("/") && !nextParam.startsWith("//")) return nextParam;
  const from = (locationState as LocationStateWithFrom | null)?.from;
  if (from?.pathname && from.pathname.startsWith("/")) return `${from.pathname}${from.search ?? ""}`;
  return "/app";
}

export function LoginPage() {
  const loginMutation = useLoginMutation();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const targetPath = resolveNextPath(searchParams.get("next"), location.state);
    try {
      await loginMutation.mutateAsync({ email: email.trim(), password });
      navigate(targetPath, { replace: true });
    } catch {
      // Handled via loginMutation.error
    }
  }

  return (
    <AuthLayout
      overline="E1-03 · Iniciar sesión"
      subtitle="Entra a tu estanque para gestionar tus instancias de PostgreSQL."
      title="Iniciar sesión"
      footer={
        <div className="flex flex-wrap items-center gap-3">
          <Link className="font-medium text-turquoise-700" to="/forgot">Recuperar contraseña</Link>
          <span>·</span>
          <Link className="font-medium text-turquoise-700" to="/register">Crear cuenta</Link>
        </div>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <AuthErrorBanner error={loginMutation.error} />
        <AuthField id="login-email" label="Correo" name="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ana@ejemplo.gt" />
        <AuthField
          id="login-password"
          label="Contraseña"
          name="password"
          type={showPassword ? "text" : "password"}
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••"
          suffix={
            <button type="button" onClick={() => setShowPassword((prev) => !prev)} className="absolute right-1.5 rounded-sm px-2 py-1 text-xs font-medium text-turquoise-700 hover:bg-bone">
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          }
        />
        <button type="submit" disabled={loginMutation.isPending} className="h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint">
          {loginMutation.isPending ? "Iniciando sesión…" : "Iniciar sesión"}
        </button>
      </form>
    </AuthLayout>
  );
}
