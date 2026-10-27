const JWT = /eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}/g;
const BEARER = /\b(bearer|basic)\s+\S+/gi;
const CONF = /\bconf_[A-Za-z0-9_-]{4,}\b/g;

export function redact(text: string, secrets: string[]): string {
  let cleaned = text;
  const unique = [...new Set(secrets.filter((secret) => secret.length >= 4))].sort(
    (a, b) => b.length - a.length,
  );
  for (const secret of unique) {
    cleaned = cleaned.split(secret).join("[redacted]");
  }
  return cleaned.replace(JWT, "[redacted]").replace(BEARER, "[redacted]").replace(CONF, "[redacted]");
}

export function errorNote(error: unknown, secrets: string[]): string {
  const message = error instanceof Error ? error.message : String(error);
  const plain = message.replace(/\u001b\[[0-9;]*m/g, "").replace(/\s+/g, " ").trim();
  return redact(plain, secrets).slice(0, 240);
}
