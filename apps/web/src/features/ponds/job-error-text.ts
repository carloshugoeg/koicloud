/** Strip a closed `code: ` prefix so the UI shows only the Spanish sentence. */
export function jobErrorSentence(lastError: string): string {
  const sep = ": ";
  const index = lastError.indexOf(sep);
  if (index === -1) {
    return lastError;
  }
  return lastError.slice(index + sep.length);
}
