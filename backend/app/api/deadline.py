"""POST /deadline: RFI response deadline for a case (reporting/deadline.py)."""

from fastapi import APIRouter

from app.reporting.deadline import response_deadline
from app.rules import accessors
from app.schemas.api import DeadlineRequest, DeadlineResponse

router = APIRouter(tags=["deadline"])


@router.post("/deadline", response_model=DeadlineResponse)
def deadline(body: DeadlineRequest) -> DeadlineResponse:
    return DeadlineResponse(
        deadline=response_deadline(body.case_info),
        rules_version=accessors.rules_version(),
    )
