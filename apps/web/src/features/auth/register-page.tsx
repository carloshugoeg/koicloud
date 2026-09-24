import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useRegisterMutation } from "@/api/hooks";
import { AuthErrorBanner, AuthField, AuthLayout } from "@/features/auth/auth-layout";

export function RegisterPage() {
  const registerMutation = useRegisterMutation();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nit, setNit] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim();
    const trimmedNit = nit.trim();
    try {
      await registerMutation.mutateAsync({
        full_name: fullName.trim(),
        email: trimmedEmail,
        password,
        nit: trimmedNit ? trimmedNit : null,
      });
      setSubmittedEmail(trimmedEmail);
    } catch {
      // Handled via registerMutation.error
    }
  }

  if (submittedEmail) {
    return (
      <AuthLayout
        overline="E1-02 · Verificar correo"
        subtitle="Tu cuenta fue creada y requiere verificación antes de iniciar sesión."
        title="Revisa tu correo"
        footer={<p>¿Ya verificaste tu cuenta? <Link className="font-medium text-turquoise-700" to="/login">Inicia sesión</Link></p>}
      >
        <section className="space-y-4 rounded-md border border-line bg-bone-raised p-5">
          <p className="text-sm leading-6 text-ink">
            Enviamos el enlace a <strong className="font-mono font-medium text-ink">{submittedEmail}</strong>. Vence en 24 horas.
          </p>
          <span className="inline-flex items-center gap-1.5 rounded-sm bg-turquoise-100 px-2 py-1 font-mono text-xs font-medium text-ink">
            <span aria-hidden="true">◐</span>
            <span>email_verified = false</span>
          </span>
          <div className="pt-2">
            <Link className="inline-flex h-9 items-center justify-center rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink hover:bg-bone" to="/login">
              Ir a iniciar sesión
            </Link>
          </div>
        </section>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      overline="E1-01 · Registro"
      subtitle="Te enviamos un enlace de verificación con 24 horas de vigencia."
      title="Crea tu cuenta"
      footer={<p>¿Ya tienes cuenta? <Link className="font-medium text-turquoise-700" to="/login">Inicia sesión</Link></p>}
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <AuthErrorBanner error={registerMutation.error} />
        <AuthField id="register-full-name" label="Nombre completo" name="full_name" type="text" required autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Ana López" />
        <AuthField id="register-email" label="Correo" name="email" type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ana@ejemplo.gt" />
        <AuthField
          id="register-password"
          label="Contraseña"
          name="password"
          type={showPassword ? "text" : "password"}
          required
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="••••••••••"
          help="Mínimo 10 caracteres. No uses una contraseña que ya tengas en otro servicio."
          suffix={
            <button type="button" onClick={() => setShowPassword((prev) => !prev)} className="absolute right-1.5 rounded-sm px-2 py-1 text-xs font-medium text-turquoise-700 hover:bg-bone">
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          }
        />
        <AuthField id="register-nit" label="NIT (opcional)" name="nit" type="text" value={nit} onChange={(e) => setNit(e.target.value)} placeholder="0614-100199-102-4" help="CF o vacío si no requieres NIT en tus facturas." />
        <button type="submit" disabled={registerMutation.isPending} className="h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint">
          {registerMutation.isPending ? "Creando…" : "Crear cuenta"}
        </button>
      </form>
    </AuthLayout>
  );
}
