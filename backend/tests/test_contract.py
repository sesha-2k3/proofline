"""Contract tests: every mock-backed endpoint returns 200 and parses into its response model."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mocks.jorge import (
    EVAL_AFTER,
    EVAL_BEFORE,
    JORGE_CASE,
    JORGE_RECORDS,
    JORGE_SAMPLES,
    PANTRY_MAY,
)
from app.schemas.api import (
    DocumentResult,
    EvaluateResponse,
    HealthResponse,
    RulesResponse,
    SamplesResponse,
    ValidateResponse,
)


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


def _records_json(confirm_pantry_may: bool = False) -> list[dict]:
    out = []
    for r in JORGE_RECORDS:
        if confirm_pantry_may and r.id == PANTRY_MAY:
            r = r.model_copy(update={"hours": r.hours.model_copy(update={"confirmed": True})})
        out.append(_dump(r))
    return out


def test_health(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    body = HealthResponse.model_validate(res.json())
    assert body.ok
    assert "demoMode" in res.json()


def test_rules(client: TestClient) -> None:
    res = client.get("/api/rules")
    assert res.status_code == 200
    body = RulesResponse.model_validate(res.json())
    assert {"self_employment_income_basis", "pay_period_split_method"} <= {u.id for u in body.unresolved_rules}
    assert body.exemption_questions and all(e.source_url for e in body.exemption_questions)


def test_samples(client: TestClient) -> None:
    res = client.get("/api/samples")
    assert res.status_code == 200
    body = SamplesResponse.model_validate(res.json())
    assert len(body.files) == 7
    assert body.case_info == JORGE_CASE


@pytest.mark.parametrize("sample", JORGE_SAMPLES, ids=lambda s: s.name)
def test_documents_known(client: TestClient, sample) -> None:
    res = client.post(
        "/api/documents",
        files={"file": (sample.name, b"%PDF-1.4 mock", "application/pdf")},
        data={"doc_id": "doc-123"},
    )
    assert res.status_code == 200
    body = DocumentResult.model_validate(res.json())
    assert body.doc_type == sample.doc_type
    assert all(r.doc_id == "doc-123" for r in body.records)
    assert all(s.status == "ok" for s in body.pipeline)
    if sample.doc_type == "rfi_notice":
        assert body.notice is not None and body.records == []
    else:
        assert body.records


def test_documents_unknown_uses_hint(client: TestClient) -> None:
    res = client.post(
        "/api/documents",
        files={"file": ("mystery.png", b"\x89PNG", "image/png")},
        data={"doc_id": "doc-x"},
    )
    body = DocumentResult.model_validate(res.json())
    assert body.doc_type == "unknown" and body.records == []
    assert body.warnings == ["Could not recognize this document. Choose its type."]

    res = client.post(
        "/api/documents",
        files={"file": ("mystery.png", b"\x89PNG", "image/png")},
        data={"doc_id": "doc-x", "doc_type_hint": "paystub"},
    )
    assert DocumentResult.model_validate(res.json()).doc_type == "paystub"


def test_validate_flags_low_confidence_hours(client: TestClient) -> None:
    payload = {"caseInfo": _dump(JORGE_CASE), "records": _records_json()}
    res = client.post("/api/validate", json=payload)
    assert res.status_code == 200
    body = ValidateResponse.model_validate(res.json())
    flagged = {r.id for r in body.records if any(f.code == "LOW_CONFIDENCE_UNCONFIRMED" for f in r.flags)}
    assert flagged == {PANTRY_MAY}

    payload["records"] = _records_json(confirm_pantry_may=True)
    body = ValidateResponse.model_validate(client.post("/api/validate", json=payload).json())
    assert not any(r.flags for r in body.records)


def test_evaluate_switches_on_confirmation(client: TestClient) -> None:
    payload = {"caseInfo": _dump(JORGE_CASE), "records": _records_json()}
    before = EvaluateResponse.model_validate(client.post("/api/evaluate", json=payload).json())
    assert before.months == EVAL_BEFORE.months
    assert before.gaps == EVAL_BEFORE.gaps
    may = next(m for m in before.months if m.month == "2027-05")
    assert may.status == "conditional"

    payload["records"] = _records_json(confirm_pantry_may=True)
    after = EvaluateResponse.model_validate(client.post("/api/evaluate", json=payload).json())
    assert after.months == EVAL_AFTER.months
    assert after.gaps == EVAL_AFTER.gaps
    assert next(m for m in after.months if m.month == "2027-05").status == "meets"
    assert after.best_month == "2027-05"


def test_evaluate_exemptions_and_spanish(client: TestClient) -> None:
    case = _dump(JORGE_CASE) | {"lang": "es"}
    payload = {
        "caseInfo": case,
        "records": _records_json(),
        "exemptionAnswers": [{"id": "medicare", "answer": True}, {"id": "aian", "answer": False}],
    }
    body = EvaluateResponse.model_validate(client.post("/api/evaluate", json=payload).json())
    assert [e.id for e in body.possible_exemptions] == ["medicare"]
    assert body.summary.startswith("Mayo de 2027")


def test_packet_and_timeline_pdfs(client: TestClient) -> None:
    payload = {"caseInfo": _dump(JORGE_CASE), "records": _records_json(), "evaluation": _dump(EVAL_BEFORE)}
    res = client.post("/api/packet", json=payload)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    assert "proofline-packet-2027-05.pdf" in res.headers["content-disposition"]

    payload = {
        "caseInfo": _dump(JORGE_CASE),
        "submissions": [{"submittedAt": "2027-06-20", "channel": "online", "documentsIncluded": ["packet"]}],
    }
    res = client.post("/api/timeline", json=payload)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    assert "proofline-submission-record.pdf" in res.headers["content-disposition"]
