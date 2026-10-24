"""Shared reportlab building blocks for the packet and submission record (in memory only)."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Table, TableStyle

_BASE = getSampleStyleSheet()
TITLE = ParagraphStyle("PLTitle", parent=_BASE["Title"], fontName="Helvetica-Bold", fontSize=18)
H2 = ParagraphStyle("PLH2", parent=_BASE["Heading2"], fontName="Helvetica-Bold", fontSize=13, spaceBefore=10)
BODY = ParagraphStyle("PLBody", parent=_BASE["BodyText"], fontName="Helvetica", fontSize=10, leading=13)
CELL = ParagraphStyle("PLCell", parent=BODY, fontSize=8, leading=10)
CELL_HEAD = ParagraphStyle("PLCellHead", parent=CELL, fontName="Helvetica-Bold")
NOTE = ParagraphStyle("PLNote", parent=BODY, fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#333333"))

PAGE_WIDTH = letter[0] - 1.5 * inch


def p(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    """Paragraph with untrusted text escaped for reportlab's mini-markup."""
    return Paragraph(escape(text), style)


def label_value(label: str, value: str) -> Paragraph:
    return Paragraph(f"<b>{escape(label)}:</b> {escape(value)}", BODY)


def table(header: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[p(h, CELL_HEAD) for h in header]] + [[p(c, CELL) for c in row] for row in rows]
    t = Table(data, colWidths=[w * PAGE_WIDTH for w in widths], repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF4")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return t


def build_pdf(title: str, story: list[Flowable]) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        title=title,
        author="Proofline",
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    doc.build(story)
    return buf.getvalue()


CASE_TYPE_LABELS = {"renewal": "Renewal", "new_application": "New application"}
