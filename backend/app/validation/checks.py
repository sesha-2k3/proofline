"""Cross-document checks (R5). Pure: records in, records with flags out.

Pipeline flags from verify (UNGROUNDED_VALUE, DATE_OUT_OF_RANGE, ARITHMETIC_MISMATCH) are kept.
Flags owned by this module are recomputed on every call, so validating twice gives the same result.
Thresholds and rule statuses come from app.rules.accessors.
"""

from datetime import date, timedelta

from pydantic.alias_generators import to_camel

from app.ledger.evaluate import (
    FIELD_NAMES,
    dedupe_key,
    dedupe_order,
    volunteer_eligible,
)
from app.rules import accessors
from app.schemas.common import CaseInfo
from app.schemas.evidence import EvidenceRecord, Flag

VALIDATION_CODES = {
    "DUPLICATE",
    "STALE_DOCUMENT",
    "VOLUNTEER_ORG_INELIGIBLE",
    "NAME_MISMATCH",
    "LOW_CONFIDENCE_UNCONFIRMED",
}
STALE_RULE = "paystub_recency_days"
STALE_DOC_TYPES = ("paystub", "employer_statement")
VOLUNTEER_RULE = "volunteer_org_requirement"


def _name_key(name: str) -> str:
    return " ".join(name.split()).casefold()


def _duplicates(records: list[EvidenceRecord]) -> dict[str, str]:
    """Record id -> id of the copy the ledger keeps, for every copy it drops."""
    kept: dict[tuple, str] = {}
    dropped: dict[str, str] = {}
    for r in sorted(records, key=dedupe_order):
        if r.period_start.value is None or r.period_end.value is None:
            continue
        key = dedupe_key(r)
        if key in kept:
            dropped[r.id] = kept[key]
        else:
            kept[key] = r.id
    return dropped


def _is_stale(record: EvidenceRecord, case_info: CaseInfo) -> bool:
    if record.doc_type not in STALE_DOC_TYPES:
        return False
    if record.document_date.value is None or case_info.rfi_received_date is None:
        return False
    received = date.fromisoformat(case_info.rfi_received_date)
    oldest = received - timedelta(days=accessors.paystub_recency_days())
    return date.fromisoformat(record.document_date.value) < oldest


def record_flags(
    record: EvidenceRecord, case_info: CaseInfo, duplicate_of: str | None
) -> list[Flag]:
    flags: list[Flag] = []
    if duplicate_of is not None:
        flags.append(
            Flag(
                code="DUPLICATE",
                message=f"This looks like a copy of another record ({duplicate_of}). It is counted once.",
            )
        )
    if _is_stale(record, case_info):
        days = accessors.paystub_recency_days()
        flags.append(
            Flag(
                code="STALE_DOCUMENT",
                message=(
                    f"This document is dated more than {days} days before the notice was received. "
                    "MassHealth may ask for a newer one."
                ),
                field="documentDate",
                rule_id=STALE_RULE,
                rule_status=accessors.rule_status(STALE_RULE),
            )
        )
    if record.activity == "volunteer" and not volunteer_eligible(record):
        flags.append(
            Flag(
                code="VOLUNTEER_ORG_INELIGIBLE",
                message=(
                    "Volunteer hours count only with a non-partisan public or nonprofit group. "
                    "These hours are not counted."
                ),
                field="orgType",
                rule_id=VOLUNTEER_RULE,
                rule_status=accessors.rule_status(VOLUNTEER_RULE),
            )
        )
    person = record.person_name.value
    if person is not None and _name_key(person) != _name_key(case_info.client_name):
        flags.append(
            Flag(
                code="NAME_MISMATCH",
                message=f'The name on this document ("{person}") does not match the client name.',
                field="personName",
            )
        )
    for name in FIELD_NAMES:
        f = getattr(record, name)
        if f is not None and f.confidence == "low" and not f.confirmed:
            flags.append(
                Flag(
                    code="LOW_CONFIDENCE_UNCONFIRMED",
                    message="This value was hard to read. Confirm it to count this record.",
                    field=to_camel(name),
                )
            )
    return flags


def validate_records(case_info: CaseInfo, records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    """Return the records (same order) with pipeline flags kept and validation flags recomputed."""
    duplicates = _duplicates(records)
    out: list[EvidenceRecord] = []
    for r in records:
        kept = [f for f in r.flags if f.code not in VALIDATION_CODES]
        new = record_flags(r, case_info, duplicates.get(r.id))
        out.append(r.model_copy(update={"flags": kept + new}))
    return out
