export const NIT_ERROR = "El NIT no es válido. Usá los dígitos y el dígito verificador, o CF.";
export const CARD_ERROR = "El número de tarjeta no es válido.";
export const EXPIRY_ERROR = "La expiración debe ser MM/AA y no estar vencida.";
export const CVV_ERROR = "El CVV debe tener 3 dígitos, o 4 si es American Express.";

export function nitError(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed || trimmed.toUpperCase() === "CF") {
    return null;
  }
  const normalized = trimmed.toUpperCase().replace(/[\s-]/g, "");
  if (!/^\d+[0-9K]$/.test(normalized)) {
    return NIT_ERROR;
  }
  const body = normalized.slice(0, -1);
  if (nitCheckDigit(body) !== normalized.slice(-1)) {
    return NIT_ERROR;
  }
  return null;
}

export function cardNumberError(value: string): string | null {
  return luhnOk(digitsOf(value)) ? null : CARD_ERROR;
}

export function expiryError(value: string, today = new Date()): string | null {
  const text = value.trim();
  const match = /^(\d{2})\/(\d{2})$/.exec(text);
  if (!match) {
    return EXPIRY_ERROR;
  }
  const month = Number(match[1]);
  const year = 2000 + Number(match[2]);
  if (month < 1 || month > 12) {
    return EXPIRY_ERROR;
  }
  const current = today.getFullYear() * 12 + today.getMonth();
  if (year * 12 + (month - 1) < current) {
    return EXPIRY_ERROR;
  }
  return null;
}

export function cvvError(number: string, cvc: string): string | null {
  const digits = digitsOf(number);
  const amex = digits.length === 15 && (digits.startsWith("34") || digits.startsWith("37"));
  const expected = amex ? 4 : 3;
  return new RegExp(`^\\d{${expected}}$`).test(cvc.trim()) ? null : CVV_ERROR;
}

export function cardDigits(value: string): string {
  return digitsOf(value);
}

function digitsOf(value: string): string {
  return value.replace(/\D/g, "");
}

function nitCheckDigit(body: string): string {
  let total = 0;
  let factor = body.length + 1;
  for (const char of body) {
    total += Number(char) * factor;
    factor -= 1;
  }
  const result = 11 - (total % 11);
  if (result === 11) return "0";
  if (result === 10) return "K";
  return String(result);
}

function luhnOk(digits: string): boolean {
  if (digits.length < 13 || digits.length > 19) {
    return false;
  }
  let total = 0;
  let alternate = false;
  for (let index = digits.length - 1; index >= 0; index -= 1) {
    let digit = Number(digits[index]);
    if (alternate) {
      digit *= 2;
      if (digit > 9) digit -= 9;
    }
    total += digit;
    alternate = !alternate;
  }
  return total % 10 === 0;
}
