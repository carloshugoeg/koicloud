const NOTICE_MAX = 200;

export type AppNotice = { text: string };

export function readAppNotice(state: unknown): AppNotice | null {
  if (typeof state !== "object" || state === null) {
    return null;
  }
  const notice = (state as { notice?: unknown }).notice;
  if (typeof notice !== "object" || notice === null) {
    return null;
  }
  const text = (notice as { text?: unknown }).text;
  if (typeof text !== "string") {
    return null;
  }
  const trimmed = text.trim();
  if (trimmed.length === 0 || trimmed.length > NOTICE_MAX) {
    return null;
  }
  return { text: trimmed };
}
