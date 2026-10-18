import { useMemo, useState } from "react";
import {
  useAdminPondsQuery,
  useAdminUsersQuery,
  useReactivateUserMutation,
  useSuspendUserMutation,
  type AdminUser,
} from "@/api/hooks/admin";
import { isCompleteCursorPage } from "@/features/admin/cursor-page";
import { MoreResultsNote } from "@/features/admin/more-results-note";
import { ReactivateDialog } from "@/features/admin/reactivate-dialog";
import { SuspendDialog } from "@/features/admin/suspend-dialog";
import { ApiError, problemToMessage } from "@/lib/errors";

type StatusFilter = "all" | "active" | "suspended";
type DialogState =
  | { kind: "closed" }
  | { kind: "suspend"; user: AdminUser }
  | { kind: "reactivate"; user: AdminUser };

export function AdminUsersPage() {
  const usersQuery = useAdminUsersQuery();
  const pondsQuery = useAdminPondsQuery();
  const suspend = useSuspendUserMutation();
  const reactivate = useReactivateUserMutation();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [dialog, setDialog] = useState<DialogState>({ kind: "closed" });
  const [confirmEmail, setConfirmEmail] = useState("");
  const [motivo, setMotivo] = useState("");

  const pondsComplete =
    pondsQuery.isSuccess && isCompleteCursorPage(pondsQuery.data.next_cursor);

  const pondCountByEmail = useMemo(() => {
    const counts = new Map<string, number>();
    if (!pondsComplete || !pondsQuery.data) {
      return counts;
    }
    for (const pond of pondsQuery.data.ponds) {
      const key = pond.owner_email.toLowerCase();
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
    return counts;
  }, [pondsComplete, pondsQuery.data]);

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

  function submitSuspend() {
    if (dialog.kind !== "suspend") {
      return;
    }
    suspend.mutate(dialog.user.id, { onSuccess: () => closeDialog() });
  }

  function submitReactivate() {
    if (dialog.kind !== "reactivate") {
      return;
    }
    reactivate.mutate(dialog.user.id, { onSuccess: () => closeDialog() });
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

  const usersHaveMore = Boolean(usersQuery.data?.next_cursor);

  return (
    <div className="space-y-4" data-testid="admin-users-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-sm text-ink-muted" data-testid="admin-users-summary">
          {users.length} cuentas visibles · suspender no detiene ponds ni borra datos.
        </p>
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
                  <td className="px-4 py-3 font-mono text-xs">
                    {user.active_subscription_plan ?? "—"}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs" data-testid={`pond-count-${user.id}`}>
                    {pondsComplete
                      ? (pondCountByEmail.get(user.email.toLowerCase()) ?? 0)
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        user.status === "suspended"
                          ? "rounded-sm bg-danger-soft px-2 py-1 text-xs text-danger"
                          : "rounded-sm bg-green-100 px-2 py-1 text-xs text-ink"
                      }
                    >
                      {user.status === "suspended" ? "suspendido" : "activo"}
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

      {usersHaveMore ? <MoreResultsNote /> : null}

      {dialog.kind === "suspend" ? (
        <SuspendDialog
          user={dialog.user}
          confirmEmail={confirmEmail}
          motivo={motivo}
          pending={suspend.isPending}
          error={suspend.error}
          onConfirmEmailChange={setConfirmEmail}
          onMotivoChange={setMotivo}
          onCancel={closeDialog}
          onSubmit={submitSuspend}
        />
      ) : null}

      {dialog.kind === "reactivate" ? (
        <ReactivateDialog
          user={dialog.user}
          pending={reactivate.isPending}
          error={reactivate.error}
          onCancel={closeDialog}
          onSubmit={submitReactivate}
        />
      ) : null}
    </div>
  );
}
