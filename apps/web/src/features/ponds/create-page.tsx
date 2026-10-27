import { type FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCreatePondMutation, useMeQuery, usePlansQuery } from "@/api/hooks";
import { ApiError, problemToMessage } from "@/lib/errors";
import { DashboardPage } from "@/features/ponds/dashboard-page";
import { isPondNameValid, pondNameIssues } from "@/features/ponds/pond-name";

export function CreatePondPage() {
  return (
    <>
      {/*
        Dashboard stays at full ink contrast (no opacity fade — that alone
        caused 30+ axe color-contrast hits). Dim only via the veil layer.
        Dialog is a sibling above the veil so its opaque bone surface is not
        composited through the scrim.
      */}
      <div className="pointer-events-none select-none" aria-hidden>
        <DashboardPage />
      </div>
      <div
        className="dialog-veil create-pond-veil fixed inset-0 z-20"
        data-testid="create-pond-veil"
        aria-hidden
      />
      <div className="fixed inset-0 z-30 flex items-start justify-center overflow-y-auto px-4 py-10">
        <CreatePondDialog />
      </div>
    </>
  );
}

function CreatePondDialog() {
  const navigate = useNavigate();
  const meQuery = useMeQuery();
  const plansQuery = usePlansQuery();
  const createMutation = useCreatePondMutation();
  const [name, setName] = useState("");

  const planId = meQuery.data?.subscription?.plan_id;
  const inheritedPlan = planId
    ? plansQuery.data?.find((plan) => plan.id === planId)
    : undefined;
  const planLoading = meQuery.isPending || plansQuery.isPending;
  const issues = pondNameIssues(name);
  const valid = isPondNameValid(name);
  const errorCode =
    createMutation.error instanceof ApiError ? createMutation.error.problem?.code : undefined;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!valid || createMutation.isPending) return;
    try {
      const { pond } = await createMutation.mutateAsync(name);
      navigate(`/app/ponds/${pond.id}`, { replace: true });
    } catch {
      return;
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="create-pond-dialog w-full max-w-[560px] overflow-hidden rounded-md border border-line bg-bone-raised shadow-dialog"
      data-testid="create-pond-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-pond-title"
    >
      <div className="create-pond-dialog__accent h-1 bg-turquoise-700" />
      <div className="space-y-4 p-5">
        <div>
          <h2 id="create-pond-title" className="font-display text-2xl text-ink">
            Nuevo pond
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Levantamos un contenedor PostgreSQL 16 real en el nodo. Tarda unos 40 segundos.
          </p>
        </div>

        {createMutation.isError ? (
          <div className="border-l-[3px] border-danger pl-3" data-testid="create-pond-error">
            <p className="text-sm text-ink">{problemToMessage(createMutation.error)}</p>
            {errorCode ? <p className="mt-1 font-mono text-xs text-ink-muted">{errorCode}</p> : null}
            {errorCode === "plan_required" ? (
              <Link
                to="/app/plans"
                className="mt-2 inline-block text-sm font-medium text-turquoise-700"
              >
                Ver planes
              </Link>
            ) : null}
          </div>
        ) : null}

        <label className="block space-y-1">
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">Nombre</span>
          <div className="flex items-center gap-2 rounded-sm border border-line-control bg-bone px-3 py-2 focus-within:border-turquoise-700">
            <input
              data-testid="create-pond-name"
              name="name"
              value={name}
              autoComplete="off"
              spellCheck={false}
              onChange={(event) => setName(event.target.value)}
              className="min-w-0 flex-1 bg-transparent font-mono text-sm text-ink outline-none placeholder:text-ink-muted"
              placeholder="inventario-mvp"
              aria-invalid={issues.length > 0 && name.length > 0}
            />
            {valid ? (
              <span className="rounded-sm bg-green-100 px-2 py-0.5 text-xs font-medium text-ink">
                ● nombre válido
              </span>
            ) : null}
          </div>
          <p className="text-xs text-ink-muted">
            Minúsculas, números y guiones; 3 a 40 caracteres.
            {name ? (
              <>
                {" "}
                Quedará como <span className="font-mono text-ink" data-testid="create-pond-echo">{name}</span>.
              </>
            ) : null}
          </p>
          {issues.length > 0 && name.length > 0 ? (
            <ul className="text-xs text-danger" data-testid="create-pond-issues">
              {issues.map((issue) => (
                <li key={issue}>{issue}</li>
              ))}
            </ul>
          ) : null}
        </label>

        <label className="block space-y-1">
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">
            Motor y versión
          </span>
          <div className="rounded-sm border border-line-control bg-bone-sunk px-3 py-2 text-sm text-ink">
            PostgreSQL 16
          </div>
          <p className="text-xs text-ink-muted">Única versión del alcance comprometido.</p>
        </label>

        <label className="block space-y-1">
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-ink-muted">Plan</span>
          <div
            className="rounded-sm border border-line-control bg-bone-sunk px-3 py-2 text-sm text-ink-muted"
            data-testid="create-pond-plan"
          >
            {planLoading
              ? "…"
              : inheritedPlan
                ? `${inheritedPlan.name} · heredado de tu suscripción`
                : "Heredado de tu suscripción"}
          </div>
          <p className="text-xs text-ink-muted">
            Define el límite de ponds y de almacenamiento. Para cambiarlo, cambia de plan.
          </p>
        </label>

        <p className="text-sm text-ink-muted">
          Al crear, te llevamos al detalle del pond. Verás el estado <b>Aprovisionando…</b> hasta que el
          nodo confirme.
        </p>
      </div>
      <div className="flex items-center gap-3 border-t border-line px-5 py-3">
        <Link
          to="/app/ponds"
          className="inline-flex h-9 items-center rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium text-ink"
        >
          Cancelar
        </Link>
        <span className="grow" />
        <button
          type="submit"
          data-testid="create-pond-submit"
          disabled={!valid || createMutation.isPending}
          className="h-9 rounded-sm bg-turquoise-700 px-4 text-sm font-medium text-bone-raised hover:bg-turquoise-900 disabled:bg-bone-sunk disabled:text-ink-muted"
        >
          {createMutation.isPending ? "Creando…" : "Crear pond"}
        </button>
      </div>
    </form>
  );
}
