from __future__ import annotations

from dataclasses import dataclass
from datetime import date

NIT_ERROR = "El NIT no es válido. Usá los dígitos y el dígito verificador, o CF."
CARD_DECLINED = "El pago simulado fue rechazado. Revisá la tarjeta."


@dataclass(frozen=True, slots=True)
class CardInput:
    number: str
    expiry: str
    cvc: str


def nit_error(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not trimmed or trimmed.upper() == "CF":
        return None
    normalized = trimmed.upper().replace(" ", "").replace("-", "")
    if len(normalized) < 2 or not normalized[:-1].isdigit() or normalized[-1] not in "0123456789K":
        return NIT_ERROR
    if _nit_check_digit(normalized[:-1]) != normalized[-1]:
        return NIT_ERROR
    return None


def card_declined(card: CardInput, today: date | None = None) -> str | None:
    digits = _digits(card.number)
    if not _luhn_ok(digits):
        return CARD_DECLINED
    expiry = card.expiry.strip()
    if len(expiry) != 5 or expiry[2] != "/" or not expiry[:2].isdigit() or not expiry[3:].isdigit():
        return CARD_DECLINED
    month = int(expiry[:2])
    year = 2000 + int(expiry[3:])
    if month < 1 or month > 12:
        return CARD_DECLINED
    current = today or date.today()
    if (year, month) < (current.year, current.month):
        return CARD_DECLINED
    amex = len(digits) == 15 and digits.startswith(("34", "37"))
    expected = 4 if amex else 3
    if not card.cvc.isdigit() or len(card.cvc) != expected:
        return CARD_DECLINED
    return None


def _nit_check_digit(body: str) -> str:
    total = 0
    factor = len(body) + 1
    for char in body:
        total += int(char) * factor
        factor -= 1
    result = 11 - (total % 11)
    if result == 11:
        return "0"
    if result == 10:
        return "K"
    return str(result)


def _digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def _luhn_ok(digits: str) -> bool:
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    alternate = False
    for char in reversed(digits):
        digit = int(char)
        if alternate:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        alternate = not alternate
    return total % 10 == 0
