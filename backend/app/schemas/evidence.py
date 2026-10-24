from typing import Literal

from pydantic import Field

from app.schemas.common import (
    ApiModel,
    BoolField,
    DateField,
    NumField,
    OrgTypeField,
    RuleStatus,
    StrField,
)

ActivityType = Literal["work", "volunteer", "job_training", "school", "income_only"]

RecordDocType = Literal[
    "paystub",
    "employer_statement",
    "gig_earnings",
    "volunteer_letter",
    "school_letter",
]

FlagCode = Literal[
    "ARITHMETIC_MISMATCH",
    "DUPLICATE",
    "STALE_DOCUMENT",
    "VOLUNTEER_ORG_INELIGIBLE",
    "NAME_MISMATCH",
    "LOW_CONFIDENCE_UNCONFIRMED",
    "UNGROUNDED_VALUE",
    "DATE_OUT_OF_RANGE",
]


class Flag(ApiModel):
    code: FlagCode
    message: str
    field: str | None = None
    rule_id: str | None = None
    rule_status: RuleStatus | None = None


class EvidenceRecord(ApiModel):
    id: str
    doc_id: str
    doc_type: RecordDocType
    activity: ActivityType
    person_name: StrField
    issuer: StrField
    org_type: OrgTypeField | None = None
    non_partisan: BoolField | None = None
    period_start: DateField
    period_end: DateField
    hours: NumField | None = None
    hourly_rate_cents: NumField | None = None
    gross_cents: NumField | None = None
    expenses_cents: NumField | None = None
    half_time_enrolled: BoolField | None = None
    document_date: DateField
    flags: list[Flag] = Field(default_factory=list)


class NoticeInfo(ApiModel):
    notice_date: DateField
    response_deadline: DateField | None = None
    request_summary: StrField


class PipelineStage(ApiModel):
    stage: Literal["ingest", "render", "classify", "extract", "normalize", "verify"]
    status: Literal["ok", "warning", "failed", "skipped"]
    duration_ms: int
    detail: str
