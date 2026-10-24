"""Jorge scenario: the ledger reproduces EVAL_BEFORE / EVAL_AFTER months exactly."""

from app.ledger.evaluate import evaluate_case
from app.mocks.jorge import (
    EVAL_AFTER,
    EVAL_BEFORE,
    JORGE_CASE,
    JORGE_RECORDS,
    PANTRY_MAY,
)


def _confirm_pantry_may():
    out = []
    for r in JORGE_RECORDS:
        if r.id == PANTRY_MAY:
            r = r.model_copy(update={"hours": r.hours.model_copy(update={"confirmed": True})})
        out.append(r)
    return out


def test_jorge_before_confirmation():
    months, best = evaluate_case(JORGE_CASE, JORGE_RECORDS)
    assert months == EVAL_BEFORE.months
    assert best == EVAL_BEFORE.best_month == "2027-05"


def test_jorge_after_confirming_pantry_may_hours():
    months, best = evaluate_case(JORGE_CASE, _confirm_pantry_may())
    assert months == EVAL_AFTER.months
    assert best == EVAL_AFTER.best_month == "2027-05"
