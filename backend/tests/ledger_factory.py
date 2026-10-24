"""Synthetic EvidenceRecord builders for ledger tests (no real data)."""

from app.schemas.common import (
    BoolField,
    CaseInfo,
    DateField,
    NumField,
    OrgTypeField,
    StrField,
)
from app.schemas.evidence import EvidenceRecord

CASE = CaseInfo(client_name="Test Person", case_type="renewal", window_start="2027-01", window_end="2027-06")

DOC_TYPE = {
    "work_gig": ("gig_earnings", "work"),
    "work_paystub": ("paystub", "work"),
    "work_employer": ("employer_statement", "work"),
    "volunteer": ("volunteer_letter", "volunteer"),
    "school": ("school_letter", "school"),
    "training": ("employer_statement", "job_training"),
}


def _f(cls, value, low: bool = False, confirmed: bool = False):
    return cls(value=value, confidence="low" if low else "high", page=1, confirmed=confirmed)


def make_record(
    rec_id: str,
    kind: str,
    start: str,
    end: str,
    hours_h: int = 0,
    gross: int = 0,
    expenses: int = 0,
    issuer: str | None = None,
    low_field: str | None = None,
    confirmed: bool = False,
    half_time: bool = True,
) -> EvidenceRecord:
    doc_type, activity = DOC_TYPE[kind]
    fields: dict = {
        "person_name": _f(StrField, "Test Person"),
        "issuer": _f(StrField, issuer or f"Issuer {rec_id}"),
        "period_start": _f(DateField, start),
        "period_end": _f(DateField, end),
        "document_date": _f(DateField, end),
    }
    if kind == "school":
        fields["half_time_enrolled"] = _f(BoolField, half_time)
    else:
        fields["hours"] = _f(NumField, hours_h / 100)
    if kind == "volunteer":
        fields["org_type"] = _f(OrgTypeField, "nonprofit")
        fields["non_partisan"] = _f(BoolField, True)
    if kind.startswith("work") or kind == "training":
        fields["gross_cents"] = _f(NumField, gross)
    if kind == "work_gig":
        fields["expenses_cents"] = _f(NumField, expenses)
    if low_field and low_field in fields:
        fields[low_field] = fields[low_field].model_copy(update={"confidence": "low", "confirmed": confirmed})
    return EvidenceRecord(id=rec_id, doc_id=f"doc-{rec_id}", doc_type=doc_type, activity=activity, **fields)
