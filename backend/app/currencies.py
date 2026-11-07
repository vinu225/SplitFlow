"""
Currency-Specific Minor Units (ISO 4217) Registry.
Guarantees precision integer accounting without floating-point errors.
Rejects unmapped currencies explicitly.
"""
from decimal import Decimal, ROUND_HALF_UP

# Exhaustive Supported ISO 4217 Currency Exponent Registry
CURRENCY_MINOR_UNITS: dict[str, int] = {
    # 2 Decimals (Standard)
    "USD": 2, "EUR": 2, "GBP": 2, "PHP": 2, "BRL": 2,
    "CAD": 2, "AUD": 2, "SGD": 2, "HKD": 2, "NZD": 2,
    "INR": 2, "MXN": 2, "CHF": 2, "SEK": 2, "NOK": 2,
    # 0 Decimals (Zero-exponent currencies)
    "JPY": 0, "KRW": 0, "VND": 0, "CLP": 0, "PYG": 0,
    # 3 Decimals (Three-exponent currencies)
    "KWD": 3, "BHD": 3, "OMR": 3, "JOD": 3, "TND": 3
}

class UnsupportedCurrencyError(ValueError):
    """Raised when an unmapped or invalid ISO 4217 currency is encountered."""
    pass

def get_currency_decimals(currency: str) -> int:
    """Returns number of minor unit decimal places for an ISO currency code."""
    if not currency:
        raise UnsupportedCurrencyError("Currency code cannot be empty.")
    curr_clean = currency.upper().strip()
    if curr_clean not in CURRENCY_MINOR_UNITS:
        raise UnsupportedCurrencyError(
            f"Currency '{curr_clean}' is not supported by SplitFlow. "
            f"Explicit minor unit configuration required. Supported: {list(CURRENCY_MINOR_UNITS.keys())}"
        )
    return CURRENCY_MINOR_UNITS[curr_clean]

def to_minor_units(amount_str: str | float | Decimal | int, currency: str) -> int:
    """Converts a monetary value into integer minor units without floating-point math."""
    decimals = get_currency_decimals(currency)
    multiplier = Decimal(10) ** decimals
    d_amount = Decimal(str(amount_str).strip())
    return int((d_amount * multiplier).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

def from_minor_units(minor_units: int, currency: str) -> str:
    """Formats integer minor units into standard decimal string representation."""
    decimals = get_currency_decimals(currency)
    divisor = Decimal(10) ** decimals
    return f"{Decimal(minor_units) / divisor:.{decimals}f}"

