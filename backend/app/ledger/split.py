"""Allocate a record's hours and money to calendar months (pure, integer arithmetic).

Hours are integer hundredths of an hour; money is integer cents.
"""

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Share:
    hours_h: int
    gross_cents: int
    expenses_cents: int


def month_of(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _days_by_month(start: date, end: date) -> list[tuple[str, int]]:
    """Inclusive day counts per month from start to end, chronological."""
    out: list[tuple[str, int]] = []
    cur = start
    while cur <= end:
        nxt_month = date(cur.year + (cur.month == 12), cur.month % 12 + 1, 1)
        seg_end = min(end, nxt_month - timedelta(days=1))
        out.append((month_of(cur), (seg_end - cur).days + 1))
        cur = nxt_month
    return out


def _round_div(num: int, den: int) -> int:
    """Round num/den half up (num, den >= 0, den > 0)."""
    return (2 * num + den) // (2 * den)


def _cumulative(total: int, days: list[int], total_days: int) -> list[int]:
    shares: list[int] = []
    cum_days = 0
    prev = 0
    for d in days:
        cum_days += d
        cur = _round_div(total * cum_days, total_days)
        shares.append(cur - prev)
        prev = cur
    return shares


def allocate_proportional(start: date, end: date, hours_h: int, gross: int, expenses: int) -> dict[str, Share]:
    """Split by days in each month with cumulative rounding; shares sum exactly to the totals."""
    segments = _days_by_month(start, end)
    days = [d for _, d in segments]
    total_days = sum(days)
    h = _cumulative(hours_h, days, total_days)
    g = _cumulative(gross, days, total_days)
    e = _cumulative(expenses, days, total_days)
    return {m: Share(h[i], g[i], e[i]) for i, (m, _) in enumerate(segments)}


def allocate_by_end_date(start: date, end: date, hours_h: int, gross: int, expenses: int) -> dict[str, Share]:
    """Assign everything to the month the period ends in. `start` is unused but kept for a matching signature."""
    return {month_of(end): Share(hours_h, gross, expenses)}


def overlapped_months(start: date, end: date) -> list[str]:
    return [m for m, _ in _days_by_month(start, end)]
