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
  if (!trimmed || trimmed.length > 200) {
    return null;
  }
  return { text: trimmed };
}
