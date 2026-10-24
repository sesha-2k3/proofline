"""Ledger correctness properties P1-P8 (design.md / BUILD_PLAN B5)."""

from datetime import date, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st
from ledger_factory import CASE, DOC_TYPE, make_record

from app.ledger.evaluate import STATUS_RANK, evaluate_case, is_countable
from app.ledger.split import allocate_by_end_date, allocate_proportional
from app.rules import accessors

H = accessors.hours_threshold()
INCOME = accessors.income_threshold_cents()
PBT = settings(max_examples=200, deadline=None)

# Valid input assumptions: dates within 2026-10-01..2027-12-31, start <= end, numbers >= 0, expenses <= gross.
D1 = date(2027, 12, 31)
LOW_FIELDS = [None, None, None, "hours", "gross_cents", "issuer", "period_start", "document_date"]


@st.composite
def periods(draw):
    start = draw(st.dates(min_value=date(2026, 12, 1), max_value=date(2027, 7, 31)))
    end = min(D1, start + timedelta(days=draw(st.integers(0, 45))))
    return start, end


@st.composite
def records_st(draw, rec_id: str, countable: bool = False, issuer: str | None = None):
    kind = draw(st.sampled_from(sorted(DOC_TYPE)))
    start, end = draw(periods())
    gross = draw(st.integers(0, 2 * INCOME))
    expenses = draw(st.integers(0, gross))
    low_field = None if countable else draw(st.sampled_from(LOW_FIELDS))
    return make_record(
        rec_id,
        kind,
        start.isoformat(),
        end.isoformat(),
        hours_h=draw(st.integers(0, H)),
        gross=gross,
        expenses=expenses,
        issuer=issuer,
        low_field=low_field,
        confirmed=draw(st.booleans()),
        half_time=draw(st.booleans()),
    )


@st.composite
def record_lists(draw, max_size: int = 6):
    n = draw(st.integers(0, max_size))
    return [draw(records_st(f"rec-{i:02d}")) for i in range(n)]


def _totals(m):
    return (m.work_hours, m.volunteer_hours, m.training_hours, m.gross_income_cents, m.net_income_cents)


# P1 ---------------------------------------------------------------------------
@PBT
@given(st.data())
def test_p1_order_independence(data):
    """**Validates: Requirements 7**"""
    records = data.draw(record_lists())
    shuffled = data.draw(st.permutations(records))
    assert evaluate_case(CASE, records) == evaluate_case(CASE, list(shuffled))


# P2 ---------------------------------------------------------------------------
@PBT
@given(record_lists(), records_st("zz-added", countable=True, issuer="Added Org"))
def test_p2_monotonicity(records, added):
    """**Validates: Requirements 7**"""
    before, _ = evaluate_case(CASE, records)
    after, _ = evaluate_case(CASE, [*records, added])
    for b, a in zip(before, after, strict=True):
        assert STATUS_RANK[a.status] >= STATUS_RANK[b.status]
        assert all(x >= y for x, y in zip(_totals(a), _totals(b), strict=True))


# P3 ---------------------------------------------------------------------------
@PBT
@given(record_lists())
def test_p3_unconfirmed_exclusion(records):
    """**Validates: Requirements 7, 6.3**"""
    uncountable = {r.id for r in records if not is_countable(r)}
    months, _ = evaluate_case(CASE, records)
    for m in months:
        assert not uncountable & set(m.counted_record_ids)


# P4 ---------------------------------------------------------------------------
@PBT
@given(periods(), st.integers(0, 100_000), st.integers(0, 1_000_000), st.data())
def test_p4_split_conservation(period, hours_h, gross, data):
    """**Validates: Requirements 7**"""
    expenses = data.draw(st.integers(0, gross))
    start, end = period
    for alloc in (allocate_proportional, allocate_by_end_date):
        shares = alloc(start, end, hours_h, gross, expenses).values()
        assert sum(s.hours_h for s in shares) == hours_h
        assert sum(s.gross_cents for s in shares) == gross
        assert sum(s.expenses_cents for s in shares) == expenses
        assert all(s.hours_h >= 0 and s.gross_cents >= 0 and s.expenses_cents >= 0 for s in shares)


# P5 ---------------------------------------------------------------------------
@PBT
@given(record_lists(max_size=5).filter(bool), st.data())
def test_p5_duplicates_collapse(records, data):
    """**Validates: Requirements 7**"""
    dup = data.draw(st.sampled_from(records))
    assert evaluate_case(CASE, [*records, dup]) == evaluate_case(CASE, records)


# P6 ---------------------------------------------------------------------------
@PBT
@given(st.integers(1, 6), st.integers(1, 28), st.data())
def test_p6_threshold_boundary(month, first_day, data):
    """**Validates: Requirements 7**"""
    last_day = data.draw(st.integers(first_day, 28))
    start, end = f"2027-{month:02d}-{first_day:02d}", f"2027-{month:02d}-{last_day:02d}"
    target = f"2027-{month:02d}"
    for hours_h, expected in ((H, "meets"), (H - 1, "short")):
        rec = make_record("rec-p6", "work_employer", start, end, hours_h=hours_h, gross=0)
        months, _ = evaluate_case(CASE, [rec])
        assert next(m for m in months if m.month == target).status == expected


# P7 ---------------------------------------------------------------------------
@PBT
@given(st.integers(1, 6), st.integers(INCOME, 2 * INCOME), st.integers(0, H - 1), st.data())
def test_p7_unresolved_never_meets(month, gross, hours_h, data):
    """**Validates: Requirements 7**"""
    expenses = data.draw(st.integers(gross - INCOME + 1, gross))  # net < threshold <= gross
    training_h = data.draw(st.integers(0, 2 * H))
    span = (f"2027-{month:02d}-01", f"2027-{month:02d}-28")
    records = [
        make_record("rec-gig", "work_gig", *span, hours_h=hours_h, gross=gross, expenses=expenses),
        make_record("rec-train", "training", *span, hours_h=training_h, gross=0),
    ]
    months, _ = evaluate_case(CASE, records)
    m = next(m for m in months if m.month == f"2027-{month:02d}")
    assert m.status == "conditional"
    assert "self_employment_income_basis" in m.depends_on_unresolved
    assert m.paths_met == []


# P8 ---------------------------------------------------------------------------
@PBT
@given(record_lists())
def test_p8_best_month_dominance(records):
    """**Validates: Requirements 7**"""
    months, best = evaluate_case(CASE, records)
    best_rank = STATUS_RANK[next(m for m in months if m.month == best).status]
    assert all(best_rank >= STATUS_RANK[m.status] for m in months)
