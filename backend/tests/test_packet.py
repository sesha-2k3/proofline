"""B11: packet and submission record PDFs (R9)."""
import pypdfium2 as pdfium
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.mocks.jorge import EVAL_AFTER, EVAL_BEFORE, JORGE_CASE, JORGE_RECORDS
from app.packet.packet import DISCLAIMER, EXEMPTION_LABEL
from app.rules import accessors


def _dump(model) -> dict:
    return model.model_dump(mode="json", by_alias=True)


def _text(pdf: bytes) -> str:
    doc = pdfium.PdfDocument(pdf)
    text = " ".join(page.get_textpage().get_text_range() for page in doc)
    return " ".join(text.split())


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def _packet(client: TestClient, evaluation: dict) -> bytes:
    payload = {
        "caseInfo": _dump(JORGE_CASE),
        "records": [_dump(r) for r in JORGE_RECORDS],
        "evaluation": evaluation,
    }
    res = client.post("/api/packet", json=payload)
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")
    return res.content


def test_packet_before_names_unresolved_rules_and_disclaimer(client: TestClient) -> None:
    text = _text(_packet(client, _dump(EVAL_BEFORE)))
    assert DISCLAIMER in text
    assert "Jorge Ramos" in text
    assert "May 2027" in text
    assert "Conditional" in text
    for rule_id in ("self_employment_income_basis", "pay_period_split_method"):
        assert rule_id in text
    assert "July 12, 2027 (provisional)" in text
    compact = text.replace(" ", "")  # long ids wrap inside table cells
    for record in JORGE_RECORDS:
        assert record.id in compact


def test_packet_after_with_possible_exemption(client: TestClient) -> None:
    exemption = accessors.exemptions()[0]
    evaluation = _dump(EVAL_AFTER)
    evaluation["possibleExemptions"] = [_dump(exemption)]
    text = _text(_packet(client, evaluation))
    assert "the evidence appears to show" in text
    assert EXEMPTION_LABEL in text
    assert exemption.source_url in text
    assert "exempt." not in text.lower()


def test_timeline_pdf_lists_submissions(client: TestClient) -> None:
    payload = {
        "caseInfo": _dump(JORGE_CASE),
        "submissions": [
            {"submittedAt": "2027-06-20", "channel": "online", "confirmationNumber": "CONF-0001", "documentsIncluded": ["packet"]},
            {"submittedAt": "2027-06-18", "channel": "in_person", "documentsIncluded": [], "notes": "Dropped off copy"},
        ],
    }
    res = client.post("/api/timeline", json=payload)
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    assert "proofline-submission-record.pdf" in res.headers["content-disposition"]
    text = _text(res.content)
    assert "CONF-0001" in text and "In person" in text
    assert text.index("June 18, 2027") < text.index("June 20, 2027")


def test_timeline_pdf_with_no_submissions(client: TestClient) -> None:
    res = client.post("/api/timeline", json={"caseInfo": _dump(JORGE_CASE), "submissions": []})
    assert res.status_code == 200
    assert res.content.startswith(b"%PDF")
    assert "No submissions logged." in _text(res.content)
