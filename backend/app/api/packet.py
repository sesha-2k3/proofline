"""Mock POST /packet (B4). Replaced by packet/packet.py in B11."""

from fastapi import APIRouter
from fastapi.responses import Response

from app.api._pdf import PDF_RESPONSES, mock_pdf_response
from app.schemas.api import PacketRequest

router = APIRouter(tags=["packet"])


@router.post("/packet", response_class=Response, responses=PDF_RESPONSES)
def packet(body: PacketRequest) -> Response:
    month = body.evaluation.best_month or "none"
    return mock_pdf_response(f"proofline-packet-{month}.pdf")
