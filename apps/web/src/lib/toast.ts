export type ToastTone = "ok" | "warn" | "danger";

export type ToastItem = {
  id: number;
  title: string;
  detail?: string;
  tone: ToastTone;
};

const VISIBLE_MS = 1200;

type Listener = (items: ToastItem[]) => void;

let items: ToastItem[] = [];
let nextId = 1;
const listeners = new Set<Listener>();
const timers = new Map<number, number>();

function emit() {
  const snapshot = items;
  listeners.forEach((listener) => listener(snapshot));
}

export function pushToast(input: { title: string; detail?: string; tone?: ToastTone }) {
  const id = nextId;
  nextId += 1;
  const item: ToastItem = {
    id,
    title: input.title,
    detail: input.detail,
    tone: input.tone ?? "ok",
  };
  items = [...items, item];
  emit();
  const timer = window.setTimeout(() => dismissToast(id), VISIBLE_MS);
  timers.set(id, timer);
  return id;
}

export function dismissToast(id: number) {
  const timer = timers.get(id);
  if (timer !== undefined) {
    window.clearTimeout(timer);
    timers.delete(id);
  }
  if (!items.some((item) => item.id === id)) {
    return;
  }
  items = items.filter((item) => item.id !== id);
  emit();
}

export function subscribeToasts(listener: Listener) {
  listeners.add(listener);
  listener(items);
  return () => {
    listeners.delete(listener);
  };
}

export function resetToasts() {
  for (const timer of timers.values()) {
    window.clearTimeout(timer);
  }
  timers.clear();
  items = [];
  emit();
}
