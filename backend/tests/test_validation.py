"""B10: cross-document validation checks (R5)."""

from app.mocks.jorge import CAFE, JORGE_CASE, JORGE_RECORDS, PANTRY_MAY, QUICKDASH_APR
from app.schemas.common import BoolField, OrgTypeField, StrField
from app.schemas.evidence import Flag
from app.validation.checks import validate_records


def _rec(rec_id: str):
    return next(r for r in JORGE_RECORDS if r.id == rec_id)


def _codes(records, rec_id: str) -> list[str]:
    return [f.code for f in next(r for r in records if r.id == rec_id).flags]


def test_jorge_only_pantry_may_hours_flagged():
    out = validate_records(JORGE_CASE, JORGE_RECORDS)
    flagged = {r.id: [(f.code, f.field) for f in r.flags] for r in out if r.flags}
    assert flagged == {PANTRY_MAY: [("LOW_CONFIDENCE_UNCONFIRMED", "hours")]}


def test_confirmed_field_not_flagged_and_validation_is_idempotent():
    out = validate_records(JORGE_CASE, JORGE_RECORDS)
    assert validate_records(JORGE_CASE, out) == out
    confirmed = [
        r.model_copy(update={"hours": r.hours.model_copy(update={"confirmed": True})}) if r.id == PANTRY_MAY else r
        for r in out
    ]
    assert not any(r.flags for r in validate_records(JORGE_CASE, confirmed))


def test_pipeline_flags_are_kept():
    ungrounded = Flag(code="UNGROUNDED_VALUE", message="x", field="grossCents")
    cafe = _rec(CAFE).model_copy(update={"flags": [ungrounded]})
    (out,) = validate_records(JORGE_CASE, [cafe])
    assert out.flags == [ungrounded]


def test_duplicate_flags_the_dropped_copy_only():
    copy = _rec(QUICKDASH_APR).model_copy(update={"id": "zz-copy", "doc_id": "other.pdf"})
    out = validate_records(JORGE_CASE, [_rec(QUICKDASH_APR), copy])
    assert _codes(out, QUICKDASH_APR) == []
    assert _codes(out, "zz-copy") == ["DUPLICATE"]


def test_stale_document_uses_provisional_rule():
    cafe = _rec(CAFE)
    old = cafe.model_copy(update={"document_date": cafe.document_date.model_copy(update={"value": "2027-04-12"})})
    edge = cafe.model_copy(update={"document_date": cafe.document_date.model_copy(update={"value": "2027-04-13"})})
    (flagged,) = validate_records(JORGE_CASE, [old])
    (ok,) = validate_records(JORGE_CASE, [edge])  # exactly 60 days before 2027-06-12
    assert [f.code for f in flagged.flags] == ["STALE_DOCUMENT"]
    assert flagged.flags[0].rule_id == "paystub_recency_days"
    assert flagged.flags[0].rule_status == "provisional"
    assert ok.flags == []


def test_volunteer_org_ineligible():
    pantry = _rec(PANTRY_MAY)
    political = pantry.model_copy(
        update={
            "id": "rec-political",
            "org_type": OrgTypeField(value="political", confidence="high", page=1),
            "hours": pantry.hours.model_copy(update={"confidence": "high"}),
        }
    )
    partisan = political.model_copy(
        update={
            "id": "rec-partisan",
            "org_type": OrgTypeField(value="nonprofit", confidence="high", page=1),
            "non_partisan": BoolField(value=False, confidence="high", page=1),
        }
    )
    (a,) = validate_records(JORGE_CASE, [political])
    (b,) = validate_records(JORGE_CASE, [partisan])
    assert [f.code for f in a.flags] == ["VOLUNTEER_ORG_INELIGIBLE"]
    assert [f.code for f in b.flags] == ["VOLUNTEER_ORG_INELIGIBLE"]
    assert a.flags[0].rule_id == "volunteer_org_requirement"


def test_name_mismatch_is_case_insensitive():
    cafe = _rec(CAFE)
    same = cafe.model_copy(update={"person_name": StrField(value="  JORGE   ramos ", confidence="high", page=1)})
    other = cafe.model_copy(
        update={"id": "rec-other", "person_name": StrField(value="Maria Lopez", confidence="high", page=1)}
    )
    (a,) = validate_records(JORGE_CASE, [same])
    (b,) = validate_records(JORGE_CASE, [other])
    assert a.flags == []
    assert [f.code for f in b.flags] == ["NAME_MISMATCH"]
