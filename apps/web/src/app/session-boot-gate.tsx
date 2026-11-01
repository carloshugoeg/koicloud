import { type PropsWithChildren, useEffect, useState } from "react";
import { restoreSession } from "@/api/client";
import { retryLogoutQuietly } from "@/api/hooks/auth";
import { DataStateSessionBoot } from "@/components/data-state";
import { useAuthStore } from "@/lib/auth-store";
import { isLoggedOut } from "@/lib/logged-out";

const isVitest = import.meta.env.MODE === "test";

export interface SessionBootGateProps extends PropsWithChildren {
  /**
   * When true, skip the boot frame (default in Vitest so existing screens
   * do not need findBy waits). Pass false to assert the boot UI.
   */
  skipBoot?: boolean;
}

/**
 * Arranque de sesión (§6.5 / CA3): quiet pond, then children.
 * Children stay unmounted until refresh settles so the router cannot
 * send the user to login before the cookie session is restored.
 */
export function SessionBootGate({
  children,
  skipBoot = isVitest,
}: SessionBootGateProps) {
  const [ready, setReady] = useState(skipBoot);

  useEffect(() => {
    if (skipBoot) {
      return;
    }

    let cancelled = false;
    const frame = window.requestAnimationFrame(() => {
      void (async () => {
        if (!useAuthStore.getState().session) {
          if (isLoggedOut()) {
            void retryLogoutQuietly();
          } else {
            const restored = await restoreSession();
            if (cancelled) {
              return;
            }
            if (restored) {
              useAuthStore.getState().setSession(restored);
            } else {
              useAuthStore.getState().clearSession();
            }
          }
        }
        if (!cancelled) {
          setReady(true);
        }
      })();
    });
    return () => {
      cancelled = true;
      window.cancelAnimationFrame(frame);
    };
  }, [skipBoot]);

  if (!ready) {
    return <DataStateSessionBoot />;
  }

  return children;
}
