from fastapi.responses import Response

PDF_RESPONSES: dict = {200: {"content": {"application/pdf": {}}, "description": "PDF file"}}


def pdf_response(content: bytes, filename: str) -> Response:
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
