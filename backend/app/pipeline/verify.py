"""Verify stage (BUILD_PLAN Appendix "Verification").

1. Grounding against the page text layer -> "grounded" | "ungrounded" | "not_checked".
2. Date sanity (DATE_SANITY_MIN..DATE_SANITY_MAX, periodStart <= periodEnd).
3. Arithmetic: |hours x rate - gross| > 2% of gross -> ARITHMETIC_MISMATCH.
4. Final confidence: low if the extractor said low, the value is null, or a check failed.
Code checks what the reader extracted; it never decides eligibility.
"""
import calendar
import re
from dataclasses import dataclass, field
from datetime import date

from app.pipeline.render import PageContent
from app.schemas.common import (
    BoolField,
    DateField,
    NumField,
    OrgTypeField,
    StrField,
)
from app.schemas.evidence import EvidenceRecord, Flag, FlagCode, NoticeInfo

DATE_SANITY_MIN = "2025-01-01"
DATE_SANITY_MAX = "2028-12-31"
ARITHMETIC_TOLERANCE_PCT = 2

AnyField = StrField | NumField | BoolField | DateField | OrgTypeField

MONEY_FIELDS = ("hourly_rate_cents", "gross_cents", "expenses_cents")
NUMBER_FIELDS = ("hours",)
DATE_FIELDS = ("period_start", "period_end", "document_date")
STRING_FIELDS = ("person_name", "issuer")
SOURCE_LINE_FIELDS = ("org_type", "non_partisan", "half_time_enrolled")
RECORD_FIELDS = (
    STRING_FIELDS + SOURCE_LINE_FIELDS + DATE_FIELDS + NUMBER_FIELDS + MONEY_FIELDS
)


def _wire(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(p.title() for p in rest)


def _norm(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------- candidates
def number_candidates(value: float) -> list[str]:
    """24 -> "24.00", "24.0", "24"; 31.5 -> "31.50", "31.5"."""
    out = [f"{value:.2f}", f"{value:.1f}" if round(value, 1) == value else None]
    if value == int(value):
        out.append(str(int(value)))
    return [c for c in dict.fromkeys(out) if c]


def money_candidates(cents: float) -> list[str]:
    """56000 -> "$560.00", "560.00", "560" (and comma forms like "$1,234.00")."""
    dollars = cents / 100
    out = [f"${dollars:,.2f}", f"${dollars:.2f}", f"{dollars:,.2f}", f"{dollars:.2f}"]
    if cents % 100 == 0:
        out += [f"${int(dollars):,}", f"{int(dollars):,}", str(int(dollars))]
    return list(dict.fromkeys(out))


def date_candidates(iso: str, month_label: bool = False) -> list[str]:
    """"2027-05-01" -> "2027-05-01", "05/01/2027", "5/1/2027", "May 1, 2027".
    month_label: a period date on the first/last day of a month also matches
    "May 2027" (volunteer letters list hours per month)."""
    d = date.fromisoformat(iso)
    month = calendar.month_name[d.month]
    out = [
        iso,
        d.strftime("%m/%d/%Y"),
        f"{d.month}/{d.day}/{d.year}",
        f"{month} {d.day}, {d.year}",
        f"{month} {d.day:02d}, {d.year}",
    ]
    last_day = calendar.monthrange(d.year, d.month)[1]
    if month_label and d.day in (1, last_day):
        out.append(f"{month} {d.year}")
    return list(dict.fromkeys(out))


def _numeric_pattern(candidate: str) -> re.Pattern[str]:
    """Match a number/date token without matching inside a longer number."""
    return re.compile(rf"(?<![\d.,/-]){re.escape(candidate)}(?!\d|[.,]\d|/\d)")


# ---------------------------------------------------------------- grounding
@dataclass
class _Page:
    lines: list[str]  # stripped original lines

    @classmethod
    def of(cls, page: PageContent) -> "_Page":
        return cls([ln.strip() for ln in page.text.splitlines() if ln.strip()])

    def find_line(
        self, candidates: list[str], numeric: bool, preferred: str | None
    ) -> str | None:
        ordered = self.lines
        if preferred is not None:
            pref = _norm(preferred)
            ordered = sorted(self.lines, key=lambda ln: _norm(ln) != pref)
        for line in ordered:
            text = _norm(line)
            for cand in candidates:
                if numeric:
                    if _numeric_pattern(cand).search(text):
                        return line
                elif cand.lower() in text.lower():
                    return line
        return None

    def has_line(self, evidence: str | None) -> str | None:
        if not evidence:
            return None
        target = _norm(evidence).lower()
        for line in self.lines:
            if target in _norm(line).lower():
                return line
        return None


def _candidates(name: str, f: AnyField) -> tuple[list[str], bool] | None:
    """(candidates, numeric) for value fields; None for source-line fields."""
    v = f.value
    if name in MONEY_FIELDS:
        return money_candidates(float(v)), True  # type: ignore[arg-type]
    if name in NUMBER_FIELDS:
        return number_candidates(float(v)), True  # type: ignore[arg-type]
    if name in DATE_FIELDS or name in ("notice_date", "response_deadline"):
        month_label = name in ("period_start", "period_end")
        return date_candidates(str(v), month_label), True
    if name in STRING_FIELDS or name == "request_summary":
        return [_norm(str(v))], False
    return None


def ground_field(name: str, f: AnyField, pages: dict[int, _Page]) -> AnyField:
    """Set verification and evidence. Ungrounded -> confidence low."""
    page = pages.get(f.page)
    if page is None or not page.lines or f.value is None:
        return f.model_copy(update={"verification": "not_checked"})
    spec = _candidates(name, f)
    if spec is None:
        line = page.has_line(f.evidence)
    else:
        line = page.find_line(spec[0], spec[1], f.evidence)
    if line is None:
        return f.model_copy(update={"verification": "ungrounded", "confidence": "low"})
    return f.model_copy(update={"verification": "grounded", "evidence": line})


# ---------------------------------------------------------------- checks
def date_out_of_range(iso: str | None) -> bool:
    return iso is not None and not (DATE_SANITY_MIN <= iso <= DATE_SANITY_MAX)


def arithmetic_mismatch(hours: float, rate_cents: float, gross_cents: float) -> bool:
    """Integer math: hours in hundredths x rate (cents) vs gross (cents) x 100."""
    computed = round(hours * 100) * round(rate_cents)
    expected = round(gross_cents) * 100
    return abs(computed - expected) * 100 > ARITHMETIC_TOLERANCE_PCT * expected


@dataclass
class VerifyReport:
    grounded: int = 0
    ungrounded: int = 0
    not_checked: int = 0
    flags: int = 0
    notes: list[str] = field(default_factory=list)

    def count(self, f: AnyField) -> None:
        if f.verification == "grounded":
            self.grounded += 1
        elif f.verification == "ungrounded":
            self.ungrounded += 1
        else:
            self.not_checked += 1

    @property
    def detail(self) -> str:
        return (
            f"{self.grounded} grounded, {self.ungrounded} ungrounded, "
            f"{self.not_checked} not checked, {self.flags} flags"
        )


def _flag(code: FlagCode, name: str, message: str) -> Flag:
    return Flag(code=code, message=message, field=_wire(name))


def _lower(f: AnyField) -> AnyField:
    return f.model_copy(update={"confidence": "low"})


def _calibrate(f: AnyField) -> AnyField:
    """Rule 4: null values are low; otherwise keep the (possibly lowered) confidence."""
    return _lower(f) if f.value is None else f


def verify_record(
    record: EvidenceRecord, pages: dict[int, _Page], report: VerifyReport
) -> EvidenceRecord:
    fields: dict[str, AnyField] = {}
    flags = list(record.flags)
    for name in RECORD_FIELDS:
        f = getattr(record, name)
        if f is None:
            continue
        f = ground_field(name, f, pages)
        if f.verification == "ungrounded":
            flags.append(
                _flag("UNGROUNDED_VALUE", name, "This value was not found on the page.")
            )
        fields[name] = f

    for name in DATE_FIELDS:
        if date_out_of_range(fields[name].value):  # type: ignore[arg-type]
            fields[name] = _lower(fields[name])
            flags.append(
                _flag("DATE_OUT_OF_RANGE", name, "This date is outside the expected range.")
            )
    start, end = fields["period_start"].value, fields["period_end"].value
    if start is not None and end is not None and start > end:
        fields["period_start"] = _lower(fields["period_start"])
        fields["period_end"] = _lower(fields["period_end"])
        flags.append(
            _flag("DATE_OUT_OF_RANGE", "period_end", "The period ends before it starts.")
        )

    hours, rate, gross = (fields.get(n) for n in ("hours", "hourly_rate_cents", "gross_cents"))
    if (
        hours is not None and rate is not None and gross is not None
        and None not in (hours.value, rate.value, gross.value)
        and arithmetic_mismatch(hours.value, rate.value, gross.value)  # type: ignore[arg-type]
    ):
        fields["gross_cents"] = _lower(gross)
        flags.append(
            _flag(
                "ARITHMETIC_MISMATCH",
                "gross_cents",
                "Hours times rate does not match the gross pay.",
            )
        )

    fields = {n: _calibrate(f) for n, f in fields.items()}
    for f in fields.values():
        report.count(f)
    report.flags += len(flags) - len(record.flags)
    return record.model_copy(update={**fields, "flags": flags})


def verify_notice(
    notice: NoticeInfo, pages: dict[int, _Page], report: VerifyReport
) -> NoticeInfo:
    """Notices have no flags; failed checks lower confidence and add a report note."""
    fields: dict[str, AnyField] = {}
    for name in ("notice_date", "response_deadline", "request_summary"):
        f = getattr(notice, name)
        if f is None:
            continue
        f = ground_field(name, f, pages)
        if name != "request_summary" and date_out_of_range(f.value):  # type: ignore[arg-type]
            f = _lower(f)
            report.notes.append(f"{_wire(name)} is outside the expected range.")
        if f.verification == "ungrounded":
            report.notes.append(f"{_wire(name)} was not found on the page.")
        f = _calibrate(f)
        report.count(f)
        fields[name] = f
    return notice.model_copy(update=fields)


def verify(
    records: list[EvidenceRecord],
    notice: NoticeInfo | None,
    pages: list[PageContent],
) -> tuple[list[EvidenceRecord], NoticeInfo | None, VerifyReport]:
    by_page = {p.page: _Page.of(p) for p in pages}
    report = VerifyReport()
    checked = [verify_record(r, by_page, report) for r in records]
    checked_notice = verify_notice(notice, by_page, report) if notice else None
    return checked, checked_notice, report
