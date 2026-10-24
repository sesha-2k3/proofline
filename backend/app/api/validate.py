"""Mock POST /validate (B4). Replaced by validation/checks.py in B10."""

from fastapi import APIRouter

from app.rules import accessors
from app.schemas.api import ValidateRequest, ValidateResponse
from app.schemas.evidence import EvidenceRecord, Flag

router = APIRouter(tags=["validate"])


def _flag_low_hours(record: EvidenceRecord) -> EvidenceRecord:
    hours = record.hours
    if hours is None or hours.confidence != "low" or hours.confirmed:
        return record
    if any(f.code == "LOW_CONFIDENCE_UNCONFIRMED" and f.field == "hours" for f in record.flags):
        return record
    flag = Flag(
        code="LOW_CONFIDENCE_UNCONFIRMED",
        message="These hours were hard to read. Confirm them to count this record.",
        field="hours",
    )
    return record.model_copy(update={"flags": [*record.flags, flag]})


@router.post("/validate", response_model=ValidateResponse)
def validate(body: ValidateRequest) -> ValidateResponse:
    return ValidateResponse(records=[_flag_low_hours(r) for r in body.records], rules_version=accessors.rules_version())
