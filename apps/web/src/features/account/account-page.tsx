import { useMeQuery } from "@/api/hooks/me";
import { FieldError } from "@/features/account/field-error";
import { PasswordForm } from "@/features/account/password-form";
import { ProfileForm } from "@/features/account/profile-form";
import { clearIntroTourDone } from "@/features/onboarding/intro-tour-storage";
import { requestIntroTourReplay } from "@/features/onboarding/intro-tour-controller";
import { useAuthStore } from "@/lib/auth-store";

export function AccountPage() {
  const meQuery = useMeQuery();
  const sessionUserId = useAuthStore((state) => state.session?.user.id);

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

  function replayTour() {
    const id = sessionUserId ?? user.id;
    clearIntroTourDone(id);
    requestIntroTourReplay();
  }

  return (
    <div className="mx-auto w-full max-w-[560px] space-y-8" data-testid="account-page">
      <header className="space-y-1 border-b border-line pb-4">
        <h1 className="font-display text-3xl font-semibold text-ink">Cuenta</h1>
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

      <PasswordForm />

      <section className="space-y-3">
        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-ink-muted">
          Ayuda
        </p>
        <div className="rounded-md border border-line bg-bone-raised p-5">
          <p className="text-sm text-ink-muted">
            Si querés repasar dónde están ponds, planes y cuenta, volvé a abrir el recorrido.
          </p>
          <button
            type="button"
            data-testid="replay-intro-tour"
            className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink"
            onClick={replayTour}
          >
            Volver a ver el recorrido
          </button>
        </div>
      </section>
    </div>
  );
}
