import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  useDeleteMeMutation,
  useMeQuery,
  useResendVerificationMutation,
} from "@/api/hooks";
import { DeleteAccountDialog, FieldError } from "@/features/account/delete-dialog";
import { PasswordForm } from "@/features/account/password-form";
import { ProfileForm } from "@/features/account/profile-form";

export function AccountPage() {
  const navigate = useNavigate();
  const meQuery = useMeQuery();
  const deleteMe = useDeleteMeMutation();
  const resend = useResendVerificationMutation();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const deleteOpenRef = useRef<HTMLButtonElement>(null);

  if (meQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="account-loading">
        <div className="h-10 w-48 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-64 max-w-[560px] animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (meQuery.isError || !meQuery.data) {
    return (
      <div
        className="max-w-[560px] rounded-md border border-line bg-bone-raised p-5"
        data-testid="account-error"
      >
        <FieldError error={meQuery.error} />
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void meQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const user = meQuery.data.user;
  const pondsCount = meQuery.data.ponds_count;

  return (
    <div className="mx-auto w-full max-w-[560px] space-y-8" data-testid="account-page">
      <header className="space-y-1 border-b border-line pb-4">
        <h1 className="font-display text-3xl font-semibold text-ink">Perfil</h1>
        <p className="text-sm text-ink-muted">
          Tus datos y el acceso a la cuenta. El correo es tu identificador y no se cambia.
        </p>
      </header>

      <ProfileForm
        email={user.email}
        emailVerified={user.email_verified}
        initialFullName={user.full_name}
        initialNit={user.nit ?? ""}
      />

      {!user.email_verified ? (
        <section className="space-y-3" data-testid="account-resend">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
            Verificación
          </p>
          <div className="space-y-3 rounded-md border border-line bg-bone-raised p-5">
            <p className="text-sm text-ink">
              Todavía no verificaste tu correo. Podemos reenviar el enlace.
            </p>
            <FieldError error={resend.error} />
            {resend.isSuccess ? (
              <p className="text-sm text-ink" data-testid="resend-ok">
                Si el correo existe y no está verificado, enviamos un nuevo enlace.
              </p>
            ) : null}
            <button
              type="button"
              data-testid="resend-verification"
              className="h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink"
              disabled={resend.isPending}
              onClick={() => resend.mutate({ email: user.email })}
            >
              {resend.isPending ? "Reenviando…" : "Reenviar verificación"}
            </button>
          </div>
        </section>
      ) : null}

      <PasswordForm />

      <section className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
          Zona de riesgo
        </p>
        <div className="rounded-md border border-line bg-bone-raised p-5">
          <h2 className="font-display text-xl font-semibold text-ink">Eliminar la cuenta</h2>
          <p className="mt-1 text-sm text-ink-muted">
            Se eliminan tus ponds, sus respaldos y tu historial de facturación.
          </p>
          <button
            ref={deleteOpenRef}
            type="button"
            data-testid="delete-me-open"
            className="mt-4 h-9 rounded-sm border border-danger bg-bone-raised px-4 text-sm font-medium text-danger focus-visible:shadow-focus"
            onClick={() => setDeleteOpen(true)}
          >
            Eliminar mi cuenta…
          </button>
        </div>
      </section>

      {deleteOpen ? (
        <DeleteAccountDialog
          email={user.email}
          pondsCount={pondsCount}
          pending={deleteMe.isPending}
          error={deleteMe.error}
          returnFocusRef={deleteOpenRef}
          onCancel={() => {
            setDeleteOpen(false);
            deleteMe.reset();
          }}
          onConfirm={(confirmEmail) => {
            deleteMe.mutate(
              { confirm_email: confirmEmail },
              {
                onSuccess: () => {
                  setDeleteOpen(false);
                  void navigate("/login", { replace: true });
                },
              },
            );
          }}
        />
      ) : null}
    </div>
  );
}
