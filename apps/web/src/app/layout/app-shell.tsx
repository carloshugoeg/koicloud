import { useCallback, useRef, useState } from "react";
import { Outlet, useMatches } from "react-router-dom";
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
  const currentTitle = readTitle(matches[matches.length - 1]?.handle);
  const mode = useSidebarMode();
  const [sheetOpen, setSheetOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const closeSheet = useCallback(() => setSheetOpen(false), []);
  const openSheet = useCallback(() => setSheetOpen(true), []);
  const isAdmin = session?.user.role === "admin";
  const collapsed = mode === "rail";

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
          <Outlet />
        </main>
      </div>
    </div>
  );
}
