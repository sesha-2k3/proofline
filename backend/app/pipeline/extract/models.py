"""Raw extraction output shared by the template and LLM extractors.

Values are raw (as read from the document, e.g. "$320.00", "04/01/2027");
normalize.py (B9) converts them to canonical types and builds EvidenceRecords.
Field names match EvidenceRecord so normalize can map them one to one.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Confidence


class _Raw(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RawField(_Raw):
    value: str | float | bool | None = None
    confidence: Confidence = "low"
    page: int = Field(default=1, ge=1)
    evidence: str | None = None


class RawRecord(_Raw):
    person_name: RawField | None = None
    issuer: RawField | None = None
    org_type: RawField | None = None
    non_partisan: RawField | None = None
    period_start: RawField | None = None
    period_end: RawField | None = None
    hours: RawField | None = None
    hourly_rate_cents: RawField | None = None
    gross_cents: RawField | None = None
    expenses_cents: RawField | None = None
    half_time_enrolled: RawField | None = None
    document_date: RawField | None = None


class RawNotice(_Raw):
    notice_date: RawField | None = None
    response_deadline: RawField | None = None
    request_summary: RawField | None = None


class RawExtraction(_Raw):
    records: list[RawRecord] = []
    notice: RawNotice | None = None
