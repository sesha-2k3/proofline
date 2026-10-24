"""Render stage: per-page text layer, text line boxes, and page images as PNG bytes."""

import io
from dataclasses import dataclass, field

import pypdfium2 as pdfium
from PIL import Image

from app.pipeline.ingest import IngestedFile

RENDER_SCALE = 2  # LLM vision input
PREVIEW_SCALE = 1  # Source_View preview image (a render setting, not an eligibility value)

Box = tuple[float, float, float, float]  # x0, y0, x1, y1 as top-left page fractions

# Characters str.splitlines() treats as line boundaries, so lines match verify._Page.
_LINE_BREAKS = frozenset("\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029")


@dataclass(frozen=True)
class PageContent:
    page: int
    text: str
    image_png: bytes | None
    lines: list[tuple[str, Box]] = field(default_factory=list)
    preview_png: bytes | None = None


def render(file: IngestedFile, with_images: bool) -> list[PageContent]:
    """PDF: text, line boxes and a preview per page; LLM images only when with_images.
    Image upload: one page, no text or lines, the PNG serves as both image and preview."""
    if file.kind == "image":
        png = _to_png(file.data)
        return [PageContent(page=1, text="", image_png=png, preview_png=png)]

    pdf = pdfium.PdfDocument(file.data)
    try:
        pages: list[PageContent] = []
        for i in range(len(pdf)):
            page = pdf[i]
            textpage = page.get_textpage()
            text = textpage.get_text_range()
            width, height = page.get_size()
            lines = line_boxes(textpage, width, height)
            image_png = _render_png(page, RENDER_SCALE) if with_images else None
            preview_png = _render_png(page, PREVIEW_SCALE)
            pages.append(
                PageContent(
                    page=i + 1,
                    text=text,
                    image_png=image_png,
                    lines=lines,
                    preview_png=preview_png,
                )
            )
        return pages
    finally:
        pdf.close()


def line_boxes(textpage: "pdfium.PdfTextPage", width: float, height: float) -> list[tuple[str, Box]]:
    """Split the text layer at line breaks and union the char boxes of each line.

    Line texts are stripped and empty lines dropped, the same way verify._Page derives lines.
    Boxes are converted from PDF points (bottom-left origin) to top-left fractions in [0, 1].
    """
    n = textpage.count_chars()
    full = textpage.get_text_range()
    if len(full) == n:
        chars = list(full)
    else:  # text and char indices disagree; read each char by index
        chars = [textpage.get_text_range(i, 1) or " " for i in range(n)]

    result: list[tuple[str, Box]] = []
    buf: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []

    def flush() -> None:
        line = "".join(buf).strip()
        if line:
            result.append((line, _to_fraction(boxes, width, height)))
        buf.clear()
        boxes.clear()

    for i, ch in enumerate(chars):
        if ch in _LINE_BREAKS:
            flush()
            continue
        buf.append(ch)
        if not ch.isspace():
            boxes.append(textpage.get_charbox(i))
    flush()
    return result


def _to_fraction(boxes: list[tuple[float, float, float, float]], width: float, height: float) -> Box:
    if not boxes or width <= 0 or height <= 0:
        return (0.0, 0.0, 0.0, 0.0)
    left = min(b[0] for b in boxes)
    bottom = min(b[1] for b in boxes)
    right = max(b[2] for b in boxes)
    top = max(b[3] for b in boxes)
    x0, x1 = _clamp(left / width), _clamp(right / width)
    y0, y1 = _clamp((height - top) / height), _clamp((height - bottom) / height)
    return (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def _render_png(page: "pdfium.PdfPage", scale: float) -> bytes:
    buf = io.BytesIO()
    page.render(scale=scale).to_pil().save(buf, format="PNG")
    return buf.getvalue()


def _to_png(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as img:
        if img.mode not in {"RGB", "RGBA", "L"}:
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
