"""POST /timeline: submission record PDF built in memory (B11)."""
from fastapi import APIRouter
from fastapi.responses import Response

from app.api._pdf import PDF_RESPONSES, pdf_response
from app.packet.timeline import build_timeline
from app.schemas.api import TimelineRequest

router = APIRouter(tags=["timeline"])


@router.post("/timeline", response_class=Response, responses=PDF_RESPONSES)
def timeline(body: TimelineRequest) -> Response:
    return pdf_response(build_timeline(body), "proofline-submission-record.pdf")
