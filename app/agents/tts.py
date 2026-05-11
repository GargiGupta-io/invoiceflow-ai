"""Helpers for voice-safe formatting of finance workflow output."""

from __future__ import annotations

from datetime import date
from typing import Any


_SPOKEN_SYMBOLS = {
    "-": "dash",
    "/": "slash",
    "_": "underscore",
    "#": "number",
    ".": "dot",
}

_CURRENCY_SPEECH = {
    "USD": ("dollar", "cent"),
    "$": ("dollar", "cent"),
    "INR": ("rupee", "paise"),
    "₹": ("rupee", "paise"),
    "EUR": ("euro", "cent"),
    "€": ("euro", "cent"),
    "GBP": ("pound", "pence"),
    "£": ("pound", "pence"),
}

_MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def tts_safe_identifier(raw_value: str | None, *, label: str | None = None) -> str:
    """Return an identifier in a form that is easy for TTS systems to read aloud."""

    if not raw_value:
        return label or "the invoice"

    spoken_parts: list[str] = []
    for character in str(raw_value).strip():
        if character.isalpha():
            spoken_parts.append(character.upper())
        elif character.isdigit():
            spoken_parts.append(character)
        elif character in _SPOKEN_SYMBOLS:
            spoken_parts.append(_SPOKEN_SYMBOLS[character])

    if not spoken_parts:
        return label or "the invoice"

    identifier_text = " ".join(spoken_parts)
    if label:
        return f"{label} {identifier_text}"
    return identifier_text


def tts_safe_date_text(raw_value: date | str | None) -> str:
    """Return a voice-friendly date string."""

    if raw_value is None:
        return "the stated due date"

    parsed_value: date | None = None
    if isinstance(raw_value, date):
        parsed_value = raw_value
    else:
        try:
            parsed_value = date.fromisoformat(str(raw_value))
        except ValueError:
            return str(raw_value)

    month_name = _MONTH_NAMES.get(parsed_value.month, str(parsed_value.month))
    return f"{month_name} {parsed_value.day}, {parsed_value.year}"


def tts_safe_amount_text(amount: float | None, currency: Any) -> str:
    """Return a voice-friendly money string."""

    if amount is None:
        return "the outstanding amount"

    currency_text = _currency_value(currency)
    major_minor_units = _CURRENCY_SPEECH.get(currency_text)
    rounded_amount = round(float(amount), 2)
    major_value = int(rounded_amount)
    minor_value = int(round((rounded_amount - major_value) * 100))

    if not major_minor_units:
        if currency_text:
            return f"{currency_text} {rounded_amount:,.2f}"
        return f"{rounded_amount:,.2f}"

    major_unit, minor_unit = major_minor_units
    major_label = major_unit if major_value == 1 else f"{major_unit}s"
    if minor_value == 0:
        return f"{major_value:,} {major_label}"

    minor_label = minor_unit if minor_value == 1 else f"{minor_unit}s"
    return f"{major_value:,} {major_label} and {minor_value} {minor_label}"


def _currency_value(raw_value: Any) -> str:
    if raw_value is None:
        return ""
    if hasattr(raw_value, "value"):
        return str(raw_value.value)
    return str(raw_value)
