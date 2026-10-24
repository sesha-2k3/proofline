"""Render stage: per-page text layer and (optionally) page images as PNG bytes."""

import io
from dataclasses import dataclass

import pypdfium2 as pdfium
from PIL import Image

from app.pipeline.ingest import IngestedFile

RENDER_SCALE = 2


@dataclass(frozen=True)
class PageContent:
    page: int
    text: str
    image_png: bytes | None


def render(file: IngestedFile, with_images: bool) -> list[PageContent]:
    """PDF: text per page, images only when with_images. Image: no text, always a PNG."""
    if file.kind == "image":
        return [PageContent(page=1, text="", image_png=_to_png(file.data))]

    pdf = pdfium.PdfDocument(file.data)
    try:
        pages: list[PageContent] = []
        for i in range(len(pdf)):
            page = pdf[i]
            text = page.get_textpage().get_text_range()
            image_png = None
            if with_images:
                buf = io.BytesIO()
                page.render(scale=RENDER_SCALE).to_pil().save(buf, format="PNG")
                image_png = buf.getvalue()
            pages.append(PageContent(page=i + 1, text=text, image_png=image_png))
        return pages
    finally:
        pdf.close()


def _to_png(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        if img.mode not in {"RGB", "RGBA", "L"}:
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
