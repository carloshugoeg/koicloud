import type { AdminUser } from "@/api/hooks/admin";

type UsersTableProps = {
  users: AdminUser[];
  pondsComplete: boolean;
  pondCountByEmail: Map<string, number>;
  onSuspend: (user: AdminUser, trigger: HTMLButtonElement) => void;
  onReactivate: (user: AdminUser) => void;
};

export function UsersTable({
  users,
  pondsComplete,
  pondCountByEmail,
  onSuspend,
  onReactivate,
}: UsersTableProps) {
  if (users.length === 0) {
    return (
      <div className="rounded-md border border-line bg-bone-raised p-8 text-center" data-testid="admin-users-empty">
        <p className="text-sm text-ink-muted">No hay usuarios con ese filtro.</p>
      </div>
    );
  }

  return (
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
              <td className="px-4 py-3 font-mono text-xs">{user.active_subscription_plan ?? "—"}</td>
              <td className="px-4 py-3 font-mono text-xs" data-testid={`pond-count-${user.id}`}>
                {pondsComplete ? (pondCountByEmail.get(user.email.toLowerCase()) ?? 0) : "—"}
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
