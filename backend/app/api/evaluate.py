"""POST /evaluate: validation -> ledger -> deadline, exemptions, gaps, summary. Code decides; the LLM may only reword the summary."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.documents import get_llm_client
from app.ledger.evaluate import evaluate_case
from app.pipeline.extract.llm import LlmClient
from app.reporting.deadline import response_deadline
from app.reporting.exemptions import possible_exemptions
from app.reporting.gaps import build_gaps
from app.reporting.summary import build_summary
from app.rules import accessors
from app.schemas.api import EvaluateRequest, EvaluateResponse
from app.settings import get_settings
from app.validation.checks import validate_records

router = APIRouter(tags=["evaluate"])


@router.post("/evaluate", response_model=EvaluateResponse)
def evaluate(
    body: EvaluateRequest,
    llm: Annotated[LlmClient | None, Depends(get_llm_client)],
) -> EvaluateResponse:
    case = body.case_info
    records = validate_records(case, body.records)
    months, best = evaluate_case(case, records)
    deadline = response_deadline(case)
    return EvaluateResponse(
        months=months,
        best_month=best,
        deadline=deadline,
        possible_exemptions=possible_exemptions(body.exemption_answers),
        gaps=build_gaps(months, best, records),
        summary=build_summary(months, best, records, deadline, case.lang, llm),
        demo_mode=get_settings().demo_mode,
        rules_version=accessors.rules_version(),
    )
