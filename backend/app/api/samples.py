from fastapi import APIRouter

from app.mocks.jorge import JORGE_CASE, JORGE_SAMPLES
from app.rules import accessors
from app.schemas.api import SamplesResponse

router = APIRouter(tags=["samples"])


@router.get("/samples", response_model=SamplesResponse)
def get_samples() -> SamplesResponse:
    return SamplesResponse(files=JORGE_SAMPLES, case_info=JORGE_CASE, rules_version=accessors.rules_version())
