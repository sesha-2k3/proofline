"""Month-by-month ledger evaluation (pure). Implements BUILD_PLAN Appendix "Ledger decisions" 1-12.

All thresholds come from app.rules.accessors. Hours are integer hundredths; money is integer cents.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from app.ledger.split import (
    Share,
    allocate_by_end_date,
    allocate_proportional,
    overlapped_months,
)
from app.rules import accessors
from app.schemas.common import CaseInfo
from app.schemas.evidence import EvidenceRecord
from app.schemas.ledger import MonthResult

SELF_EMPLOYMENT = "self_employment_income_basis"
JOB_TRAINING = "job_training_approved"
SPLIT_METHOD = "pay_period_split_method"
DEPENDENCY_ORDER = [SELF_EMPLOYMENT, JOB_TRAINING, SPLIT_METHOD]

HOURS_PATH = "hours_threshold"
INCOME_PATH = "income_threshold_cents"
SCHOOL_PATH = "school_half_time"

STATUS_RANK = {"short": 0, "conditional": 1, "meets": 2}

FIELD_NAMES = [
    "person_name",
    "issuer",
    "org_type",
    "non_partisan",
    "period_start",
    "period_end",
    "hours",
    "hourly_rate_cents",
    "gross_cents",
    "expenses_cents",
    "half_time_enrolled",
    "document_date",
]

Allocator = Callable[[date, date, int, int, int], dict[str, Share]]


@dataclass
class _Totals:
    work_h: int = 0
    volunteer_h: int = 0
    training_h: int = 0
    employee_gross: int = 0
    gig_gross: int = 0
    gig_net: int = 0

    @property
    def hours_h(self) -> int:
        return self.work_h + self.volunteer_h

    @property
    def gross(self) -> int:
        return self.employee_gross + self.gig_gross

    @property
    def net(self) -> int:
        return self.employee_gross + self.gig_net


@dataclass
class _Outcome:
    status: str
    deps: list[str] = field(default_factory=list)
    paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Thresholds:
    hours_h: int
    income_cents: int


# --- helpers -----------------------------------------------------------------


def _month_range(start: str, end: str) -> list[str]:
    y, m = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    out: list[str] = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def case_months(case_info: CaseInfo) -> list[str]:
    """Renewal: window_start..window_end. New application: the month before application_month."""
    if case_info.case_type == "renewal":
        if not case_info.window_start or not case_info.window_end:
            return []
        return _month_range(case_info.window_start, case_info.window_end)
    if not case_info.application_month:
        return []
    y, m = int(case_info.application_month[:4]), int(case_info.application_month[5:7])
    y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return [f"{y:04d}-{m:02d}"]


def is_countable(record: EvidenceRecord) -> bool:
    """Decision 1: every present field is high-confidence or navigator-confirmed."""
    for name in FIELD_NAMES:
        f = getattr(record, name)
        if f is not None and f.confidence != "high" and not f.confirmed:
            return False
    return True


def volunteer_eligible(record: EvidenceRecord) -> bool:
    allowed = accessors.allowed_volunteer_org_types()
    if record.org_type is None or record.org_type.value not in allowed:
        return False
    if accessors.rule("volunteer_org_requirement").requires_non_partisan:
        return record.non_partisan is not None and record.non_partisan.value is True
    return True


def _num(f) -> int:
    return 0 if f is None or f.value is None else round(f.value)


def _hours_h(record: EvidenceRecord) -> int:
    return 0 if record.hours is None or record.hours.value is None else round(record.hours.value * 100)


def _dates(record: EvidenceRecord) -> tuple[date, date] | None:
    if record.period_start.value is None or record.period_end.value is None:
        return None
    return date.fromisoformat(record.period_start.value), date.fromisoformat(record.period_end.value)


def dedupe_key(r: EvidenceRecord) -> tuple:
    """Duplicate identity: same doc_type, issuer (case-insensitive), and period."""
    return (r.doc_type, (r.issuer.value or "").casefold(), r.period_start.value, r.period_end.value)


def dedupe_order(r: EvidenceRecord) -> tuple:
    """Which copy of a duplicate the ledger keeps: a countable one first, then the smallest id."""
    return (not is_countable(r), r.id)


def _dedupe(records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    """Collapse duplicates (same doc_type, issuer, period). Keep a countable one first, then the smallest id."""
    kept: dict[tuple, EvidenceRecord] = {}
    for r in sorted(records, key=dedupe_order):
        kept.setdefault(dedupe_key(r), r)
    return sorted(kept.values(), key=lambda r: r.id)


def _add(totals: _Totals, record: EvidenceRecord, share: Share) -> None:
    if record.activity == "work":
        totals.work_h += share.hours_h
    elif record.activity == "volunteer":
        totals.volunteer_h += share.hours_h
    elif record.activity == "job_training":
        totals.training_h += share.hours_h
    if record.activity in ("volunteer", "school"):
        return
    if record.doc_type == "gig_earnings":
        totals.gig_gross += share.gross_cents
        totals.gig_net += max(0, share.gross_cents - share.expenses_cents)
    elif record.doc_type in ("paystub", "employer_statement"):
        totals.employee_gross += share.gross_cents


def _totals(records: list[EvidenceRecord], months: list[str], allocate: Allocator) -> dict[str, _Totals]:
    out = {m: _Totals() for m in months}
    for r in records:
        start, end = _dates(r)  # type: ignore[misc]
        gross = _num(r.gross_cents)
        expenses = _num(r.expenses_cents) if r.doc_type == "gig_earnings" else 0
        for m, share in allocate(start, end, _hours_h(r), gross, expenses).items():
            if m in out:
                _add(out[m], r, share)
    return out


def _outcome(t: _Totals, school: bool, th: _Thresholds) -> _Outcome:
    paths: list[str] = []
    if t.hours_h >= th.hours_h:
        paths.append(HOURS_PATH)
    if t.net >= th.income_cents:
        paths.append(INCOME_PATH)
    if school:
        paths.append(SCHOOL_PATH)
    if paths:
        return _Outcome("meets", [], paths)
    deps: list[str] = []
    if t.gross >= th.income_cents:
        deps.append(SELF_EMPLOYMENT)
    if t.hours_h + t.training_h >= th.hours_h:
        deps.append(JOB_TRAINING)
    return _Outcome("conditional" if deps else "short", deps, [])


def _combine(p: _Outcome, e: _Outcome) -> _Outcome:
    """Decision 5: combine proportional and end-date outcomes."""
    deps = set(p.deps) | set(e.deps)
    if (p.status, p.deps) != (e.status, e.deps):
        deps.add(SPLIT_METHOD)
    if p.status == "meets" and e.status == "meets":
        status = "meets"
    elif "meets" in (p.status, e.status) or "conditional" in (p.status, e.status):
        status = "conditional"
    else:
        status = "short"
    if status == "meets":
        return _Outcome("meets", [], list(p.paths))
    return _Outcome(status, [d for d in DEPENDENCY_ORDER if d in deps], [])


# --- public ------------------------------------------------------------------


def evaluate_months(case_info: CaseInfo, records: list[EvidenceRecord]) -> list[MonthResult]:
    months = case_months(case_info)
    month_set = set(months)
    th = _Thresholds(accessors.hours_threshold(), accessors.income_threshold_cents())

    dated = [r for r in records if _dates(r) is not None]
    unique = _dedupe(dated)

    counted: list[EvidenceRecord] = []
    counted_ids: dict[str, list[str]] = {m: [] for m in months}
    excluded_ids: dict[str, list[str]] = {m: [] for m in months}
    school: dict[str, bool] = {m: False for m in months}
    for r in unique:
        start, end = _dates(r)  # type: ignore[misc]
        overlap = [m for m in overlapped_months(start, end) if m in month_set]
        if not is_countable(r):
            for m in overlap:
                excluded_ids[m].append(r.id)
            continue
        if r.activity == "volunteer" and not volunteer_eligible(r):
            continue
        counted.append(r)
        for m in overlap:
            counted_ids[m].append(r.id)
            if r.activity == "school" and r.half_time_enrolled is not None and r.half_time_enrolled.value:
                school[m] = True

    prop = _totals(counted, months, allocate_proportional)
    end = _totals(counted, months, allocate_by_end_date)

    results: list[MonthResult] = []
    for m in months:
        t = prop[m]
        outcome = _combine(_outcome(t, school[m], th), _outcome(end[m], school[m], th))
        results.append(
            MonthResult(
                month=m,
                work_hours=t.work_h / 100,
                volunteer_hours=t.volunteer_h / 100,
                training_hours=t.training_h / 100,
                school_half_time=school[m],
                gross_income_cents=t.gross,
                net_income_cents=t.net,
                status=outcome.status,
                paths_met=outcome.paths,
                depends_on_unresolved=outcome.deps,
                hours_shortfall=max(0, th.hours_h - t.hours_h) / 100,
                income_shortfall_cents=max(0, th.income_cents - t.gross),
                counted_record_ids=sorted(counted_ids[m]),
                excluded_record_ids=sorted(excluded_ids[m]),
            )
        )
    return results


def best_month(months: list[MonthResult], records: list[EvidenceRecord]) -> str | None:
    """Decision 12: meets > conditional > short; fewer flagged counted records; most recent; largest hours margin."""
    if not months:
        return None
    flagged = {r.id for r in records if r.flags}
    hours_h = accessors.hours_threshold()

    def key(m: MonthResult) -> tuple:
        n_flagged = sum(1 for rid in m.counted_record_ids if rid in flagged)
        margin = round((m.work_hours + m.volunteer_hours) * 100) - hours_h
        return (STATUS_RANK[m.status], -n_flagged, m.month, margin)

    return max(months, key=key).month


def evaluate_case(case_info: CaseInfo, records: list[EvidenceRecord]) -> tuple[list[MonthResult], str | None]:
    months = evaluate_months(case_info, records)
    return months, best_month(months, records)
