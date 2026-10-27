import { type FormEvent, useState } from "react";
import { useUpdateProfileMutation } from "@/api/hooks";
import { FieldError } from "@/features/account/delete-dialog";

type ProfileFormProps = {
  email: string;
  emailVerified: boolean;
  initialFullName: string;
  initialNit: string;
};

export function ProfileForm({
  email,
  emailVerified,
  initialFullName,
  initialNit,
}: ProfileFormProps) {
  const updateProfile = useUpdateProfileMutation();
  const [fullName, setFullName] = useState(initialFullName);
  const [nit, setNit] = useState(initialNit);
  const [saved, setSaved] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSaved(false);
    const trimmedNit = nit.trim();
    await updateProfile.mutateAsync({
      full_name: fullName.trim(),
      nit: trimmedNit ? trimmedNit : null,
    });
    setSaved(true);
  }

  return (
    <section className="space-y-3">
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
        Datos para la factura
      </p>
      <form
        className="space-y-4 rounded-md border border-line bg-bone-raised p-5"
        onSubmit={(e) => void handleSubmit(e)}
      >
        <FieldError error={updateProfile.error} />
        {saved ? (
          <p className="text-sm text-ink" data-testid="profile-saved">
            Cambios guardados.
          </p>
        ) : null}
        <label className="block space-y-1.5 text-xs font-medium text-ink-muted" htmlFor="account-full-name">
          Nombre completo
          <input
            id="account-full-name"
            className="block h-9 w-full rounded-sm border border-line-control bg-paper px-3 text-sm text-ink focus:shadow-focus"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
        </label>
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-ink-muted">Correo</p>
          <p className="h-9 rounded-sm border border-line bg-bone-sunk px-3 font-mono text-sm leading-9 text-ink-muted">
            {email}
          </p>
          <p className="text-xs text-ink-muted">
            {emailVerified ? "Correo verificado." : "Correo sin verificar."}
          </p>
        </div>
        <label className="block space-y-1.5 text-xs font-medium text-ink-muted" htmlFor="account-nit">
          NIT
          <input
            id="account-nit"
            className="block h-9 w-full rounded-sm border border-line-control bg-paper px-3 font-mono text-sm text-ink focus:shadow-focus"
            value={nit}
            onChange={(e) => setNit(e.target.value)}
            placeholder="CF"
          />
          <span className="block text-xs font-normal text-ink-muted">
            Escribe CF si no tienes NIT. Aparece en la factura tal cual.
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <button
            type="submit"
            className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised disabled:opacity-40"
            disabled={updateProfile.isPending}
          >
            {updateProfile.isPending ? "Guardando…" : "Guardar cambios"}
          </button>
        </div>
      </form>
    </section>
  );
}
