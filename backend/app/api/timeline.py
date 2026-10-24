"""Mock POST /timeline (B4). Replaced by packet/timeline.py in B11."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.api._pdf import PDF_RESPONSES, mock_pdf_response
from app.schemas.api import TimelineRequest

router = APIRouter(tags=["timeline"])


@router.post("/timeline", response_class=Response, responses=PDF_RESPONSES)
def timeline(body: TimelineRequest) -> Response:
    return mock_pdf_response("proofline-submission-record.pdf")
