"""Threshold boundaries and a record spanning two months. Thresholds come from the rules file."""

from datetime import date

from ledger_factory import CASE, make_record

from app.ledger.evaluate import evaluate_case
from app.ledger.split import Share, allocate_by_end_date, allocate_proportional
from app.rules import accessors

H = accessors.hours_threshold()  # integer hundredths of an hour
INCOME = accessors.income_threshold_cents()


def _month(records, month):
    months, _ = evaluate_case(CASE, records)
    return next(m for m in months if m.month == month)


def test_hours_one_hundredth_below_threshold_is_short():
    m = _month([make_record("r1", "work_employer", "2027-03-01", "2027-03-31", hours_h=H - 1)], "2027-03")
    assert m.status == "short"
    assert m.hours_shortfall == 0.01
    assert m.paths_met == []


def test_hours_exactly_threshold_meets():
    m = _month([make_record("r1", "work_employer", "2027-03-01", "2027-03-31", hours_h=H)], "2027-03")
    assert m.status == "meets"
    assert m.paths_met == ["hours_threshold"]
    assert m.hours_shortfall == 0


def test_income_one_cent_below_threshold_is_short():
    m = _month([make_record("r1", "work_paystub", "2027-03-01", "2027-03-31", gross=INCOME - 1)], "2027-03")
    assert m.status == "short"
    assert m.income_shortfall_cents == 1


def test_income_exactly_threshold_meets():
    m = _month([make_record("r1", "work_paystub", "2027-03-01", "2027-03-31", gross=INCOME)], "2027-03")
    assert m.status == "meets"
    assert m.paths_met == ["income_threshold_cents"]
    assert m.income_shortfall_cents == 0


def test_split_two_months_proportional_and_end_date():
    start, end = date(2027, 5, 24), date(2027, 6, 6)  # 8 days in May, 6 in June
    assert allocate_proportional(start, end, 2000, 31000, 0) == {
        "2027-05": Share(1143, 17714, 0),
        "2027-06": Share(857, 13286, 0),
    }
    assert allocate_by_end_date(start, end, 2000, 31000, 0) == {"2027-06": Share(2000, 31000, 0)}


def test_record_spanning_two_months_counts_in_both_and_can_depend_on_split_method():
    # Base work in April just under the threshold; a spanning record pushes April over only proportionally.
    base = make_record("r-base", "work_employer", "2027-04-01", "2027-04-30", hours_h=H - 100)
    span = make_record("r-span", "work_employer", "2027-04-21", "2027-05-10", hours_h=400)  # 10 days Apr, 10 May
    months, _ = evaluate_case(CASE, [base, span])
    apr = next(m for m in months if m.month == "2027-04")
    may = next(m for m in months if m.month == "2027-05")
    assert apr.counted_record_ids == ["r-base", "r-span"]
    assert may.counted_record_ids == ["r-span"]
    assert apr.work_hours == (H - 100 + 200) / 100
    assert apr.status == "conditional"
    assert apr.depends_on_unresolved == ["pay_period_split_method"]
    assert apr.paths_met == []
