"""Submission record PDF (R9): a table of what was sent to MassHealth, when, and how."""
from reportlab.platypus import Flowable, Spacer

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
from app.reporting.text import date_label
from app.schemas.api import TimelineRequest

CHANNEL_LABELS = {
    "online": "Online",
    "mail": "Mail",
    "fax": "Fax",
    "in_person": "In person",
    "phone": "Phone",
}
NOTE_TEXT = "Keep this record with your copy of the packet. It shows what was sent and when."


def build_timeline(body: TimelineRequest) -> bytes:
    case = body.case_info
    story: list[Flowable] = [
        p("Proofline submission record", TITLE),
        p(NOTE_TEXT, NOTE),
        Spacer(1, 8),
        label_value("Client", case.client_name),
        label_value("Case type", CASE_TYPE_LABELS[case.case_type]),
    ]
    if case.rfi_received_date:
        story.append(label_value("Request for Information received", date_label(case.rfi_received_date)))
    story.append(p("Submissions", H2))
    if not body.submissions:
        story.append(p("No submissions logged."))
    else:
        rows = [
            [
                date_label(s.submitted_at),
                CHANNEL_LABELS[s.channel],
                s.confirmation_number or "—",
                ", ".join(s.documents_included) or "—",
                s.notes or "—",
            ]
            for s in sorted(body.submissions, key=lambda s: s.submitted_at)
        ]
        header = ["Date submitted", "Channel", "Confirmation number", "Documents included", "Notes"]
        story.append(table(header, rows, [0.16, 0.12, 0.18, 0.28, 0.26]))
    return build_pdf("Proofline submission record", story)
