export function isCompleteCursorPage(nextCursor: string | null | undefined) {
  return nextCursor == null;
}
