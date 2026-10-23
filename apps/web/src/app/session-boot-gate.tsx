import { type PropsWithChildren, useEffect, useState } from "react";
import { DataStateSessionBoot } from "@/components/data-state";
import {
  restoreSessionFromStorage,
  subscribeSessionPersistence,
} from "@/lib/session-boot";

const isTest = import.meta.env.MODE === "test";

/**
 * Shows the quiet-pond DataState while restoring session (arranque §6.5 / CA3).
 * Does not modify auth-store.ts — persistence lives in lib/session-boot.ts.
 *
 * In Vitest the boot frame is skipped so existing screens don't need findBy waits.
 */
export function SessionBootGate({ children }: PropsWithChildren) {
  const [ready, setReady] = useState(isTest);

  useEffect(() => {
    restoreSessionFromStorage();
    const unsubscribe = subscribeSessionPersistence();

    if (isTest) {
      return unsubscribe;
    }

    const frame = window.requestAnimationFrame(() => {
      setReady(true);
    });
    return () => {
      window.cancelAnimationFrame(frame);
      unsubscribe();
    };
  }, []);

  if (!ready) {
    return <DataStateSessionBoot />;
  }

  return children;
}
