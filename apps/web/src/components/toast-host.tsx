import { useEffect, useState } from "react";
import { subscribeToasts, type ToastItem, type ToastTone } from "@/lib/toast";

const TONE_BORDER: Record<ToastTone, string> = {
  ok: "border-l-green-700",
  warn: "border-l-warn",
  danger: "border-l-danger",
};

export function ToastHost() {
  const [items, setItems] = useState<ToastItem[]>([]);

  useEffect(() => subscribeToasts(setItems), []);

  if (items.length === 0) {
    return null;
  }

  return (
    <div
      className="pointer-events-none fixed inset-x-4 bottom-4 z-50 flex flex-col gap-2 sm:inset-x-auto sm:right-4 sm:w-80"
      aria-live="polite"
    >
      {items.map((item) => (
        <div
          key={item.id}
          role="status"
          data-testid="toast"
          data-tone={item.tone}
          className={`pointer-events-auto rounded-sm border border-line bg-bone-raised px-3 py-2 shadow-print border-l-[3px] ${TONE_BORDER[item.tone]}`}
        >
          <p className="text-sm font-medium text-ink">{item.title}</p>
          {item.detail ? <p className="mt-0.5 text-xs text-ink-muted">{item.detail}</p> : null}
        </div>
      ))}
    </div>
  );
}
