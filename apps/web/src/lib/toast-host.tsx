import { useEffect, useState } from "react";
import { subscribeToasts, type ToastItem } from "@/lib/toast";

const TOAST_MS = 1200;

const BORDER: Record<ToastItem["tone"], string> = {
  ok: "border-ok",
  warn: "border-warn",
  danger: "border-danger",
};

function motionReduced(): boolean {
  const media = window.matchMedia?.("(prefers-reduced-motion: reduce)");
  return media?.matches ?? false;
}

export function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => {
    const timers = new Set<number>();
    const unsubscribe = subscribeToasts((item) => {
      setItems((current) => [...current, item]);
      const timer = window.setTimeout(() => {
        timers.delete(timer);
        setItems((current) => current.filter((row) => row.id !== item.id));
      }, TOAST_MS);
      timers.add(timer);
    });
    return () => {
      unsubscribe();
      for (const timer of timers) window.clearTimeout(timer);
    };
  }, []);

  const calm = motionReduced();

  // Always mount the live region so AT can discover it before the first toast.
  return (
    <div
      aria-live="polite"
      aria-relevant="additions text"
      data-testid="toast-host"
      className="pointer-events-none fixed bottom-4 left-4 right-4 z-50 flex flex-col gap-2 sm:left-auto sm:w-80"
    >
      {items.map((item) => (
        <div
          key={item.id}
          role={item.tone === "danger" ? "alert" : "status"}
          data-testid="toast"
          data-tone={item.tone}
          className={[
            "rounded-sm border-l-[3px] bg-bone-raised px-3 py-2 text-sm text-ink shadow-print",
            BORDER[item.tone],
            calm ? "" : "transition-opacity duration-instant",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {item.message}
        </div>
      ))}
    </div>
  );
}
