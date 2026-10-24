"""Gap report (BUILD_PLAN Appendix "Gaps"). Restates code-computed ledger results; decides nothing.

Order: best-month unconfirmed_record gaps, then best-month unresolved_rule gaps (dependsOnUnresolved
order), then unconfirmed_record gaps for other months (chronological), then hours gaps for short
months that have records (chronological), then short months with no records (chronological).
"""

from datetime import date

from app.ledger.evaluate import FIELD_NAMES, JOB_TRAINING, SELF_EMPLOYMENT, SPLIT_METHOD
from app.ledger.split import overlapped_months
from app.reporting.text import hours_text, month_label, month_name, threshold_money_text
from app.rules import accessors
from app.schemas.common import DocType
from app.schemas.evidence import EvidenceRecord
from app.schemas.ledger import GapItem, MonthResult

HOURS_DOC_TYPES: list[DocType] = ["employer_statement", "volunteer_letter", "paystub"]

FIELD_LABELS = {
    "person_name": "name",
    "issuer": "organization name",
    "org_type": "organization type",
    "non_partisan": "non-partisan status",
    "period_start": "start date",
    "period_end": "end date",
    "hours": "hours",
    "hourly_rate_cents": "pay rate",
    "gross_cents": "pay",
    "expenses_cents": "expenses",
    "half_time_enrolled": "enrollment status",
    "document_date": "document date",
}


def unconfirmed_fields(record: EvidenceRecord) -> list[str]:
    """Field names that keep the record from counting (low confidence, not confirmed)."""
    out = []
    for name in FIELD_NAMES:
        f = getattr(record, name)
        if f is not None and f.confidence != "high" and not f.confirmed:
            out.append(name)
    return out


def issuer_name(record: EvidenceRecord) -> str:
    return record.issuer.value or "this document"


def unconfirmed_message(record: EvidenceRecord, month: str) -> str:
    fields = unconfirmed_fields(record)
    who = f"The {issuer_name(record)}'s {month_name(month)}"
    if fields == ["hours"] and record.hours is not None and record.hours.value is not None:
        h = hours_text(record.hours.value)
        return f"{who} hours were hard to read. Confirm the {h} hours to count them."
    labels = ", ".join(FIELD_LABELS[f] for f in fields)
    return f"{who} record has values that were hard to read ({labels}). Confirm them to count this record."


def _unconfirmed_gaps(m: MonthResult, by_id: dict[str, EvidenceRecord]) -> list[GapItem]:
    return [
        GapItem(
            month=m.month,
            kind="unconfirmed_record",
            message=unconfirmed_message(by_id[rid], m.month),
            suggested_doc_types=[by_id[rid].doc_type],
        )
        for rid in m.excluded_record_ids
        if rid in by_id
    ]


def _split_records(m: MonthResult, by_id: dict[str, EvidenceRecord]) -> list[tuple[EvidenceRecord, list[str]]]:
    """Counted records in month m whose period also covers other months."""
    out = []
    for rid in m.counted_record_ids:
        r = by_id.get(rid)
        if r is None or r.period_start.value is None or r.period_end.value is None:
            continue
        others = [
            x
            for x in overlapped_months(date.fromisoformat(r.period_start.value), date.fromisoformat(r.period_end.value))
            if x != m.month
        ]
        if others:
            out.append((r, others))
    return out


def unresolved_message(rule_id: str, m: MonthResult, by_id: dict[str, EvidenceRecord]) -> str:
    name = month_name(m.month)
    if rule_id == SELF_EMPLOYMENT:
        income = threshold_money_text(accessors.income_threshold_cents())
        return (
            f"{name}'s income meets {income} only if gig income counts before expenses. "
            "MassHealth has not said which applies."
        )
    if rule_id == SPLIT_METHOD:
        parts = []
        for r, others in _split_records(m, by_id):
            kind = "pay period" if r.doc_type in ("paystub", "employer_statement") else "period"
            where = " and ".join(
                month_name(x) if x[:4] == m.month[:4] else month_label(x) for x in others
            )
            parts.append(f"Part of the {issuer_name(r)} {kind} falls in {where}.")
        return " ".join([*parts, "How MassHealth splits pay periods is not published."])
    if rule_id == JOB_TRAINING:
        hours = hours_text(accessors.hours_threshold_hours())
        return (
            f"{name} reaches {hours} hours only if the job training counts. "
            "MassHealth has not published which programs are approved."
        )
    return accessors.rule(rule_id).description or rule_id


def _hours_gap(m: MonthResult) -> GapItem:
    threshold = hours_text(accessors.hours_threshold_hours())
    return GapItem(
        month=m.month,
        kind="hours",
        message=f"{month_label(m.month)} is {hours_text(m.hours_shortfall)} hours short of {threshold}.",
        suggested_doc_types=list(HOURS_DOC_TYPES),
    )


def build_gaps(months: list[MonthResult], best: str | None, records: list[EvidenceRecord]) -> list[GapItem]:
    by_id = {r.id: r for r in records}
    gaps: list[GapItem] = []
    best_m = next((m for m in months if m.month == best), None)
    if best_m is not None:
        gaps += _unconfirmed_gaps(best_m, by_id)
        gaps += [
            GapItem(
                month=best_m.month,
                kind="unresolved_rule",
                message=unresolved_message(rule_id, best_m, by_id),
                suggested_doc_types=[],
                rule_id=rule_id,
            )
            for rule_id in best_m.depends_on_unresolved
        ]
    for m in months:
        if m is not best_m:
            gaps += _unconfirmed_gaps(m, by_id)
    short = [m for m in months if m.status == "short"]
    with_records = [m for m in short if m.counted_record_ids or m.excluded_record_ids]
    without = [m for m in short if not (m.counted_record_ids or m.excluded_record_ids)]
    gaps += [_hours_gap(m) for m in with_records + without]
    return gaps
