"""Offline template extractor for the synthetic sample layouts (BUILD_PLAN Appendix).

Each layout is one "Label: value" per line. Values are returned raw (as printed).
Confidence is "high", except values on a line containing "[handwritten" -> "low".
Each field keeps its page and the matched line as evidence.
"""

import calendar
import re
from collections.abc import Callable
from dataclasses import dataclass

from app.pipeline.extract.models import RawExtraction, RawField, RawNotice, RawRecord
from app.pipeline.render import PageContent
from app.schemas.common import DocType

HANDWRITTEN_MARK = "[handwritten"
_MONEY = r"(\$[\d,]+(?:\.\d{2})?)"
_NUM = r"(\d+(?:\.\d+)?)"
_RANGE = r"(\S+)\s*-\s*(\S+)"


@dataclass(frozen=True)
class _Line:
    page: int
    text: str


class _Doc:
    def __init__(self, pages: list[PageContent]):
        self.lines = [
            _Line(p.page, line.strip())
            for p in pages
            for line in p.text.splitlines()
            if line.strip()
        ]

    def find(self, pattern: str) -> tuple[re.Match[str], _Line] | None:
        regex = re.compile(pattern)
        for line in self.lines:
            m = regex.search(line.text)
            if m:
                return m, line
        return None

    def find_all(self, pattern: str) -> list[tuple[re.Match[str], _Line]]:
        regex = re.compile(pattern)
        return [(m, line) for line in self.lines if (m := regex.search(line.text))]


def _field(
    value: str | float | bool | None, line: _Line, from_label: bool = False
) -> RawField:
    """from_label: value comes from the printed label (e.g. "May 2027"), not the
    handwritten value, so the handwritten mark does not lower it."""
    handwritten = HANDWRITTEN_MARK in line.text and not from_label
    confidence = "low" if handwritten else "high"
    return RawField(
        value=value, confidence=confidence, page=line.page, evidence=line.text
    )


def _group(doc: _Doc, pattern: str, group: int = 1) -> RawField | None:
    hit = doc.find(pattern)
    if hit is None:
        return None
    m, line = hit
    return _field(m.group(group).strip(), line)


def _range(doc: _Doc, pattern: str) -> tuple[RawField | None, RawField | None]:
    hit = doc.find(pattern)
    if hit is None:
        return None, None
    m, line = hit
    return _field(m.group(1), line), _field(m.group(2), line)


def _record_or_none(record: RawRecord) -> RawExtraction | None:
    """A layout matches only if the person and period were found."""
    if record.person_name is None or record.period_start is None:
        return None
    return RawExtraction(records=[record])


def _rfi_notice(doc: _Doc) -> RawExtraction | None:
    notice = RawNotice(
        notice_date=_group(doc, r"^Notice date:\s*(.+)$"),
        response_deadline=_group(doc, r"^Respond by:\s*(.+)$"),
        request_summary=_group(doc, r"^Request:\s*(.+)$"),
    )
    if notice.notice_date is None or notice.request_summary is None:
        return None
    return RawExtraction(notice=notice)


def _gig_earnings(doc: _Doc) -> RawExtraction | None:
    start, end = _range(doc, rf"^Period:\s*{_RANGE}$")
    return _record_or_none(
        RawRecord(
            issuer=_group(doc, r"^(.+?)\s+Driver Earnings Summary$"),
            person_name=_group(doc, r"^Driver:\s*(.+)$"),
            period_start=start,
            period_end=end,
            hours=_group(doc, rf"^Active hours:\s*{_NUM}"),
            gross_cents=_group(doc, rf"^Gross earnings:\s*{_MONEY}"),
            expenses_cents=_group(doc, rf"^Expenses(?:\s*\([^)]*\))?:\s*{_MONEY}"),
            document_date=_group(doc, r"^Statement date:\s*(\S+)"),
        )
    )


def _employer_statement(doc: _Doc) -> RawExtraction | None:
    if doc.find(r"^Statement of Hours Worked") is None:
        return None
    start, end = _range(doc, rf"^Period:\s*{_RANGE}$")
    return _record_or_none(
        RawRecord(
            issuer=_group(doc, r"^Employer:\s*(.+)$"),
            person_name=_group(doc, r"^Worker:\s*(.+)$"),
            period_start=start,
            period_end=end,
            hours=_group(doc, rf"^Hours worked:\s*{_NUM}"),
            gross_cents=_group(doc, rf"^Pay:.*?{_MONEY}"),
            document_date=_group(doc, r"^Date:\s*(\S+)"),
        )
    )


def _org_type(text: str) -> str:
    lowered = text.lower()
    if "nonprofit" in lowered or "non-profit" in lowered or "501(c)(3)" in lowered:
        return "nonprofit"
    if "political" in lowered:
        return "political"
    if "for-profit" in lowered or "for profit" in lowered:
        return "for_profit"
    if "public" in lowered or "government" in lowered:
        return "public"
    return "unknown"


def _non_partisan(text: str) -> bool | None:
    lowered = text.lower()
    if "non-partisan" in lowered or "nonpartisan" in lowered:
        return True
    if "partisan" in lowered:
        return False
    return None


_MONTHS = {name: i for i, name in enumerate(calendar.month_name) if name}


def _volunteer_letter(doc: _Doc) -> RawExtraction | None:
    issuer = _group(doc, r"^Organization:\s*(.+)$")
    person = _group(doc, r"^Volunteer:\s*(.+)$")
    document_date = _group(doc, r"^Date:\s*(\S+)")
    org_type = non_partisan = None
    hit = doc.find(r"^Organization type:\s*(.+)$")
    if hit is not None:
        m, line = hit
        org_type = _field(_org_type(m.group(1)), line)
        np_value = _non_partisan(m.group(1))
        non_partisan = _field(np_value, line) if np_value is not None else None

    records: list[RawRecord] = []
    for m, line in doc.find_all(rf"^([A-Z][a-z]+)\s+(\d{{4}})\s+hours:\s*{_NUM}"):
        month = _MONTHS.get(m.group(1))
        if month is None:
            continue
        year = int(m.group(2))
        last_day = calendar.monthrange(year, month)[1]
        records.append(
            RawRecord(
                issuer=issuer,
                person_name=person,
                org_type=org_type,
                non_partisan=non_partisan,
                period_start=_field(
                    f"{year:04d}-{month:02d}-01", line, from_label=True
                ),
                period_end=_field(
                    f"{year:04d}-{month:02d}-{last_day:02d}", line, from_label=True
                ),
                hours=_field(m.group(3), line),
                document_date=document_date,
            )
        )
    if person is None or not records:
        return None
    return RawExtraction(records=records)


def _paystub(doc: _Doc) -> RawExtraction | None:
    start, end = _range(doc, rf"^Pay period:\s*{_RANGE}$")
    return _record_or_none(
        RawRecord(
            issuer=_group(doc, r"^(.+?)\s+Pay Stub$"),
            person_name=_group(doc, r"^Employee:\s*(.+)$"),
            period_start=start,
            period_end=end,
            hours=_group(doc, rf"^Hours:\s*{_NUM}"),
            hourly_rate_cents=_group(doc, rf"^Rate:\s*{_MONEY}"),
            gross_cents=_group(doc, rf"^Gross pay:\s*{_MONEY}"),
            document_date=_group(doc, r"^Pay date:\s*(\S+)"),
        )
    )


_PARSERS: dict[DocType, Callable[[_Doc], RawExtraction | None]] = {
    "rfi_notice": _rfi_notice,
    "gig_earnings": _gig_earnings,
    "employer_statement": _employer_statement,
    "volunteer_letter": _volunteer_letter,
    "paystub": _paystub,
}


def extract_template(
    doc_type: DocType, pages: list[PageContent]
) -> RawExtraction | None:
    """Parse a known synthetic layout. None when the text does not match the layout."""
    parser = _PARSERS.get(doc_type)
    if parser is None or not any(p.text.strip() for p in pages):
        return None
    return parser(_Doc(pages))
