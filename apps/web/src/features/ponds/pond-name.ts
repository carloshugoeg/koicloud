const NAME_CHAR = /^[a-z0-9-]+$/;

export function pondNameIssues(name: string): string[] {
  const issues: string[] = [];
  if (name.length > 0 && !NAME_CHAR.test(name)) {
    issues.push("Solo minúsculas, números y guiones.");
  }
  if (name.length < 3) issues.push("Mínimo 3 caracteres.");
  if (name.length > 40) issues.push("Máximo 40 caracteres.");
  return issues;
}

export function isPondNameValid(name: string): boolean {
  return pondNameIssues(name).length === 0;
}
