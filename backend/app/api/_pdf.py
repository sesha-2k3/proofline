from io import BytesIO

from fastapi.responses import Response
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

PDF_RESPONSES: dict = {200: {"content": {"application/pdf": {}}, "description": "PDF file"}}


def mock_pdf_response(filename: str) -> Response:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 18)
    c.drawString(72, 700, "Mock PDF")
    c.showPage()
    c.save()
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
