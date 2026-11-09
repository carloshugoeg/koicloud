import { useLayoutEffect, useRef } from "react";
import type { AdminUser } from "@/api/hooks/admin";

type UsersTableProps = {
  users: AdminUser[];
  emptyMessage: string;
  pondsComplete: boolean;
  pondCountByEmail: Map<string, number>;
  focusUserId: string | null;
  onSuspend: (user: AdminUser, trigger: HTMLButtonElement) => void;
  onReactivate: (user: AdminUser) => void;
};

const MONTHS_ES = [
  "ene",
  "feb",
  "mar",
  "abr",
  "may",
  "jun",
  "jul",
  "ago",
  "sep",
  "oct",
  "nov",
  "dic",
] as const;

function formatCreatedAt(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Guatemala",
    day: "numeric",
    month: "numeric",
    year: "numeric",
  }).formatToParts(date);
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  const monthIndex = Number(parts.find((part) => part.type === "month")?.value ?? "0") - 1;
  const year = parts.find((part) => part.type === "year")?.value ?? "";
  const month = MONTHS_ES[monthIndex] ?? "—";
  return `${day} ${month} ${year}`;
}

export function UsersTable({
  users,
  emptyMessage,
  pondsComplete,
  pondCountByEmail,
  focusUserId,
  onSuspend,
  onReactivate,
}: UsersTableProps) {
  const focusRef = useRef<HTMLTableRowElement>(null);

  useLayoutEffect(() => {
    focusRef.current?.focus();
  }, [focusUserId]);

  if (users.length === 0) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="admin-users-empty">
        <p className="text-sm text-ink-muted">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-line bg-bone-raised">
      <table className="w-full min-w-[880px] border-collapse text-sm">
        <thead className="bg-bone-sunk text-left text-xs uppercase tracking-[0.12em] text-ink-muted">
          <tr>
            <th className="px-4 py-3 font-medium">Usuario</th>
            <th className="px-4 py-3 font-medium">Plan</th>
            <th className="px-4 py-3 font-medium">Ponds</th>
            <th className="px-4 py-3 font-medium">Verificado</th>
            <th className="px-4 py-3 font-medium">Creado</th>
            <th className="px-4 py-3 font-medium">Estado</th>
            <th className="px-4 py-3 font-medium">Acciones</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr
              key={user.id}
              ref={user.id === focusUserId ? focusRef : undefined}
              tabIndex={user.id === focusUserId ? -1 : undefined}
              className={
                user.id === focusUserId
                  ? "group border-t border-line focus:outline focus:outline-2 focus:-outline-offset-2 focus:outline-turquoise-700"
                  : "border-t border-line"
              }
              data-testid={`admin-user-row-${user.id}`}
            >
              <td
                className={
                  user.id === focusUserId ? "px-4 py-3 group-focus:shadow-focus" : "px-4 py-3"
                }
              >
                <p className="font-medium text-ink">{user.full_name}</p>
                <p className="font-mono text-xs text-ink-muted">{user.email}</p>
              </td>
              <td className="px-4 py-3 font-mono text-xs">{user.active_subscription_plan ?? "—"}</td>
              <td
                className="px-4 py-3 text-right font-mono text-xs tabular-nums"
                data-testid={`pond-count-${user.id}`}
              >
                {pondsComplete ? (pondCountByEmail.get(user.email.toLowerCase()) ?? 0) : "—"}
              </td>
              <td className="px-4 py-3" data-testid={`email-verified-${user.id}`}>
                <span className="text-xs text-ink">
                  {user.email_verified ? "sí · ●" : "no · ○"}
                </span>
              </td>
              <td
                className="px-4 py-3 font-mono text-xs tabular-nums"
                data-testid={`created-at-${user.id}`}
              >
                {formatCreatedAt(user.created_at)}
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
                    className="h-8 rounded-sm border border-danger px-3 text-xs font-medium text-danger focus:shadow-focus"
                    data-testid={`suspend-${user.id}`}
                    onClick={(event) => onSuspend(user, event.currentTarget)}
                  >
                    Suspender
                  </button>
                ) : (
                  <button
                    type="button"
                    className="h-8 rounded-sm border border-line-control px-3 text-xs font-medium"
                    data-testid={`reactivate-${user.id}`}
                    onClick={() => onReactivate(user)}
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
  );
}
