"""IBAN validation logic — mod-97 algorithm, country-specific lengths.

No external dependency required.  Pure Python so it works in any
environment (FastAPI, workers, CLI, etc.).
"""

from __future__ import annotations

import re

# Country codes with their IBAN lengths (total characters including BBAN).
# Source: SWIFT IBAN registry (https://www.swift.com/standards/data-standards/iban).
# Only the most commonly used countries for Spain/EU are included.
# Unknown countries still pass the generic format check (2L + 2D + up to 30 alnum).

IBAN_COUNTRY_LENGTHS: dict[str, int] = {
    "AL": 28, "AD": 24, "AT": 20, "AZ": 28, "BH": 22, "BY": 28,
    "BE": 16, "BG": 22, "HR": 21, "CY": 28, "CZ": 24, "DK": 18,
    "EE": 20, "EG": 29, "FO": 18, "FI": 18, "FR": 27, "GE": 22,
    "DE": 22, "GI": 23, "GR": 27, "GL": 18, "GT": 28, "HU": 28,
    "IS": 26, "IQ": 23, "IE": 22, "IL": 23, "IT": 27, "JO": 30,
    "KZ": 20, "XK": 20, "KW": 30, "LV": 21, "LB": 28, "LI": 21,
    "LT": 20, "LU": 20, "MK": 19, "MT": 31, "MR": 27, "MU": 30,
    "MC": 27, "MD": 24, "ME": 22, "NL": 18, "NO": 15, "PK": 24,
    "PS": 29, "PL": 28, "PT": 25, "QA": 29, "RO": 24, "LC": 32,
    "SM": 27, "ST": 25, "SA": 24, "RS": 22, "SC": 31, "SK": 24,
    "SI": 19, "ES": 24, "SD": 18, "SR": 23, "SE": 24, "CH": 21,
    "TL": 23, "TN": 24, "TR": 26,     "UA": 29, "AE": 23, "GB": 22,
    "VG": 24,
}

# Regex: 2 uppercase letters + 2 digits + up to 30 alphanumeric chars
_IBAN_RE = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{1,30}$")


def _country_code(iban: str) -> str:
    """Extract country code from an IBAN."""
    return iban[:2]


def _check_digit(iban: str) -> int:
    """Extract the two-digit check number from an IBAN."""
    return int(iban[2:4])


def _rearrange(iban: str) -> str:
    """Rearrange IBAN: move first 4 chars to end."""
    return iban[4:] + iban[:4]


def _to_integers(iban: str) -> str:
    """Replace letters with numbers (A=10, B=11, ..., Z=35)."""
    result = []
    for ch in iban:
        if ch.isalpha():
            result.append(str(ord(ch.upper()) - ord("A") + 10))
        else:
            result.append(ch)
    return "".join(result)


def validate_iban(iban: str) -> dict:
    """Validate an IBAN string.

    Returns a dict with:
        - valid: bool
        - iban: str (cleaned, uppercase)
        - country_code: str | None
        - country_length_ok: bool | None (None = country not in registry)
        - format_ok: bool
        - check_digit_valid: bool
        - errors: list[str]
    """
    errors: list[str] = []
    cleaned = iban.replace(" ", "").upper().strip()

    # Basic format check
    if not cleaned:
        return {
            "valid": False,
            "iban": "",
            "country_code": None,
            "country_length_ok": None,
            "format_ok": False,
            "check_digit_valid": False,
            "errors": ["IBAN is empty"],
        }

    if not _IBAN_RE.match(cleaned):
        return {
            "valid": False,
            "iban": cleaned,
            "country_code": _country_code(cleaned) if len(cleaned) >= 2 else None,
            "country_length_ok": None,
            "format_ok": False,
            "check_digit_valid": False,
            "errors": ["IBAN format invalid: expected 2 letters + 2 digits + up to 30 alphanumeric"],
        }

    # Length check (country-specific)
    cc = _country_code(cleaned)
    expected_length = IBAN_COUNTRY_LENGTHS.get(cc)
    country_length_ok: bool | None
    if expected_length is not None:
        country_length_ok = len(cleaned) == expected_length
        if not country_length_ok:
            errors.append(
                f"IBAN length {len(cleaned)} does not match expected {expected_length} for {cc}"
            )
    else:
        country_length_ok = None  # unknown country — skip length check

    # Mod-97 check
    rearranged = _rearrange(cleaned)
    integer_string = _to_integers(rearranged)
    check_digit_valid = int(integer_string) % 97 == 1

    if not check_digit_valid:
        errors.append("IBAN check digit validation failed (mod-97)")

    return {
        "valid": len(errors) == 0,
        "iban": cleaned,
        "country_code": cc,
        "country_length_ok": country_length_ok,
        "format_ok": True,
        "check_digit_valid": check_digit_valid,
        "errors": errors,
    }
