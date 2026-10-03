import { type FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useForgotPasswordMutation } from "@/api/hooks";
import { AuthErrorBanner, AuthField, AuthLayout } from "@/features/auth/auth-layout";

export function ForgotPage() {
  const forgotMutation = useForgotPasswordMutation();
  const [email, setEmail] = useState("");
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedEmail = email.trim();
    try {
      await forgotMutation.mutateAsync({ email: trimmedEmail });
      setSubmittedEmail(trimmedEmail);
    } catch {
      // Handled via forgotMutation.error
    }
  }

  if (submittedEmail) {
    return (
      <AuthLayout
        overline="E1-04 · Recuperar acceso"
        subtitle="Si el correo existe, enviamos un enlace de restablecimiento."
        title="Revisa tu correo"
        footer={
          <p>
            ¿Ya recuperaste el acceso?{" "}
            <Link className="font-medium text-turquoise-700" to="/login">
              Inicia sesión
            </Link>
          </p>
        }
      >
        <section className="space-y-4 rounded-md border border-line bg-bone-raised p-5">
          <p className="text-sm leading-6 text-ink">
            Si existe una cuenta para{" "}
            <strong className="font-mono font-medium text-ink">{submittedEmail}</strong>, vas a
            recibir un enlace. Vence en 1 hora.
          </p>
          <p className="text-sm leading-6 text-ink-muted">
            Por seguridad no confirmamos si el correo está registrado.
          </p>
          <div className="pt-2">
            <Link
              className="inline-flex h-9 items-center justify-center rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink hover:bg-bone"
              to="/login"
            >
              Volver a iniciar sesión
            </Link>
          </div>
        </section>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      overline="E1-04 · Recuperar acceso"
      subtitle="Te enviamos un enlace de un solo uso para elegir una contraseña nueva."
      title="Recuperar acceso"
      footer={
        <p>
          ¿Recordaste tu contraseña?{" "}
          <Link className="font-medium text-turquoise-700" to="/login">
            Inicia sesión
          </Link>
        </p>
      }
    >
      <form className="space-y-4" onSubmit={handleSubmit}>
        <AuthErrorBanner error={forgotMutation.error} />
        <AuthField
          id="forgot-email"
          label="Correo"
          name="email"
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="ana@ejemplo.gt"
        />
        <button
          type="submit"
          disabled={forgotMutation.isPending}
          className="h-9 w-full rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised transition-colors duration-instant ease-brand-out hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-faint"
        >
          {forgotMutation.isPending ? "Enviando…" : "Enviar enlace"}
        </button>
      </form>
    </AuthLayout>
  );
}
