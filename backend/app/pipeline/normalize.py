"""Normalize stage: raw extracted values -> canonical types, then EvidenceRecords.

Money -> integer cents, hours -> float with 2 decimals, dates -> YYYY-MM-DD.
A value that cannot be parsed becomes null with confidence "low" (never guessed).
"""
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, get_args

from app.pipeline.extract.models import RawExtraction, RawField, RawNotice, RawRecord
from app.schemas.common import (
    BoolField,
    DateField,
    DocType,
    NumField,
    OrgType,
    OrgTypeField,
    StrField,
)
from app.schemas.evidence import ActivityType, EvidenceRecord, NoticeInfo, RecordDocType

ACTIVITY_BY_DOC_TYPE: dict[str, ActivityType] = {
    "paystub": "work",
    "employer_statement": "work",
    "gig_earnings": "work",
    "volunteer_letter": "volunteer",
    "school_letter": "school",
}
_RECORD_DOC_TYPES: frozenset[str] = frozenset(get_args(RecordDocType))
_ORG_TYPES: frozenset[str] = frozenset(get_args(OrgType))
_DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y")
_TRUE = {"true", "yes", "y"}
_FALSE = {"false", "no", "n"}


# ---------------------------------------------------------------- value parsers
def parse_money_cents(value: Any) -> int | None:
    """"$1,234.56" / "560" / 560.0 (dollars, as printed) -> cents."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        text = str(value)
    else:
        match = re.search(r"-?\$?\s*([\d,]+(?:\.\d+)?)", str(value))
        if match is None:
            return None
        text = match.group(1).replace(",", "")
    try:
        cents = (Decimal(text) * 100).quantize(Decimal(1))
    except InvalidOperation:
        return None
    return int(cents) if cents >= 0 else None


def parse_hours(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    match = re.search(r"\d+(?:\.\d+)?", str(value))
    if match is None:
        return None
    return float(Decimal(match.group(0)).quantize(Decimal("0.01")))


def parse_date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE:
            return True
        if lowered in _FALSE:
            return False
    return None


def parse_str(value: Any) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    text = " ".join(str(value).split())
    return text or None


def parse_org_type(value: Any) -> str | None:
    text = parse_str(value)
    if text is None:
        return None
    key = text.lower().replace("-", "_").replace(" ", "_")
    return key if key in _ORG_TYPES else "unknown"


# ---------------------------------------------------------------- field builders
def _common(raw: RawField, value: Any) -> dict[str, Any]:
    confidence = raw.confidence if value is not None else "low"
    return {
        "value": value,
        "confidence": confidence,
        "page": raw.page,
        "evidence": raw.evidence,
    }


def _missing() -> dict[str, Any]:
    return {"value": None, "confidence": "low", "page": 1}


def str_field(raw: RawField | None) -> StrField:
    return StrField(**(_missing() if raw is None else _common(raw, parse_str(raw.value))))


def date_field(raw: RawField | None) -> DateField:
    return DateField(
        **(_missing() if raw is None else _common(raw, parse_date(raw.value)))
    )


def _num(raw: RawField | None, parser) -> NumField | None:
    if raw is None:
        return None
    return NumField(**_common(raw, parser(raw.value)))


def _bool(raw: RawField | None) -> BoolField | None:
    if raw is None:
        return None
    return BoolField(**_common(raw, parse_bool(raw.value)))


def _org(raw: RawField | None) -> OrgTypeField | None:
    if raw is None:
        return None
    return OrgTypeField(**_common(raw, parse_org_type(raw.value)))


# ---------------------------------------------------------------- records
def slug(text: str | None) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or "unknown"


def record_id(doc_type: str, issuer: str | None, period_start: str | None) -> str:
    return f"rec-{doc_type}-{slug(issuer)}-{period_start or 'unknown'}"


def normalize_record(
    raw: RawRecord, doc_type: RecordDocType, doc_id: str
) -> EvidenceRecord:
    issuer = str_field(raw.issuer)
    period_start = date_field(raw.period_start)
    return EvidenceRecord(
        id=record_id(doc_type, issuer.value, period_start.value),
        doc_id=doc_id,
        doc_type=doc_type,
        activity=ACTIVITY_BY_DOC_TYPE[doc_type],
        person_name=str_field(raw.person_name),
        issuer=issuer,
        org_type=_org(raw.org_type),
        non_partisan=_bool(raw.non_partisan),
        period_start=period_start,
        period_end=date_field(raw.period_end),
        hours=_num(raw.hours, parse_hours),
        hourly_rate_cents=_num(raw.hourly_rate_cents, parse_money_cents),
        gross_cents=_num(raw.gross_cents, parse_money_cents),
        expenses_cents=_num(raw.expenses_cents, parse_money_cents),
        half_time_enrolled=_bool(raw.half_time_enrolled),
        document_date=date_field(raw.document_date),
    )


def normalize_notice(raw: RawNotice) -> NoticeInfo:
    return NoticeInfo(
        notice_date=date_field(raw.notice_date),
        response_deadline=(
            date_field(raw.response_deadline) if raw.response_deadline else None
        ),
        request_summary=str_field(raw.request_summary),
    )


def normalize(
    doc_type: DocType, extraction: RawExtraction, doc_id: str
) -> tuple[list[EvidenceRecord], NoticeInfo | None]:
    """Records only for record doc types; the notice only for rfi_notice."""
    records: list[EvidenceRecord] = []
    if doc_type in _RECORD_DOC_TYPES:
        records = [
            normalize_record(raw, doc_type, doc_id)  # type: ignore[arg-type]
            for raw in extraction.records
        ]
    notice = None
    if doc_type == "rfi_notice" and extraction.notice is not None:
        notice = normalize_notice(extraction.notice)
    return records, notice
