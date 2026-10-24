"""Small formatting helpers shared by reporting modules (en/es)."""

MONTHS = {
    "en": [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ],
    "es": [
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ],
}


def month_name(month: str, lang: str = "en") -> str:
    """'2027-05' -> 'May' / 'mayo'."""
    return MONTHS[lang][int(month[5:7]) - 1]


def month_label(month: str, lang: str = "en") -> str:
    """'2027-05' -> 'May 2027' / 'mayo de 2027'."""
    name = month_name(month, lang)
    return f"{name} {month[:4]}" if lang == "en" else f"{name} de {month[:4]}"


def date_label(iso: str, lang: str = "en") -> str:
    """'2027-07-12' -> 'July 12, 2027' / '12 de julio de 2027'."""
    name = MONTHS[lang][int(iso[5:7]) - 1]
    day = int(iso[8:10])
    return f"{name} {day}, {iso[:4]}" if lang == "en" else f"{day} de {name} de {iso[:4]}"


def hours_text(hours: float) -> str:
    """68.93 -> '68.93', 80.0 -> '80', 36.5 -> '36.5'."""
    return f"{hours:.2f}".rstrip("0").rstrip(".")


def money_text(cents: int) -> str:
    """73714 -> '$737.14'."""
    return f"${cents / 100:,.2f}"


def threshold_money_text(cents: int) -> str:
    """Whole-dollar thresholds without cents: 58000 -> '$580'."""
    return f"${cents // 100:,}" if cents % 100 == 0 else money_text(cents)


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]
