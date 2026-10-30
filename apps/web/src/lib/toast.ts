type ToastTone = "ok" | "warn" | "danger";

export type ToastItem = {
  id: number;
  tone: ToastTone;
  message: string;
};

const listeners = new Set<(item: ToastItem) => void>();
let nextId = 0;

export function toast(input: { tone: ToastTone; message: string }) {
  nextId += 1;
  const item: ToastItem = { id: nextId, tone: input.tone, message: input.message };
  for (const listener of listeners) listener(item);
}

export function subscribeToasts(listener: (item: ToastItem) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
