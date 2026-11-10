import { type FormEvent, useState } from "react";
import { useChangePasswordMutation } from "@/api/hooks/me";
import { FieldError } from "@/features/account/field-error";
import { ApiError } from "@/lib/errors";
import {
  MIN_PASSWORD_LENGTH,
  isPasswordLongEnough,
  passwordMinHelp,
} from "@/lib/password";

export function PasswordForm() {
  const changePassword = useChangePasswordMutation();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [saved, setSaved] = useState(false);
  const [clientError, setClientError] = useState<Error | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaved(false);
    setClientError(null);
    changePassword.reset();

    if (newPassword !== confirmPassword) {
      setClientError(new Error("Las contraseñas no coinciden."));
      return;
    }
    if (!isPasswordLongEnough(newPassword)) {
      setClientError(
        new ApiError({ code: "password_too_weak", message: passwordMinHelp() }),
      );
      return;
    }

    try {
      await changePassword.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
      });
    } catch {
      return;
    }
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setSaved(true);
  }

  return (
    <section className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
        Contraseña
      </p>
      <form
        className="space-y-4 rounded-md border border-line bg-bone-raised p-5"
        noValidate
        onSubmit={(e) => void handleSubmit(e)}
      >
        <FieldError error={clientError ?? changePassword.error} />
        {saved ? (
          <p className="text-sm text-ink" data-testid="password-saved">
            Contraseña actualizada.
          </p>
        ) : null}
        <label
          className="block space-y-1.5 text-xs font-medium text-ink-muted"
          htmlFor="account-current-password"
        >
          Contraseña actual
          <input
            id="account-current-password"
            data-testid="account-current-password"
            type={showPassword ? "text" : "password"}
            className="block h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink focus:shadow-focus"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        <label
          className="block space-y-1.5 text-xs font-medium text-ink-muted"
          htmlFor="account-new-password"
        >
          Nueva contraseña
          <input
            id="account-new-password"
            data-testid="account-new-password"
            type={showPassword ? "text" : "password"}
            className="block h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink focus:shadow-focus"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            minLength={MIN_PASSWORD_LENGTH}
            required
          />
          <span className="block text-xs font-normal text-ink-muted">
            {passwordMinHelp()}
          </span>
        </label>
        <label
          className="block space-y-1.5 text-xs font-medium text-ink-muted"
          htmlFor="account-confirm-password"
        >
          Confirmar contraseña
          <input
            id="account-confirm-password"
            data-testid="account-confirm-password"
            type={showPassword ? "text" : "password"}
            className="block h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink focus:shadow-focus"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            required
          />
        </label>
        <label className="flex items-center gap-2 text-xs text-ink-muted">
          <input
            type="checkbox"
            checked={showPassword}
            onChange={(e) => setShowPassword(e.target.checked)}
          />
          Mostrar contraseñas
        </label>
        <div className="flex justify-end">
          <button
            type="submit"
            data-testid="change-password-submit"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:opacity-40"
            disabled={changePassword.isPending}
          >
            {changePassword.isPending ? "Actualizando…" : "Cambiar contraseña"}
          </button>
        </div>
      </form>
    </section>
  );
}
