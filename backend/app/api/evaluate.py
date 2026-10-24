"""Mock POST /evaluate (B4). Replaced by the ledger and reporting in B10."""

from fastapi import APIRouter

from app.mocks.jorge import EVAL_AFTER, EVAL_BEFORE, SUMMARIES
from app.rules import accessors
from app.schemas.api import EvaluateRequest, EvaluateResponse
from app.settings import get_settings

router = APIRouter(tags=["evaluate"])


def _pantry_may_confirmed(body: EvaluateRequest) -> bool:
    for r in body.records:
        if r.doc_type == "volunteer_letter" and r.period_start.value == "2027-05-01":
            return r.hours is not None and r.hours.confirmed
    return False


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest) -> EvaluateResponse:
    key = "after" if _pantry_may_confirmed(body) else "before"
    base = EVAL_AFTER if key == "after" else EVAL_BEFORE
    yes = {a.id for a in body.exemption_answers if a.answer}
    return base.model_copy(
        update={
            "possible_exemptions": [e for e in accessors.exemptions() if e.id in yes],
            "summary": SUMMARIES[key][body.case_info.lang],
            "demo_mode": get_settings().demo_mode,
        },
        deep=True,
    )
