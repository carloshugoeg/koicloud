import { useMemo, useRef, useState } from "react";
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
import { UsersTable } from "@/features/admin/users-table";
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
  const suspendTriggerRef = useRef<HTMLElement | null>(null);
  const reactivateTriggerRef = useRef<HTMLElement | null>(null);

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

  function openReactivate(user: AdminUser, trigger: HTMLButtonElement) {
    reactivateTriggerRef.current = trigger;
    setDialog({ kind: "reactivate", user });
  }

  function openSuspend(user: AdminUser, trigger: HTMLButtonElement) {
    suspendTriggerRef.current = trigger;
    setDialog({ kind: "suspend", user });
    setConfirmEmail("");
    setMotivo("");
  }

  function submitSuspend() {
    if (dialog.kind !== "suspend") {
      return;
    }
    const trimmed = motivo.trim();
    suspend.mutate(
      { userId: dialog.user.id, reason: trimmed ? trimmed : undefined },
      { onSuccess: () => closeDialog() },
    );
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

      <UsersTable
        users={users}
        pondsComplete={pondsComplete}
        pondCountByEmail={pondCountByEmail}
        onSuspend={openSuspend}
        onReactivate={openReactivate}
      />

      {usersQuery.data?.next_cursor ? <MoreResultsNote /> : null}

      {dialog.kind === "suspend" ? (
        <SuspendDialog
          user={dialog.user}
          confirmEmail={confirmEmail}
          motivo={motivo}
          pending={suspend.isPending}
          error={suspend.error}
          returnFocusRef={suspendTriggerRef}
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
          returnFocusRef={reactivateTriggerRef}
          onCancel={closeDialog}
          onSubmit={submitReactivate}
        />
      ) : null}
    </div>
  );
}
