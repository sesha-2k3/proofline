"""POST /validate: cross-document checks (validation/checks.py)."""

from fastapi import APIRouter

from app.rules import accessors
from app.schemas.api import ValidateRequest, ValidateResponse
from app.validation.checks import validate_records

router = APIRouter(tags=["validate"])


@router.post("/validate", response_model=ValidateResponse)
def validate(body: ValidateRequest) -> ValidateResponse:
    return ValidateResponse(
        records=validate_records(body.case_info, body.records),
        rules_version=accessors.rules_version(),
    )
