import { useState } from "react";
import type { AdminUser } from "@/api/hooks/admin";

type PageIntent = { kind: "load" | "retry"; baseline: number };

type NextPageFocusInput = {
  users: AdminUser[];
  nextCursor: string | null;
  fetchingNextPage: boolean;
  fetchNextPage: () => Promise<unknown>;
};

export function useNextPageFocus({
  users,
  nextCursor,
  fetchingNextPage,
  fetchNextPage,
}: NextPageFocusInput) {
  const [intent, setIntent] = useState<PageIntent | null>(null);

  function loadMore() {
    setIntent({ kind: "load", baseline: users.length });
    void fetchNextPage();
  }

  function retry() {
    if (fetchingNextPage) {
      return;
    }
    setIntent({ kind: "retry", baseline: users.length });
    void fetchNextPage();
  }

  const landed = intent != null && !fetchingNextPage && users.length > intent.baseline;
  const moveFocus = landed && (intent.kind === "retry" || nextCursor == null);
  const focusUserId = moveFocus ? (users[intent.baseline]?.id ?? null) : null;

  return {
    focusUserId,
    holdRetryAlert: intent?.kind === "retry" && fetchingNextPage,
    loadMore,
    retry,
  };
}
