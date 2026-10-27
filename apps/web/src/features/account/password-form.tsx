import { type FormEvent, useState } from "react";
import { useChangePasswordMutation } from "@/api/hooks";
import { ApiError } from "@/lib/errors";
import {
  MIN_PASSWORD_LENGTH,
  isPasswordLongEnough,
  passwordMinHelp,
} from "@/lib/password";
import { FieldError } from "@/features/account/delete-dialog";

export function PasswordForm() {
  const changePassword = useChangePasswordMutation();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [saved, setSaved] = useState(false);
  const [clientError, setClientError] = useState<ApiError | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaved(false);
    setClientError(null);
    if (!isPasswordLongEnough(newPassword)) {
      setClientError(new ApiError({ code: "password_too_weak", message: passwordMinHelp() }));
      return;
    }
    await changePassword.mutateAsync({
      current_password: currentPassword,
      new_password: newPassword,
    });
    setCurrentPassword("");
    setNewPassword("");
    setSaved(true);
  }

  return (
    <section className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">Contraseña</p>
      <form
        className="space-y-4 rounded-md border border-line bg-bone-raised p-5"
        noValidate
        onSubmit={(e) => void handleSubmit(e)}
      >
        <FieldError error={clientError ?? changePassword.error} />
        {saved ? (
          <p className="text-sm text-ink" data-testid="password-saved">
            Contraseña actualizada. Las otras sesiones se cerraron.
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
          Contraseña nueva
          <div className="relative">
            <input
              id="account-new-password"
              data-testid="account-new-password"
              type={showPassword ? "text" : "password"}
              className="block h-9 w-full rounded-sm border border-line-control bg-paper px-3 pr-20 text-sm text-ink focus:shadow-focus"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              autoComplete="new-password"
              minLength={MIN_PASSWORD_LENGTH}
              required
            />
            <button
              type="button"
              className="absolute right-1.5 top-1.5 rounded-sm px-2 py-1 text-xs font-medium text-turquoise-700"
              onClick={() => setShowPassword((v) => !v)}
            >
              {showPassword ? "Ocultar" : "Mostrar"}
            </button>
          </div>
          <span className="block text-xs font-normal text-ink-muted">
            {passwordMinHelp("Al cambiarla cerramos las otras sesiones.")}
          </span>
        </label>
        <div className="flex justify-end">
          <button
            type="submit"
            data-testid="change-password-submit"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:opacity-40"
            disabled={changePassword.isPending}
          >
            {changePassword.isPending ? "Cambiando…" : "Cambiar contraseña"}
          </button>
        </div>
      </form>
    </section>
  );
}
