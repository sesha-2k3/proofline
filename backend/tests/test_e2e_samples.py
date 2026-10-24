"""B10 end-to-end: upload the 7 sample PDFs -> validate -> evaluate reproduces EVAL_BEFORE, then EVAL_AFTER."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mocks.jorge import (
    EVAL_AFTER,
    EVAL_BEFORE,
    JORGE_CASE,
    JORGE_SAMPLES,
    PANTRY_MAY,
    SUMMARIES,
)
from app.schemas.api import DocumentResult, EvaluateResponse, ValidateResponse
from app.settings import get_settings

SAMPLES_DIR = get_settings().samples_dir


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _case(lang="en") -> dict:
    return JORGE_CASE.model_copy(update={"lang": lang}).model_dump(mode="json", by_alias=True)


def _upload_all(client: TestClient) -> list[dict]:
    records: list[dict] = []
    for i, sample in enumerate(JORGE_SAMPLES):
        res = client.post(
            "/api/documents",
            files={"file": (sample.name, (SAMPLES_DIR / sample.name).read_bytes(), "application/pdf")},
            data={"doc_id": f"doc-{i}"},
        )
        assert res.status_code == 200
        records += [r.model_dump(mode="json", by_alias=True) for r in DocumentResult.model_validate(res.json()).records]
    return records


def _evaluate(client: TestClient, records: list[dict], lang="en") -> EvaluateResponse:
    res = client.post("/api/evaluate", json={"caseInfo": _case(lang), "records": records})
    assert res.status_code == 200
    return EvaluateResponse.model_validate(res.json())


def test_samples_upload_validate_evaluate_before_and_after(client: TestClient):
    records = _upload_all(client)
    assert len(records) == 7

    res = client.post("/api/validate", json={"caseInfo": _case(), "records": records})
    assert res.status_code == 200
    validated = ValidateResponse.model_validate(res.json()).records
    flagged = {r.id: [f.code for f in r.flags] for r in validated if r.flags}
    assert flagged == {PANTRY_MAY: ["LOW_CONFIDENCE_UNCONFIRMED"]}
    validated_json = [r.model_dump(mode="json", by_alias=True) for r in validated]

    before = _evaluate(client, validated_json)
    assert before.months == EVAL_BEFORE.months
    assert before.gaps == EVAL_BEFORE.gaps
    assert before.best_month == "2027-05" and before.deadline == EVAL_BEFORE.deadline
    assert before.summary == SUMMARIES["before"]["en"]

    # Navigator confirms the pantry's May hours.
    for r in validated_json:
        if r["id"] == PANTRY_MAY:
            r["hours"]["confirmed"] = True
    after = _evaluate(client, validated_json)
    assert after.months == EVAL_AFTER.months
    assert after.gaps == EVAL_AFTER.gaps
    assert after.best_month == "2027-05" and after.deadline == EVAL_AFTER.deadline
    assert after.summary == SUMMARIES["after"]["en"]
    assert _evaluate(client, validated_json, "es").summary == SUMMARIES["after"]["es"]
