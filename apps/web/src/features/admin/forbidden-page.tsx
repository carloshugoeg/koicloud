import { problemToMessage } from "@/lib/errors";

export function AdminForbiddenPage() {
  return (
    <div className="rounded-md border border-line bg-bone-raised p-5" data-testid="admin-forbidden">
      <div className="border-l-[3px] border-danger pl-3">
        <p className="text-sm text-ink">{problemToMessage({ code: "admin_only", message: "admin_only" })}</p>
        <p className="mt-1 font-mono text-xs text-ink-faint">admin_only</p>
      </div>
    </div>
  );
}
