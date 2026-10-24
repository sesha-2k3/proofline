"""Generate the 7 synthetic Jorge Ramos sample PDFs and ground truth (BUILD_PLAN.md B6).

Synthetic data only. Layouts follow BUILD_PLAN.md Appendix "Synthetic layouts":
one "Label: value" per line so the offline template parser can read them.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.mocks.jorge import JORGE_NOTICE, JORGE_RECORDS, JORGE_SAMPLES, REQUEST_SUMMARY

BANNER = "SAMPLE — SYNTHETIC — NOT A REAL DOCUMENT"
FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
MARGIN = 54
BODY_SIZE = 11
MIN_SIZE = 7

SAMPLES_DIR = BACKEND_DIR / "samples"
GROUND_TRUTH_PATH = BACKEND_DIR / "synthetic" / "ground_truth.json"


def _quickdash(mm: str, last_day: str, hours: str, gross: str, expenses: str, stmt: str) -> list[str]:
    return [
        "Driver: Jorge Ramos",
        f"Period: {mm}/01/2027 - {mm}/{last_day}/2027",
        f"Active hours: {hours}",
        f"Gross earnings: {gross}",
        f"Expenses (mileage): {expenses}",
        f"Statement date: {stmt}",
    ]


def _bakery(mm: str, last_day: str, hours: str, date: str) -> list[str]:
    return [
        "Employer: Ramos Family Bakery",
        "Worker: Jorge Ramos",
        f"Period: {mm}/01/2027 - {mm}/{last_day}/2027",
        f"Hours worked: {hours}",
        "Pay: Unpaid ($0.00)",
        "Signed: Ana Ramos, Owner",
        f"Date: {date}",
    ]


# filename -> (title, labeled lines)
DOCUMENTS: dict[str, tuple[str, list[str]]] = {
    "rfi_notice.pdf": (
        "MassHealth Request for Information (SAMPLE)",
        [
            "Member: Jorge Ramos",
            "Notice date: 06/10/2027",
            "Respond by: 07/12/2027",
            f"Request: {REQUEST_SUMMARY}",
        ],
    ),
    "quickdash_2027-04.pdf": (
        "QuickDash Driver Earnings Summary",
        _quickdash("04", "30", "14.00", "$320.00", "$110.00", "05/01/2027"),
    ),
    "quickdash_2027-05.pdf": (
        "QuickDash Driver Earnings Summary",
        _quickdash("05", "31", "31.50", "$560.00", "$210.00", "06/01/2027"),
    ),
    "bakery_statement_2027-04.pdf": (
        "Statement of Hours Worked",
        _bakery("04", "30", "20.00", "05/02/2027"),
    ),
    "bakery_statement_2027-05.pdf": (
        "Statement of Hours Worked",
        _bakery("05", "31", "26.00", "06/02/2027"),
    ),
    "pantry_letter.pdf": (
        "Volunteer Service Letter",
        [
            "Organization: Eastside Community Food Pantry",
            "Organization type: 501(c)(3) nonprofit, non-partisan",
            "Volunteer: Jorge Ramos",
            "April 2027 hours: 10.00",
            "May 2027 hours: 24.00 [handwritten, partially illegible]",
            "Date: 06/05/2027",
        ],
    ),
    "harbor_cafe_paystub.pdf": (
        "Harbor Cafe Pay Stub",
        [
            "Employee: Jorge Ramos",
            "Pay period: 05/24/2027 - 06/06/2027",
            "Hours: 20.00",
            "Rate: $15.50",
            "Gross pay: $310.00",
            "Pay date: 06/07/2027",
        ],
    ),
}


def _fit_size(text: str, font: str, size: float, width: float) -> float:
    """Shrink the font so the whole line fits on one line (keeps one label per line)."""
    while size > MIN_SIZE and stringWidth(text, font, size) > width:
        size -= 0.5
    return size


def write_pdf(path: Path, title: str, lines: list[str]) -> None:
    page_w, page_h = letter
    usable = page_w - 2 * MARGIN
    c = canvas.Canvas(str(path), pagesize=letter, invariant=1)
    c.setTitle(title)
    c.setAuthor("Proofline synthetic generator")
    y = page_h - MARGIN

    c.setFont(FONT_BOLD, 10)
    c.drawString(MARGIN, y, BANNER)
    y -= 36

    c.setFont(FONT_BOLD, 16)
    c.drawString(MARGIN, y, title)
    y -= 32

    for line in lines:
        size = _fit_size(line, FONT, BODY_SIZE, usable)
        c.setFont(FONT, size)
        c.drawString(MARGIN, y, line)
        y -= 22

    c.showPage()
    c.save()


def ground_truth() -> dict:
    """Records and notice per sample file, from app/mocks/jorge.py."""
    files: dict[str, dict] = {}
    for sample in JORGE_SAMPLES:
        records = [r for r in JORGE_RECORDS if r.doc_id == sample.name]
        notice = JORGE_NOTICE if sample.doc_type == "rfi_notice" else None
        files[sample.name] = {
            "docType": sample.doc_type,
            "records": [r.model_dump(by_alias=True, mode="json") for r in records],
            "notice": notice.model_dump(by_alias=True, mode="json") if notice else None,
        }
    return {"files": files}


def generate(samples_dir: Path = SAMPLES_DIR, truth_path: Path = GROUND_TRUTH_PATH) -> list[Path]:
    samples_dir.mkdir(parents=True, exist_ok=True)
    truth_path.parent.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, (title, lines) in DOCUMENTS.items():
        path = samples_dir / name
        write_pdf(path, title, lines)
        written.append(path)
    truth_path.write_text(json.dumps(ground_truth(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return written


def main() -> None:
    written = generate()
    for path in written:
        print(f"wrote {path.relative_to(BACKEND_DIR)}")
    print(f"wrote {GROUND_TRUTH_PATH.relative_to(BACKEND_DIR)}")


if __name__ == "__main__":
    main()
