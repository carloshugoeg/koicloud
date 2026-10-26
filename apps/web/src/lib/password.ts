export const MIN_PASSWORD_LENGTH = 10;

export function passwordMinHelp(extra?: string): string {
  const base = `Mínimo ${MIN_PASSWORD_LENGTH} caracteres.`;
  return extra ? `${base} ${extra}` : base;
}

export function isPasswordLongEnough(password: string): boolean {
  return password.length >= MIN_PASSWORD_LENGTH;
}
