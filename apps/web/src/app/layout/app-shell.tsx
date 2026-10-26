import { useCallback, useRef, useState } from "react";
import { Outlet, useLocation, useMatches, useNavigate } from "react-router-dom";
import { readAppNotice } from "@/app/layout/app-notice";
import { AppHeader } from "@/app/layout/app-header";
import { SidebarRail, SidebarSheet } from "@/app/layout/sidebar";
import { useSidebarMode } from "@/app/layout/use-sidebar-mode";
import { useAuthStore } from "@/lib/auth-store";

function readTitle(handle: unknown) {
  if (
    typeof handle === "object" &&
    handle !== null &&
    typeof (handle as { title?: unknown }).title === "string"
  ) {
    return (handle as { title: string }).title;
  }

  return "KoiCloud";
}

export function AppShell() {
  const session = useAuthStore((state) => state.session);
  const clearSession = useAuthStore((state) => state.clearSession);
  const matches = useMatches();
  const location = useLocation();
  const navigate = useNavigate();
  const currentTitle = readTitle(matches[matches.length - 1]?.handle);
  const mode = useSidebarMode();
  const [sheetOpen, setSheetOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const openSheet = useCallback(() => setSheetOpen(true), []);
  const isAdmin = session?.user.role === "admin";
  const collapsed = mode === "rail";
  const notice = readAppNotice(location.state);

  return (
    <div className="flex min-h-screen overflow-x-hidden bg-bone text-ink">
      {mode === "sheet" ? null : (
        <SidebarRail isAdmin={Boolean(isAdmin)} collapsed={collapsed} />
      )}
      <SidebarSheet
        isAdmin={Boolean(isAdmin)}
        open={mode === "sheet" && sheetOpen}
        onClose={closeSheet}
        returnFocusRef={menuButtonRef}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader
          title={currentTitle}
          userName={session?.user.full_name ?? "Operador"}
          userEmail={session?.user.email ?? ""}
          onLogout={clearSession}
          onOpenNav={openSheet}
          showMenuButton={mode === "sheet"}
          menuButtonRef={menuButtonRef}
        />

        {session?.user.status === "suspended" ? (
          <p
            role="status"
            data-testid="suspended-banner"
            className="border-b-[3px] border-marigold bg-danger-soft px-4 py-3 text-sm text-ink sm:px-6"
          >
            <span className="font-medium text-danger">Tu cuenta está suspendida.</span> No puedes
            crear ponds ni ejecutar SQL. Tus datos y tus respaldos siguen intactos. Escribe al
            administrador para reactivarla.
          </p>
        ) : null}

        <main className="mx-auto w-full max-w-content flex-1 overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {notice ? (
            <div
              className="mb-4 border-l-[3px] border-green-700 bg-bone-raised px-4 py-3 text-sm text-ink shadow-print"
              role="status"
              data-testid="app-notice"
            >
              <div className="flex items-start justify-between gap-3">
                <p>{notice.text}</p>
                <button
                  type="button"
                  className="text-xs font-medium text-ink-muted"
                  onClick={() => navigate(location.pathname, { replace: true, state: null })}
                >
                  Cerrar
                </button>
              </div>
            </div>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
