from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


Lang = Literal["en", "es"]
Confidence = Literal["high", "low"]
RuleStatus = Literal["confirmed", "provisional", "unresolved"]

IsoDate = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]
IsoMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}$")]

Verification = Literal["grounded", "ungrounded", "not_checked"]

OrgType = Literal["public", "nonprofit", "for_profit", "political", "unknown"]


class _FieldBase(ApiModel):
    confidence: Confidence
    page: int = Field(ge=1)
    confirmed: bool = False
    evidence: str | None = None
    verification: Verification = "not_checked"


class StrField(_FieldBase):
    value: str | None


class NumField(_FieldBase):
    value: float | None


class BoolField(_FieldBase):
    value: bool | None


class DateField(_FieldBase):
    value: IsoDate | None


class OrgTypeField(_FieldBase):
    value: OrgType | None


DocType = Literal[
    "rfi_notice",
    "paystub",
    "employer_statement",
    "gig_earnings",
    "volunteer_letter",
    "school_letter",
    "unknown",
]


class CaseInfo(ApiModel):
    client_name: str = Field(min_length=1)
    case_type: Literal["renewal", "new_application"]
    window_start: IsoMonth | None = None
    window_end: IsoMonth | None = None
    application_month: IsoMonth | None = None
    rfi_received_date: IsoDate | None = None
    lang: Lang = "en"


ErrorCode = Literal["BAD_REQUEST", "UNSUPPORTED_FILE", "EXTRACTION_FAILED", "RULES_INVALID", "INTERNAL"]


class ErrorDetail(ApiModel):
    code: ErrorCode
    message: str
    details: Any | None = None


class ErrorBody(ApiModel):
    error: ErrorDetail
