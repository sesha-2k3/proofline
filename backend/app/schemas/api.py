from typing import Literal

from pydantic import Field

from app.schemas.common import (
    ApiModel,
    CaseInfo,
    Confidence,
    DocType,
    IsoDate,
    IsoMonth,
    RuleStatus,
)
from app.schemas.evidence import EvidenceRecord, NoticeInfo, PipelineStage
from app.schemas.ledger import Deadline, GapItem, MonthResult, PossibleExemption


class HealthResponse(ApiModel):
    ok: bool
    demo_mode: bool
    llm_provider: Literal["anthropic", "bedrock", "none"]
    rules_version: str


class Thresholds(ApiModel):
    hours: float
    income_cents: int
    rfi_response_days: int


class UnresolvedRule(ApiModel):
    id: str
    description: str


class RulesResponse(ApiModel):
    rules_version: str
    thresholds: Thresholds
    rule_statuses: dict[str, RuleStatus]
    unresolved_rules: list[UnresolvedRule]
    exemption_questions: list[PossibleExemption]
    sources: dict[str, str]


class SampleFile(ApiModel):
    name: str
    url: str
    doc_type: DocType


class SamplesResponse(ApiModel):
    files: list[SampleFile]
    case_info: CaseInfo
    rules_version: str


class LineBox(ApiModel):
    x0: float = Field(ge=0, le=1)  # left, fraction of page width
    y0: float = Field(ge=0, le=1)  # top, fraction of page height (top-left origin)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)


class TextLine(ApiModel):
    text: str
    box: LineBox


class PageView(ApiModel):
    page: int = Field(ge=1)
    image_data_url: str | None = None  # "data:image/png;base64,..."
    lines: list[TextLine] = Field(default_factory=list)


class DocumentResult(ApiModel):
    doc_id: str
    file_name: str
    doc_type: DocType
    classification_confidence: Confidence
    extractor: Literal["template", "llm", "none"]
    records: list[EvidenceRecord]
    notice: NoticeInfo | None = None
    pipeline: list[PipelineStage]
    warnings: list[str]
    demo_mode: bool
    rules_version: str
    pages: list[PageView] = Field(default_factory=list)


class ValidateRequest(ApiModel):
    case_info: CaseInfo
    records: list[EvidenceRecord]


class ValidateResponse(ApiModel):
    records: list[EvidenceRecord]
    rules_version: str


class ExemptionAnswer(ApiModel):
    id: str
    answer: bool


class EvaluateRequest(ApiModel):
    case_info: CaseInfo
    records: list[EvidenceRecord]
    exemption_answers: list[ExemptionAnswer] = Field(default_factory=list)


class EvaluateResponse(ApiModel):
    months: list[MonthResult]
    best_month: IsoMonth | None = None
    deadline: Deadline | None = None
    possible_exemptions: list[PossibleExemption]
    gaps: list[GapItem]
    summary: str
    demo_mode: bool
    rules_version: str


class DeadlineRequest(ApiModel):
    case_info: CaseInfo


class DeadlineResponse(ApiModel):
    deadline: Deadline | None = None
    rules_version: str


class SubmissionEntry(ApiModel):
    submitted_at: IsoDate
    channel: Literal["online", "mail", "fax", "in_person", "phone"]
    confirmation_number: str | None = None
    documents_included: list[str]
    notes: str | None = None


class PacketRequest(ApiModel):
    case_info: CaseInfo
    records: list[EvidenceRecord]
    evaluation: EvaluateResponse


class TimelineRequest(ApiModel):
    case_info: CaseInfo
    submissions: list[SubmissionEntry]
