"""Exact Jorge Ramos scenario data (BUILD_PLAN.md Appendix "Jorge scenario"). Synthetic only."""

from app.rules import accessors
from app.schemas.api import EvaluateResponse, SampleFile
from app.schemas.common import (
    BoolField,
    CaseInfo,
    DateField,
    NumField,
    OrgTypeField,
    StrField,
)
from app.schemas.evidence import EvidenceRecord, NoticeInfo
from app.schemas.ledger import Deadline, GapItem, MonthResult

PERSON = "Jorge Ramos"

JORGE_CASE = CaseInfo(
    client_name=PERSON,
    case_type="renewal",
    window_start="2027-02",
    window_end="2027-06",
    rfi_received_date="2027-06-12",
    lang="en",
)


def _s(value: str, evidence: str) -> StrField:
    return StrField(value=value, confidence="high", page=1, verification="grounded", evidence=evidence)


def _n(value: float, evidence: str, confidence: str = "high") -> NumField:
    return NumField(value=value, confidence=confidence, page=1, verification="grounded", evidence=evidence)


def _d(value: str, evidence: str) -> DateField:
    return DateField(value=value, confidence="high", page=1, verification="grounded", evidence=evidence)


# --- Records -----------------------------------------------------------------

QUICKDASH_APR = "rec-gig_earnings-quickdash-2027-04-01"
QUICKDASH_MAY = "rec-gig_earnings-quickdash-2027-05-01"
BAKERY_APR = "rec-employer_statement-ramos-family-bakery-2027-04-01"
BAKERY_MAY = "rec-employer_statement-ramos-family-bakery-2027-05-01"
PANTRY_APR = "rec-volunteer_letter-eastside-community-food-pantry-2027-04-01"
PANTRY_MAY = "rec-volunteer_letter-eastside-community-food-pantry-2027-05-01"
CAFE = "rec-paystub-harbor-cafe-2027-05-24"


def _quickdash(rec_id: str, mm: str, last_day: str, hours: float, gross: int, expenses: int, doc_date: str) -> EvidenceRecord:
    period_line = f"Period: {mm}/01/2027 - {mm}/{last_day}/2027"
    us_date = f"{doc_date[5:7]}/{doc_date[8:10]}/{doc_date[0:4]}"
    return EvidenceRecord(
        id=rec_id,
        doc_id=f"quickdash_2027-{mm}.pdf",
        doc_type="gig_earnings",
        activity="work",
        person_name=_s(PERSON, f"Driver: {PERSON}"),
        issuer=_s("QuickDash", "QuickDash Driver Earnings Summary"),
        period_start=_d(f"2027-{mm}-01", period_line),
        period_end=_d(f"2027-{mm}-{last_day}", period_line),
        hours=_n(hours, f"Active hours: {hours:.2f}"),
        gross_cents=_n(gross, f"Gross earnings: ${gross / 100:.2f}"),
        expenses_cents=_n(expenses, f"Expenses (mileage): ${expenses / 100:.2f}"),
        document_date=_d(doc_date, f"Statement date: {us_date}"),
    )


def _bakery(rec_id: str, mm: str, last_day: str, hours: float, doc_date: str) -> EvidenceRecord:
    period_line = f"Period: {mm}/01/2027 - {mm}/{last_day}/2027"
    us_date = f"{doc_date[5:7]}/{doc_date[8:10]}/{doc_date[0:4]}"
    return EvidenceRecord(
        id=rec_id,
        doc_id=f"bakery_statement_2027-{mm}.pdf",
        doc_type="employer_statement",
        activity="work",
        person_name=_s(PERSON, f"Worker: {PERSON}"),
        issuer=_s("Ramos Family Bakery", "Employer: Ramos Family Bakery"),
        period_start=_d(f"2027-{mm}-01", period_line),
        period_end=_d(f"2027-{mm}-{last_day}", period_line),
        hours=_n(hours, f"Hours worked: {hours:.2f}"),
        gross_cents=_n(0, "Pay: Unpaid ($0.00)"),
        document_date=_d(doc_date, f"Date: {us_date}"),
    )


def _pantry(rec_id: str, mm: str, last_day: str, month_name: str, hours: float, low: bool) -> EvidenceRecord:
    hours_line = f"{month_name} 2027 hours: {hours:.2f}" + (" [handwritten, partially illegible]" if low else "")
    org_line = "Organization type: 501(c)(3) nonprofit, non-partisan"
    return EvidenceRecord(
        id=rec_id,
        doc_id="pantry_letter.pdf",
        doc_type="volunteer_letter",
        activity="volunteer",
        person_name=_s(PERSON, f"Volunteer: {PERSON}"),
        issuer=_s("Eastside Community Food Pantry", "Organization: Eastside Community Food Pantry"),
        org_type=OrgTypeField(value="nonprofit", confidence="high", page=1, verification="grounded", evidence=org_line),
        non_partisan=BoolField(value=True, confidence="high", page=1, verification="grounded", evidence=org_line),
        period_start=_d(f"2027-{mm}-01", hours_line),
        period_end=_d(f"2027-{mm}-{last_day}", hours_line),
        hours=_n(hours, hours_line, "low" if low else "high"),
        document_date=_d("2027-06-05", "Date: 06/05/2027"),
    )


_cafe_period = "Pay period: 05/24/2027 - 06/06/2027"

JORGE_RECORDS: list[EvidenceRecord] = [
    _quickdash(QUICKDASH_APR, "04", "30", 14.00, 32000, 11000, "2027-05-01"),
    _quickdash(QUICKDASH_MAY, "05", "31", 31.50, 56000, 21000, "2027-06-01"),
    _bakery(BAKERY_APR, "04", "30", 20.00, "2027-05-02"),
    _bakery(BAKERY_MAY, "05", "31", 26.00, "2027-06-02"),
    _pantry(PANTRY_APR, "04", "30", "April", 10.00, low=False),
    _pantry(PANTRY_MAY, "05", "31", "May", 24.00, low=True),
    EvidenceRecord(
        id=CAFE,
        doc_id="harbor_cafe_paystub.pdf",
        doc_type="paystub",
        activity="work",
        person_name=_s(PERSON, f"Employee: {PERSON}"),
        issuer=_s("Harbor Cafe", "Harbor Cafe Pay Stub"),
        period_start=_d("2027-05-24", _cafe_period),
        period_end=_d("2027-06-06", _cafe_period),
        hours=_n(20.00, "Hours: 20.00"),
        hourly_rate_cents=_n(1550, "Rate: $15.50"),
        gross_cents=_n(31000, "Gross pay: $310.00"),
        document_date=_d("2027-06-07", "Pay date: 06/07/2027"),
    ),
]

# --- Notice ------------------------------------------------------------------

REQUEST_SUMMARY = (
    "MassHealth is asking for proof that you met the work and education requirements "
    "for one month between February and June 2027."
)

JORGE_NOTICE = NoticeInfo(
    notice_date=_d("2027-06-10", "Notice date: 06/10/2027"),
    response_deadline=_d("2027-07-12", "Respond by: 07/12/2027"),
    request_summary=_s(REQUEST_SUMMARY, f"Request: {REQUEST_SUMMARY}"),
)

# --- Samples -----------------------------------------------------------------

_SAMPLE_TYPES: list[tuple[str, str]] = [
    ("rfi_notice.pdf", "rfi_notice"),
    ("quickdash_2027-04.pdf", "gig_earnings"),
    ("quickdash_2027-05.pdf", "gig_earnings"),
    ("bakery_statement_2027-04.pdf", "employer_statement"),
    ("bakery_statement_2027-05.pdf", "employer_statement"),
    ("pantry_letter.pdf", "volunteer_letter"),
    ("harbor_cafe_paystub.pdf", "paystub"),
]

JORGE_SAMPLES: list[SampleFile] = [
    SampleFile(name=name, url=f"/samples/{name}", doc_type=doc_type) for name, doc_type in _SAMPLE_TYPES
]

# --- Evaluations -------------------------------------------------------------

_HOURS_H = accessors.hours_threshold_hours()
_INCOME = accessors.income_threshold_cents()


def _fmt_hours(h: float) -> str:
    return f"{h:.2f}".rstrip("0").rstrip(".")


def _month(
    month: str,
    work: float,
    vol: float,
    gross: int,
    net: int,
    counted: list[str],
    excluded: list[str] | None = None,
    status: str = "short",
    paths_met: list[str] | None = None,
    depends: list[str] | None = None,
) -> MonthResult:
    return MonthResult(
        month=month,
        work_hours=work,
        volunteer_hours=vol,
        training_hours=0,
        school_half_time=False,
        gross_income_cents=gross,
        net_income_cents=net,
        status=status,
        paths_met=paths_met or [],
        depends_on_unresolved=depends or [],
        hours_shortfall=round(max(0.0, _HOURS_H - (work + vol)), 2),
        income_shortfall_cents=max(0, _INCOME - gross),
        counted_record_ids=sorted(counted),
        excluded_record_ids=sorted(excluded or []),
    )


_FEB = _month("2027-02", 0, 0, 0, 0, [])
_MAR = _month("2027-03", 0, 0, 0, 0, [])
_APR = _month("2027-04", 34, 10, 32000, 21000, [QUICKDASH_APR, BAKERY_APR, PANTRY_APR])
_JUN = _month("2027-06", 8.57, 0, 13286, 13286, [CAFE])
_MAY_BEFORE = _month(
    "2027-05", 68.93, 0, 73714, 52714, [QUICKDASH_MAY, BAKERY_MAY, CAFE],
    excluded=[PANTRY_MAY], status="conditional",
    depends=["self_employment_income_basis", "pay_period_split_method"],
)
_MAY_AFTER = _month(
    "2027-05", 68.93, 24, 73714, 52714, [QUICKDASH_MAY, BAKERY_MAY, CAFE, PANTRY_MAY],
    status="meets", paths_met=["hours_threshold"],
)


def _hours_gap(m: MonthResult, label: str) -> GapItem:
    return GapItem(
        month=m.month,
        kind="hours",
        message=f"{label} is {_fmt_hours(m.hours_shortfall)} hours short of {_fmt_hours(_HOURS_H)}.",
        suggested_doc_types=["employer_statement", "volunteer_letter", "paystub"],
    )


_HOURS_GAPS = [
    _hours_gap(_APR, "April 2027"),
    _hours_gap(_JUN, "June 2027"),
    _hours_gap(_FEB, "February 2027"),
    _hours_gap(_MAR, "March 2027"),
]

_GAPS_BEFORE = [
    GapItem(
        month="2027-05",
        kind="unconfirmed_record",
        message="The Eastside Community Food Pantry's May hours were hard to read. Confirm the 24 hours to count them.",
        suggested_doc_types=["volunteer_letter"],
    ),
    GapItem(
        month="2027-05",
        kind="unresolved_rule",
        message=(
            f"May's income meets ${_INCOME // 100} only if gig income counts before expenses. "
            "MassHealth has not said which applies."
        ),
        suggested_doc_types=[],
        rule_id="self_employment_income_basis",
    ),
    GapItem(
        month="2027-05",
        kind="unresolved_rule",
        message=(
            "Part of the Harbor Cafe pay period falls in June. "
            "How MassHealth splits pay periods is not published."
        ),
        suggested_doc_types=[],
        rule_id="pay_period_split_method",
    ),
    *_HOURS_GAPS,
]

_H = _fmt_hours(_HOURS_H)

SUMMARIES: dict[str, dict[str, str]] = {
    "before": {
        "en": (
            f"May 2027 is the strongest month. Counted hours: 68.93 of {_H}. "
            "Income is $737.14 before expenses and $527.14 after. "
            "Whether May meets the requirement depends on rules MassHealth has not settled, "
            "and on confirming the Eastside Community Food Pantry's May hours. MassHealth makes the final decision."
        ),
        "es": (
            f"Mayo de 2027 es el mes más fuerte. Horas contadas: 68.93 de {_H}. "
            "Los ingresos son $737.14 antes de gastos y $527.14 después. "
            "Si mayo cumple el requisito depende de reglas que MassHealth aún no ha definido "
            "y de confirmar las horas de mayo de Eastside Community Food Pantry. MassHealth toma la decisión final."
        ),
    },
    "after": {
        "en": (
            "May 2027 is the strongest month. "
            f"The evidence appears to show 92.93 qualifying hours, above the {_H}-hour requirement. "
            "Response deadline: July 12, 2027 (provisional). MassHealth makes the final decision."
        ),
        "es": (
            "Mayo de 2027 es el mes más fuerte. "
            f"La evidencia parece mostrar 92.93 horas que cuentan, más que el requisito de {_H} horas. "
            "Fecha límite para responder: 12 de julio de 2027 (provisional). "
            "MassHealth toma la decisión final."
        ),
    },
}

_DEADLINE = Deadline(
    date="2027-07-12",
    rule_id="rfi_response_days",
    rule_status=accessors.rule_status("rfi_response_days"),
)

EVAL_BEFORE = EvaluateResponse(
    months=[_FEB, _MAR, _APR, _MAY_BEFORE, _JUN],
    best_month="2027-05",
    deadline=_DEADLINE,
    possible_exemptions=[],
    gaps=_GAPS_BEFORE,
    summary=SUMMARIES["before"]["en"],
    demo_mode=True,
    rules_version=accessors.rules_version(),
)

EVAL_AFTER = EvaluateResponse(
    months=[_FEB, _MAR, _APR, _MAY_AFTER, _JUN],
    best_month="2027-05",
    deadline=_DEADLINE,
    possible_exemptions=[],
    gaps=list(_HOURS_GAPS),
    summary=SUMMARIES["after"]["en"],
    demo_mode=True,
    rules_version=accessors.rules_version(),
)
