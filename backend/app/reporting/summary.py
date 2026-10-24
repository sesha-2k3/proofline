"""Plain-language summary (en/es) that restates code-computed facts (R9).

The template text is built from the ledger result only. If an LLM is available it may reword the
template, but every number must appear unchanged (same numbers, same count); otherwise the
template is used. The LLM never decides anything here.
"""

import re
from collections import Counter
from typing import Protocol

from app.ledger.evaluate import INCOME_PATH, SCHOOL_PATH
from app.reporting.gaps import issuer_name, unconfirmed_fields
from app.reporting.text import (
    capitalize,
    date_label,
    hours_text,
    money_text,
    month_label,
    month_name,
    threshold_money_text,
)
from app.rules import accessors
from app.schemas.evidence import EvidenceRecord
from app.schemas.ledger import Deadline, MonthResult

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

STATUS_LABEL = {
    "en": {"provisional": "provisional", "unresolved": "unresolved"},
    "es": {"provisional": "provisional", "unresolved": "sin resolver"},
}

class Rephraser(Protocol):
    def rephrase(self, text: str, lang: str) -> str | None: ...


def numbers_in(text: str) -> Counter[str]:
    return Counter(_NUMBER.findall(text))


def numbers_unchanged(original: str, rewritten: str) -> bool:
    return numbers_in(original) == numbers_in(rewritten)


# ---------------------------------------------------------------- pieces


def _excluded_phrase(record: EvidenceRecord, month: str, lang: str) -> str:
    fields = unconfirmed_fields(record)
    if lang == "es":
        what = "las horas" if fields == ["hours"] else "los datos"
        return f"{what} de {month_name(month, 'es')} de {issuer_name(record)}"
    what = "hours" if fields == ["hours"] else "values"
    return f"the {issuer_name(record)}'s {month_name(month)} {what}"


def _join(items: list[str], lang: str) -> str:
    conj = " y " if lang == "es" else " and "
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + conj + items[-1]


def _totals_sentences(m: MonthResult, lang: str) -> list[str]:
    hours = hours_text(m.work_hours + m.volunteer_hours)
    threshold = hours_text(accessors.hours_threshold_hours())
    gross, net = money_text(m.gross_income_cents), money_text(m.net_income_cents)
    if lang == "es":
        income = (
            f"Los ingresos son {gross}."
            if gross == net
            else f"Los ingresos son {gross} antes de gastos y {net} después."
        )
        return [f"Horas contadas: {hours} de {threshold}.", income]
    income = f"Income is {gross}." if gross == net else f"Income is {gross} before expenses and {net} after."
    return [f"Counted hours: {hours} of {threshold}.", income]


def _path_sentences(m: MonthResult, lang: str) -> list[str]:
    out = []
    hours = hours_text(m.work_hours + m.volunteer_hours)
    threshold = hours_text(accessors.hours_threshold_hours())
    above = (m.work_hours + m.volunteer_hours) > accessors.hours_threshold_hours()
    for path in m.paths_met:
        if path == INCOME_PATH:
            net = money_text(m.net_income_cents)
            limit = threshold_money_text(accessors.income_threshold_cents())
            out.append(
                f"La evidencia parece mostrar {net} de ingresos, al menos el requisito de {limit}."
                if lang == "es"
                else f"The evidence appears to show {net} in income, at least the {limit} requirement."
            )
        elif path == SCHOOL_PATH:
            out.append(
                "La evidencia parece mostrar estudios de al menos medio tiempo."
                if lang == "es"
                else "The evidence appears to show at least half-time school enrollment."
            )
        elif lang == "es":
            cmp = "más que" if above else "igual al"
            out.append(f"La evidencia parece mostrar {hours} horas que cuentan, {cmp} el requisito de {threshold} horas.")
        else:
            cmp = "above" if above else "equal to"
            out.append(f"The evidence appears to show {hours} qualifying hours, {cmp} the {threshold}-hour requirement.")
    return out


def _deadline_sentence(deadline: Deadline, lang: str) -> str:
    label = STATUS_LABEL[lang].get(deadline.rule_status)
    suffix = f" ({label})" if label else ""
    if lang == "es":
        return f"Fecha límite para responder: {date_label(deadline.date, 'es')}{suffix}."
    return f"Response deadline: {date_label(deadline.date)}{suffix}."


def _depends_sentence(m: MonthResult, excluded: list[EvidenceRecord], lang: str) -> str:
    parts = []
    name = month_name(m.month, lang)
    if lang == "es":
        if m.depends_on_unresolved:
            parts.append("de reglas que MassHealth aún no ha definido")
        if excluded:
            parts.append("de confirmar " + _join([_excluded_phrase(r, m.month, lang) for r in excluded], lang))
        return f"Si {name} cumple el requisito depende {' y '.join(parts)}."
    if m.depends_on_unresolved:
        parts.append("rules MassHealth has not settled")
    if excluded:
        parts.append("confirming " + _join([_excluded_phrase(r, m.month, lang) for r in excluded], lang))
    return f"Whether {name} meets the requirement depends on {', and on '.join(parts)}."


def _short_sentences(excluded: list[EvidenceRecord], m: MonthResult, lang: str) -> list[str]:
    if lang == "es":
        out = ["La evidencia contada todavía no muestra un mes que cumpla el requisito."]
        if excluded:
            phrase = _join([_excluded_phrase(r, m.month, lang) for r in excluded], lang)
            out.append(f"Confirmar {phrase} podría cambiar esto.")
        return out
    out = ["The counted evidence does not yet show a month that meets the requirement."]
    if excluded:
        phrase = _join([_excluded_phrase(r, m.month, lang) for r in excluded], lang)
        out.append(f"Confirming {phrase} could change this.")
    return out


# ---------------------------------------------------------------- public


def template_summary(
    months: list[MonthResult],
    best: str | None,
    records: list[EvidenceRecord],
    deadline: Deadline | None,
    lang: str = "en",
) -> str:
    final = "MassHealth toma la decisión final." if lang == "es" else "MassHealth makes the final decision."
    m = next((x for x in months if x.month == best), None)
    if m is None:
        if lang == "es":
            return f"No hay meses para revisar. Agregue el período de renovación o el mes de solicitud. {final}"
        return f"There are no months to check. Add the renewal window or application month. {final}"
    by_id = {r.id: r for r in records}
    excluded = [by_id[i] for i in m.excluded_record_ids if i in by_id]
    opening = (
        f"{capitalize(month_label(m.month, 'es'))} es el mes más fuerte."
        if lang == "es"
        else f"{month_label(m.month)} is the strongest month."
    )
    sentences = [opening]
    if m.status == "meets":
        sentences += _path_sentences(m, lang)
        if deadline is not None:
            sentences.append(_deadline_sentence(deadline, lang))
    elif m.status == "conditional":
        sentences += _totals_sentences(m, lang)
        sentences.append(_depends_sentence(m, excluded, lang))
    else:
        sentences += _totals_sentences(m, lang)
        sentences += _short_sentences(excluded, m, lang)
    sentences.append(final)
    return " ".join(sentences)


def build_summary(
    months: list[MonthResult],
    best: str | None,
    records: list[EvidenceRecord],
    deadline: Deadline | None,
    lang: str = "en",
    rephraser: Rephraser | None = None,
) -> str:
    text = template_summary(months, best, records, deadline, lang)
    if rephraser is None:
        return text
    rewritten = rephraser.rephrase(text, lang)
    if not rewritten or not rewritten.strip() or not numbers_unchanged(text, rewritten):
        return text
    return rewritten.strip()
