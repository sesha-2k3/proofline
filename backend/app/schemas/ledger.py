from typing import Literal

from app.schemas.common import ApiModel, DocType, IsoDate, IsoMonth, RuleStatus

MonthStatus = Literal["meets", "conditional", "short"]


class MonthResult(ApiModel):
    month: IsoMonth
    work_hours: float
    volunteer_hours: float
    training_hours: float
    school_half_time: bool
    gross_income_cents: int
    net_income_cents: int
    status: MonthStatus
    paths_met: list[str]
    depends_on_unresolved: list[str]
    hours_shortfall: float
    income_shortfall_cents: int
    counted_record_ids: list[str]
    excluded_record_ids: list[str]


class GapItem(ApiModel):
    month: IsoMonth
    kind: Literal["hours", "income", "unresolved_rule", "unconfirmed_record"]
    message: str
    suggested_doc_types: list[DocType]
    rule_id: str | None = None


class PossibleExemption(ApiModel):
    id: str
    label: str
    source: str
    source_url: str


class Deadline(ApiModel):
    date: IsoDate
    rule_id: Literal["rfi_response_days"]
    rule_status: RuleStatus
