"""Evidence packet PDF (R9). Restates code-computed results; never states eligibility."""
from reportlab.platypus import Flowable, PageBreak, Spacer

from app.packet._common import (
    CASE_TYPE_LABELS,
    H2,
    NOTE,
    TITLE,
    build_pdf,
    label_value,
    p,
    table,
)
from app.reporting.text import date_label, hours_text, money_text, month_label
from app.rules import accessors
from app.schemas.api import PacketRequest
from app.schemas.evidence import EvidenceRecord
from app.schemas.ledger import MonthResult

DISCLAIMER = "This summary organizes evidence. MassHealth makes all eligibility decisions."
EXEMPTION_LABEL = "Possible exemption — navigator to confirm"

STATUS_TEXT = {
    "meets": "Meets — the evidence appears to show this month meets the requirement.",
    "conditional": "Conditional — the result depends on rules MassHealth has not settled or on values a navigator must confirm.",
    "short": "Short — the evidence does not yet show enough for this month.",
}

_RECORD_FIELDS = (
    "person_name", "issuer", "org_type", "non_partisan", "period_start", "period_end", "hours",
    "hourly_rate_cents", "gross_cents", "expenses_cents", "half_time_enrolled", "document_date",
)


def _fields(record: EvidenceRecord) -> list:
    return [f for name in _RECORD_FIELDS if (f := getattr(record, name)) is not None]


def _verification(record: EvidenceRecord) -> str:
    states = {f.verification for f in _fields(record)}
    if "ungrounded" in states:
        return "Ungrounded"
    if states == {"grounded"}:
        return "Grounded"
    return "Not checked" if states == {"not_checked"} else "Partly checked"


def _confirmed(record: EvidenceRecord) -> str:
    names = [name for name in _RECORD_FIELDS if (f := getattr(record, name)) is not None and f.confirmed]
    return "Yes (" + ", ".join(n.replace("_", " ") for n in names) + ")" if names else "No"


def _rule_text(rule_id: str) -> str:
    entry = accessors.rule(rule_id)
    return f"{rule_id}: {entry.description or entry.label or rule_id}"


def _cover(body: PacketRequest, best: MonthResult | None) -> list[Flowable]:
    case = body.case_info
    ev = body.evaluation
    story: list[Flowable] = [
        p("Proofline evidence summary", TITLE),
        p(DISCLAIMER, NOTE),
        Spacer(1, 8),
        label_value("Client", case.client_name),
        label_value("Case type", CASE_TYPE_LABELS[case.case_type]),
    ]
    if case.case_type == "renewal" and case.window_start and case.window_end:
        story.append(label_value("Months reviewed", f"{month_label(case.window_start)} to {month_label(case.window_end)}"))
    if case.case_type == "new_application" and case.application_month:
        story.append(label_value("Application month", month_label(case.application_month)))
    story.append(label_value("Rules version", ev.rules_version))

    story.append(p("Strongest month", H2))
    if best is None:
        story.append(p("No month could be reviewed with the information given."))
    else:
        story += [
            label_value("Month", month_label(best.month)),
            label_value("Status", STATUS_TEXT[best.status]),
            label_value("Work hours", hours_text(best.work_hours)),
            label_value("Volunteer hours", hours_text(best.volunteer_hours)),
            label_value("Job training hours", hours_text(best.training_hours)),
            label_value("School at least half-time", "Yes" if best.school_half_time else "No"),
            label_value("Income before expenses", money_text(best.gross_income_cents)),
            label_value("Income after expenses", money_text(best.net_income_cents)),
            label_value("Requirement paths met", ", ".join(best.paths_met) or "None shown"),
        ]
        story.append(p("Unresolved rules affecting this result", H2))
        if best.depends_on_unresolved:
            story += [p("• " + _rule_text(rid)) for rid in best.depends_on_unresolved]
        else:
            story.append(p("None."))

    story.append(p("Response deadline", H2))
    if ev.deadline is None:
        story.append(p("No Request for Information date was entered."))
    else:
        label = date_label(ev.deadline.date)
        if ev.deadline.rule_status != "confirmed":
            label += f" ({ev.deadline.rule_status})"
        story.append(label_value("Respond by", label))

    if ev.summary:
        story += [p("Summary", H2), p(ev.summary)]
    story += [Spacer(1, 12), p(DISCLAIMER, NOTE)]
    return story


def _evidence(records: list[EvidenceRecord]) -> list[Flowable]:
    story: list[Flowable] = [p("Evidence", H2)]
    if not records:
        return story + [p("No evidence records were included.")]
    rows = []
    for r in sorted(records, key=lambda x: x.id):
        period = f"{r.period_start.value or '?'} to {r.period_end.value or '?'}"
        hours = hours_text(r.hours.value) if r.hours is not None and r.hours.value is not None else "—"
        amount = money_text(round(r.gross_cents.value)) if r.gross_cents is not None and r.gross_cents.value is not None else "—"
        page = (r.hours or r.gross_cents or r.issuer).page
        rows.append([r.id, r.issuer.value or "—", period, hours, amount, str(page), _verification(r), _confirmed(r)])
    header = ["Record", "Issuer", "Period", "Hours", "Amount", "Source page", "Verification", "Confirmed by navigator"]
    return story + [table(header, rows, [0.22, 0.14, 0.14, 0.07, 0.09, 0.07, 0.11, 0.16])]


def _exemptions(body: PacketRequest) -> list[Flowable]:
    story: list[Flowable] = [p("Possible exemptions", H2)]
    items = body.evaluation.possible_exemptions
    if not items:
        return story + [p("None indicated.")]
    for ex in items:
        story.append(p(f"{EXEMPTION_LABEL}: {ex.label}"))
        story.append(p(f"Source: {ex.source} {ex.source_url}".rstrip(), NOTE))
    return story


def build_packet(body: PacketRequest) -> bytes:
    ev = body.evaluation
    best = next((m for m in ev.months if m.month == ev.best_month), None)
    story = _cover(body, best) + [PageBreak()] + _evidence(body.records) + _exemptions(body)
    return build_pdf("Proofline evidence summary", story)
