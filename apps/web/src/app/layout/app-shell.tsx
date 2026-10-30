import { useCallback, useRef, useState } from "react";
import { Outlet, useLocation, useMatches } from "react-router-dom";
import { AppHeader } from "@/app/layout/app-header";
import { readAppNotice } from "@/app/layout/app-notice";
import { SidebarRail, SidebarSheet } from "@/app/layout/sidebar";
import { useSidebarMode } from "@/app/layout/use-sidebar-mode";
import { revokeSession } from "@/api/hooks/auth";
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
  const logout = useCallback(() => {
    void revokeSession();
  }, []);
  const location = useLocation();
  const matches = useMatches();
  const notice = readAppNotice(location.state);
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
          onLogout={logout}
          onOpenNav={openSheet}
          showMenuButton={mode === "sheet"}
          menuButtonRef={menuButtonRef}
        />

        <main className="mx-auto w-full max-w-content flex-1 overflow-x-hidden px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          {notice ? (
            <p
              className="mb-4 rounded-md border border-line bg-bone-raised px-4 py-3 text-sm text-ink"
              data-testid="app-notice"
              role="status"
            >
              {notice.text}
            </p>
          ) : null}
          <Outlet />
        </main>
      </div>
    </div>
  );
}
