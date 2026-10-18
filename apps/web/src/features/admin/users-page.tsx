import { useMemo, useState } from "react";
import {
  SUSPEND_CONFIRM_TEXT,
  useAdminUsersQuery,
  useReactivateUserMutation,
  useSuspendUserMutation,
  type AdminUser,
} from "@/api/hooks/admin";
import { ApiError, problemToMessage } from "@/lib/errors";

type StatusFilter = "all" | "active" | "suspended";
type DialogState =
  | { kind: "closed" }
  | { kind: "suspend"; user: AdminUser }
  | { kind: "reactivate"; user: AdminUser };

function planLabel(user: AdminUser) {
  return user.active_subscription_plan ?? "—";
}

function statusLabel(status: AdminUser["status"]) {
  return status === "suspended" ? "suspendido" : "activo";
}

export function AdminUsersPage() {
  const usersQuery = useAdminUsersQuery();
  const suspend = useSuspendUserMutation();
  const reactivate = useReactivateUserMutation();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [dialog, setDialog] = useState<DialogState>({ kind: "closed" });
  const [confirmEmail, setConfirmEmail] = useState("");
  const [motivo, setMotivo] = useState("");

  const users = useMemo(() => {
    const rows = usersQuery.data?.users ?? [];
    const needle = query.trim().toLowerCase();
    return rows.filter((user) => {
      if (statusFilter !== "all" && user.status !== statusFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        user.email.toLowerCase().includes(needle) ||
        user.full_name.toLowerCase().includes(needle)
      );
    });
  }, [usersQuery.data?.users, query, statusFilter]);

  function closeDialog() {
    setDialog({ kind: "closed" });
    setConfirmEmail("");
    setMotivo("");
    suspend.reset();
    reactivate.reset();
  }

  async function submitSuspend() {
    if (dialog.kind !== "suspend") {
      return;
    }
    await suspend.mutateAsync(dialog.user.id);
    closeDialog();
  }

  async function submitReactivate() {
    if (dialog.kind !== "reactivate") {
      return;
    }
    await reactivate.mutateAsync(dialog.user.id);
    closeDialog();
  }

  if (usersQuery.isPending) {
    return (
      <div className="space-y-4" data-testid="admin-users-loading">
        <div className="h-10 w-56 animate-pulse rounded-sm bg-bone-sunk" />
        <div className="h-64 animate-pulse rounded-md border border-line bg-bone-sunk" />
      </div>
    );
  }

  if (usersQuery.isError) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="admin-users-error">
        <div className="border-l-[3px] border-danger pl-3">
          <p className="text-sm text-ink">{problemToMessage(usersQuery.error)}</p>
          <p className="mt-1 font-mono text-xs text-ink-faint">
            {usersQuery.error instanceof ApiError ? usersQuery.error.problem?.code : "error"}
          </p>
        </div>
        <button
          type="button"
          className="mt-4 h-9 rounded-sm border border-line-control bg-bone-raised px-4 text-sm font-medium"
          onClick={() => void usersQuery.refetch()}
        >
          Reintentar
        </button>
      </div>
    );
  }

  const actionError = suspend.error ?? reactivate.error;
  const emailMatches =
    dialog.kind === "suspend" && confirmEmail.trim().toLowerCase() === dialog.user.email.toLowerCase();

  return (
    <div className="space-y-4" data-testid="admin-users-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-ink-muted" data-testid="admin-users-summary">
            {users.length} cuentas visibles · suspender no detiene ponds ni borra datos.
          </p>
        </div>
        <div className="flex flex-wrap gap-2" data-testid="admin-users-filters">
          <label className="text-xs text-ink-muted">
            Buscar
            <input
              className="mt-1 block h-9 w-52 rounded-sm border border-line-control bg-bone-raised px-3 text-sm"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="correo o nombre"
            />
          </label>
          <label className="text-xs text-ink-muted">
            Estado
            <select
              className="mt-1 block h-9 rounded-sm border border-line-control bg-bone-raised px-3 text-sm"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              <option value="all">Todos</option>
              <option value="active">Activos</option>
              <option value="suspended">Suspendidos</option>
            </select>
          </label>
        </div>
      </div>

      {users.length === 0 ? (
        <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="admin-users-empty">
          <p className="text-sm text-ink-muted">No hay usuarios con ese filtro.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-md border border-line bg-bone-raised">
          <table className="w-full min-w-[720px] border-collapse text-sm">
            <thead className="bg-bone-sunk text-left text-xs uppercase tracking-[0.12em] text-ink-muted">
              <tr>
                <th className="px-4 py-3 font-medium">Usuario</th>
                <th className="px-4 py-3 font-medium">Plan</th>
                <th className="px-4 py-3 font-medium">Ponds</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-t border-line" data-testid={`admin-user-row-${user.id}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-ink">{user.full_name}</p>
                    <p className="font-mono text-xs text-ink-muted">{user.email}</p>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs">{planLabel(user)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ink-muted" title="pond_count no está en el contrato congelado">
                    —
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        user.status === "suspended"
                          ? "rounded-sm bg-danger-soft px-2 py-1 text-xs text-danger"
                          : "rounded-sm bg-green-100 px-2 py-1 text-xs text-ink"
                      }
                    >
                      {statusLabel(user.status)}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    {user.status === "active" ? (
                      <button
                        type="button"
                        className="h-8 rounded-sm border border-danger px-3 text-xs font-medium text-danger"
                        data-testid={`suspend-${user.id}`}
                        onClick={() => {
                          setDialog({ kind: "suspend", user });
                          setConfirmEmail("");
                          setMotivo("");
                        }}
                      >
                        Suspender
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="h-8 rounded-sm border border-line-control px-3 text-xs font-medium"
                        data-testid={`reactivate-${user.id}`}
                        onClick={() => setDialog({ kind: "reactivate", user })}
                      >
                        Reactivar
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialog.kind === "suspend" ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4" data-testid="suspend-dialog">
          <div className="w-full max-w-md rounded-md border border-line bg-bone-raised shadow-lg">
            <div className="h-1 bg-danger" />
            <div className="space-y-4 p-5">
              <h3 className="font-display text-2xl text-ink">Suspender a {dialog.user.full_name}</h3>
              <div className="rounded-sm border border-danger/40 bg-danger-soft px-3 py-2 text-sm text-ink">
                La cuenta no podrá iniciar sesión. Sus ponds siguen corriendo y no se borra ningún dato.
              </div>
              <label className="block text-xs text-ink-muted">
                Escribe el correo de la cuenta para confirmar
                <input
                  className="mt-1 block h-10 w-full rounded-sm border border-line-control bg-bone px-3 font-mono text-sm"
                  value={confirmEmail}
                  onChange={(event) => setConfirmEmail(event.target.value)}
                  data-testid="suspend-confirm-email"
                />
                <span className="mt-1 block font-mono text-[11px]">Esperado: {dialog.user.email}</span>
              </label>
              <label className="block text-xs text-ink-muted">
                Motivo <span className="text-ink-faint">(queda en la bitácora)</span>
                <input
                  className="mt-1 block h-10 w-full rounded-sm border border-line-control bg-bone px-3 text-sm"
                  value={motivo}
                  onChange={(event) => setMotivo(event.target.value)}
                  data-testid="suspend-motivo"
                />
              </label>
              <p className="font-mono text-[11px] text-ink-faint">
                API: confirm_text = {SUSPEND_CONFIRM_TEXT}
              </p>
              {actionError ? (
                <p className="text-sm text-danger" data-testid="suspend-error">
                  {problemToMessage(actionError)}
                </p>
              ) : null}
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
              <button type="button" className="h-9 px-3 text-sm" onClick={closeDialog}>
                Cancelar
              </button>
              <button
                type="button"
                className="h-9 rounded-sm bg-danger px-4 text-sm font-medium text-bone disabled:opacity-40"
                data-testid="suspend-submit"
                disabled={!emailMatches || !motivo.trim() || suspend.isPending}
                onClick={() => void submitSuspend()}
              >
                Suspender cuenta
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {dialog.kind === "reactivate" ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/40 p-4" data-testid="reactivate-dialog">
          <div className="w-full max-w-md rounded-md border border-line bg-bone-raised">
            <div className="space-y-4 p-5">
              <h3 className="font-display text-2xl text-ink">Reactivar a {dialog.user.full_name}</h3>
              <p className="text-sm text-ink-muted">
                La cuenta podrá iniciar sesión de nuevo. Confirmá para continuar.
              </p>
              {actionError ? (
                <p className="text-sm text-danger">{problemToMessage(actionError)}</p>
              ) : null}
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-line px-5 py-3">
              <button type="button" className="h-9 px-3 text-sm" onClick={closeDialog}>
                Cancelar
              </button>
              <button
                type="button"
                className="h-9 rounded-sm border border-turquoise-700 bg-turquoise-100 px-4 text-sm font-medium text-turquoise-900 disabled:opacity-40"
                data-testid="reactivate-submit"
                disabled={reactivate.isPending}
                onClick={() => void submitReactivate()}
              >
                Reactivar cuenta
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
