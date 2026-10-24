"""B12: the evaluation script scores the offline pipeline on the 7 samples."""
from app.mocks.jorge import EVAL_AFTER, EVAL_BEFORE
from scripts.eval_extraction import format_report, run_eval


def test_eval_on_samples_is_exact_with_no_false_passes():
    res = run_eval()
    assert res.files == 7 and res.classification_accuracy == 1.0
    assert res.fields_total > 0 and res.field_accuracy == 1.0
    assert res.grounding_rate == 1.0
    assert res.false_pass_count == 0 and res.mismatches == []
    before = {m: got for m, got, _ in res.month_status["as extracted"]}
    after = {m: got for m, got, _ in res.month_status["after navigator confirmation"]}
    assert before == {m.month: m.status for m in EVAL_BEFORE.months}
    assert after == {m.month: m.status for m in EVAL_AFTER.months}
    report = format_report(res)
    for label in ("Classification accuracy", "Field accuracy", "Grounding rate", "False-pass count"):
        assert label in report
