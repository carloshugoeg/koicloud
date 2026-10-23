import { type PropsWithChildren, useEffect, useState } from "react";
import { DataStateSessionBoot } from "@/components/data-state";

const isVitest = import.meta.env.MODE === "test";

export interface SessionBootGateProps extends PropsWithChildren {
  /**
   * When true, skip the boot frame (default in Vitest so existing screens
   * do not need findBy waits). Pass false to assert the boot UI.
   */
  skipBoot?: boolean;
}

/**
 * Arranque de sesión (§6.5 / CA3): one quiet-pond DataState frame, then children.
 * No token persistence — auth stays in-memory (auth-store.ts is No tocar).
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

    const frame = window.requestAnimationFrame(() => {
      setReady(true);
    });
    return () => {
      window.cancelAnimationFrame(frame);
    };
  }, [skipBoot]);

  if (!ready) {
    return <DataStateSessionBoot />;
  }

  return children;
}
