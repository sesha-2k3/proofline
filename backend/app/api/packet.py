"""POST /packet: evidence packet PDF built in memory (B11)."""
from fastapi import APIRouter
from fastapi.responses import Response

from app.api._pdf import PDF_RESPONSES, pdf_response
from app.packet.packet import build_packet
from app.schemas.api import PacketRequest

router = APIRouter(tags=["packet"])


@router.post("/packet", response_class=Response, responses=PDF_RESPONSES)
def packet(body: PacketRequest) -> Response:
    month = body.evaluation.best_month or "none"
    return pdf_response(build_packet(body), f"proofline-packet-{month}.pdf")
