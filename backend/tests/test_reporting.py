"""B10: deadline, exemptions, gaps, summary (R2.2, R2.3, R8, R9)."""

from app.ledger.evaluate import evaluate_case
from app.mocks.jorge import (
    EVAL_AFTER,
    EVAL_BEFORE,
    JORGE_CASE,
    JORGE_RECORDS,
    PANTRY_MAY,
    SUMMARIES,
)
from app.reporting.deadline import response_deadline
from app.reporting.exemptions import possible_exemptions
from app.reporting.gaps import build_gaps
from app.reporting.summary import build_summary, numbers_unchanged
from app.schemas.api import ExemptionAnswer
from app.schemas.common import CaseInfo
from app.validation.checks import validate_records


def _confirmed():
    return [
        r.model_copy(update={"hours": r.hours.model_copy(update={"confirmed": True})}) if r.id == PANTRY_MAY else r
        for r in JORGE_RECORDS
    ]


def _run(records, lang="en", rephraser=None):
    records = validate_records(JORGE_CASE, records)
    months, best = evaluate_case(JORGE_CASE, records)
    deadline = response_deadline(JORGE_CASE)
    gaps = build_gaps(months, best, records)
    summary = build_summary(months, best, records, deadline, lang, rephraser)
    return gaps, summary


def test_deadline_is_rfi_date_plus_response_days_and_provisional():
    assert response_deadline(JORGE_CASE) == EVAL_BEFORE.deadline
    assert response_deadline(JORGE_CASE.model_copy(update={"rfi_received_date": None})) is None


def test_possible_exemptions_only_for_yes_answers_with_sources():
    out = possible_exemptions(
        [ExemptionAnswer(id="aian", answer=True), ExemptionAnswer(id="medicare", answer=False),
         ExemptionAnswer(id="not_a_rule", answer=True)]
    )
    assert [e.id for e in out] == ["aian"]
    assert out[0].source == "S1" and out[0].source_url.startswith("https://www.mass.gov/")
    assert "exempt" not in out[0].label.lower().split()


def test_gaps_match_jorge_before_and_after():
    assert _run(JORGE_RECORDS)[0] == EVAL_BEFORE.gaps
    assert _run(_confirmed())[0] == EVAL_AFTER.gaps


def test_summaries_match_jorge_en_and_es():
    for lang in ("en", "es"):
        assert _run(JORGE_RECORDS, lang)[1] == SUMMARIES["before"][lang]
        assert _run(_confirmed(), lang)[1] == SUMMARIES["after"][lang]


class _Fake:
    def __init__(self, reply):
        self.reply = reply

    def rephrase(self, text, lang):
        return self.reply(text)


def test_llm_rephrase_used_only_when_numbers_unchanged():
    template = SUMMARIES["after"]["en"]
    kept = _Fake(lambda t: "Good news. " + t)
    changed = _Fake(lambda t: t.replace("92.93", "95"))
    dropped = _Fake(lambda t: "May 2027 looks good. MassHealth makes the final decision.")
    assert _run(_confirmed(), rephraser=kept)[1] == "Good news. " + template
    assert _run(_confirmed(), rephraser=changed)[1] == template
    assert _run(_confirmed(), rephraser=dropped)[1] == template
    assert _run(_confirmed(), rephraser=_Fake(lambda t: None))[1] == template
    assert numbers_unchanged("a 1.5 b $2", "$2 then 1.5") and not numbers_unchanged("80", "80 81")


def test_new_application_evaluates_only_month_before():
    case = CaseInfo(client_name="Jorge Ramos", case_type="new_application", application_month="2027-06")
    months, best = evaluate_case(case, JORGE_RECORDS)
    assert [m.month for m in months] == ["2027-05"] and best == "2027-05"
    jan = CaseInfo(client_name="Jorge Ramos", case_type="new_application", application_month="2027-01")
    assert [m.month for m in evaluate_case(jan, JORGE_RECORDS)[0]] == ["2026-12"]
