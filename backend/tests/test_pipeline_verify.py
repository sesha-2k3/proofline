"""B9: normalize, verify, orchestrator, and the real POST /documents."""
import io
import json

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.api.documents import get_llm_client
from app.main import app
from app.mocks.jorge import JORGE_SAMPLES
from app.pipeline.extract.llm import LlmClient
from app.pipeline.extract.models import RawField, RawRecord
from app.pipeline.extract.template import extract_template
from app.pipeline.ingest import ingest
from app.pipeline.normalize import normalize, parse_date, parse_hours, parse_money_cents
from app.pipeline.render import PageContent, render
from app.pipeline.verify import arithmetic_mismatch, verify
from app.schemas.api import DocumentResult
from app.settings import BACKEND_DIR, get_settings

SAMPLES_DIR = get_settings().samples_dir
GROUND_TRUTH = json.loads(
    (BACKEND_DIR / "synthetic" / "ground_truth.json").read_text()
)["files"]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _upload(client: TestClient, name: str, data: bytes, mime="application/pdf"):
    return client.post(
        "/api/documents", files={"file": (name, data, mime)}, data={"doc_id": "doc-1"}
    )


def _pages(name: str) -> list[PageContent]:
    data = (SAMPLES_DIR / name).read_bytes()
    return render(ingest(name, "application/pdf", data, 10), with_images=False)


def _without_doc_id(items: list[dict]) -> list[dict]:
    return [{k: v for k, v in r.items() if k != "docId"} for r in items]


# ---------------------------------------------------------------- normalize
def test_normalize_parsers():
    assert parse_money_cents("$1,234.56") == 123456
    assert parse_money_cents("Unpaid ($0.00)") == 0
    assert parse_money_cents(560) == 56000
    assert parse_hours("31.5") == 31.5 and parse_hours("14.004") == 14.0
    assert parse_date("05/01/2027") == "2027-05-01"
    assert parse_date("May 1, 2027") == "2027-05-01"
    assert parse_date("2027-05-01") == "2027-05-01"
    assert parse_date("sometime in May") is None


def test_unparseable_value_becomes_null_and_low():
    raw = RawRecord(
        person_name=RawField(value="Jorge Ramos", confidence="high"),
        issuer=RawField(value="Harbor Cafe", confidence="high"),
        period_start=RawField(value="05/24/2027", confidence="high"),
        period_end=RawField(value="06/06/2027", confidence="high"),
        hours=RawField(value="about twenty", confidence="high"),
        document_date=RawField(value="06/07/2027", confidence="high"),
    )
    from app.pipeline.extract.models import RawExtraction

    (record,), _ = normalize("paystub", RawExtraction(records=[raw]), "d")
    assert record.id == "rec-paystub-harbor-cafe-2027-05-24"
    assert record.hours.value is None and record.hours.confidence == "low"


# ---------------------------------------------------------------- verify
def _template_records(name: str):
    truth = GROUND_TRUTH[name]
    pages = _pages(name)
    extraction = extract_template(truth["docType"], pages)
    records, notice = normalize(truth["docType"], extraction, name)
    return records, notice, pages


@pytest.mark.parametrize("sample", JORGE_SAMPLES, ids=lambda s: s.name)
def test_every_sample_value_is_grounded(sample):
    records, notice, pages = _template_records(sample.name)
    records, notice, report = verify(records, notice, pages)
    assert report.ungrounded == 0 and report.not_checked == 0 and report.flags == 0
    assert report.grounded > 0


def test_tampered_value_is_ungrounded():
    records, _, pages = _template_records("quickdash_2027-05.pdf")
    tampered = records[0].model_copy(
        update={"gross_cents": records[0].gross_cents.model_copy(update={"value": 99900})}
    )
    (checked,), _, report = verify([tampered], None, pages)
    assert checked.gross_cents.verification == "ungrounded"
    assert checked.gross_cents.confidence == "low"
    assert [f.code for f in checked.flags] == ["UNGROUNDED_VALUE"]
    assert checked.flags[0].field == "grossCents"
    assert checked.hours.verification == "grounded" and report.ungrounded == 1


def test_image_pages_are_not_checked():
    records, _, _ = _template_records("harbor_cafe_paystub.pdf")
    image_pages = [PageContent(page=1, text="", image_png=b"\x89PNG")]
    (checked,), _, _ = verify(records, None, image_pages)
    assert checked.hours.verification == "not_checked"
    assert checked.hours.confidence == "high" and checked.flags == []


def test_arithmetic_tolerance():
    assert not arithmetic_mismatch(20, 1550, 31000)
    assert not arithmetic_mismatch(20, 1550, 31620)  # exactly 2% off: allowed
    assert arithmetic_mismatch(20, 1550, 32000)
    assert arithmetic_mismatch(40, 1550, 31000)


def test_arithmetic_mismatch_flag_lowers_gross():
    records, _, pages = _template_records("harbor_cafe_paystub.pdf")
    rec = records[0].model_copy(
        update={"hours": records[0].hours.model_copy(update={"value": 30.0})}
    )
    (checked,), _, _ = verify([rec], None, pages)
    codes = {f.code for f in checked.flags}
    assert "ARITHMETIC_MISMATCH" in codes
    assert checked.gross_cents.confidence == "low"


def test_date_out_of_range_and_reversed_period():
    records, _, pages = _template_records("harbor_cafe_paystub.pdf")
    rec = records[0]
    old = rec.model_copy(
        update={"document_date": rec.document_date.model_copy(update={"value": "2019-06-07"})}
    )
    (checked,), _, _ = verify([old], None, pages)
    assert any(
        f.code == "DATE_OUT_OF_RANGE" and f.field == "documentDate" for f in checked.flags
    )
    assert checked.document_date.confidence == "low"

    reversed_ = rec.model_copy(
        update={
            "period_start": rec.period_end.model_copy(),
            "period_end": rec.period_start.model_copy(),
        }
    )
    (checked,), _, _ = verify([reversed_], None, pages)
    assert any(f.code == "DATE_OUT_OF_RANGE" for f in checked.flags)
    assert checked.period_start.confidence == checked.period_end.confidence == "low"


# ---------------------------------------------------------------- POST /documents
@pytest.mark.parametrize("sample", JORGE_SAMPLES, ids=lambda s: s.name)
def test_upload_sample_matches_ground_truth(client, sample):
    res = _upload(client, sample.name, (SAMPLES_DIR / sample.name).read_bytes())
    assert res.status_code == 200
    body = res.json()
    truth = GROUND_TRUTH[sample.name]
    result = DocumentResult.model_validate(body)
    assert result.doc_type == truth["docType"] and result.extractor == "template"
    assert result.demo_mode == get_settings().demo_mode
    assert [s.stage for s in result.pipeline] == [
        "ingest", "render", "classify", "extract", "normalize", "verify"
    ]
    assert all(s.status == "ok" for s in result.pipeline)
    assert all(r["docId"] == "doc-1" for r in body["records"])
    assert _without_doc_id(body["records"]) == _without_doc_id(truth["records"])
    assert body["notice"] == truth["notice"]
    for r in result.records:
        for name in type(r).model_fields:
            f = getattr(r, name)
            if hasattr(f, "verification"):
                assert f.verification == "grounded", (r.id, name)


def test_upload_rejects_unsupported_file(client):
    res = _upload(client, "notes.txt", b"hello", "text/plain")
    assert res.status_code == 415
    assert res.json()["error"]["code"] == "UNSUPPORTED_FILE"


def _edited_paystub_pdf() -> bytes:
    """A paystub whose layout the template can't read ("Worker name" label),
    so the (fake) reader runs; the page says 20.00 hours."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter, invariant=1)
    y = 720
    for line in [
        "SAMPLE — SYNTHETIC — NOT A REAL DOCUMENT",
        "Harbor Cafe Pay Stub",
        "Worker name: Jorge Ramos",
        "Pay period: 05/24/2027 - 06/06/2027",
        "Hours: 20.00",
        "Rate: $15.50",
        "Gross pay: $310.00",
        "Pay date: 06/07/2027",
    ]:
        c.drawString(72, y, line)
        y -= 20
    c.save()
    return buf.getvalue()


def _f(value, evidence, confidence="high"):
    return {"value": value, "confidence": confidence, "page": 1, "evidence": evidence}


class _FakeTransport:
    def __init__(self, reply: dict):
        self.reply = json.dumps(reply)

    def send(self, prompt: str, images: list[bytes]) -> str:
        return self.reply


def test_upload_with_value_not_on_page_is_ungrounded(client):
    reply = {
        "records": [
            {
                "person_name": _f("Jorge Ramos", "Worker name: Jorge Ramos"),
                "issuer": _f("Harbor Cafe", "Harbor Cafe Pay Stub"),
                "period_start": _f("2027-05-24", "Pay period: 05/24/2027 - 06/06/2027"),
                "period_end": _f("2027-06-06", "Pay period: 05/24/2027 - 06/06/2027"),
                "hours": _f(40.0, "Hours: 40.00"),  # differs from the page (20.00)
                "hourly_rate_cents": _f("$15.50", "Rate: $15.50"),
                "gross_cents": _f("$310.00", "Gross pay: $310.00"),
                "document_date": _f("2027-06-07", "Pay date: 06/07/2027"),
            }
        ]
    }
    app.dependency_overrides[get_llm_client] = lambda: LlmClient(_FakeTransport(reply))
    res = _upload(client, "edited_paystub.pdf", _edited_paystub_pdf())
    assert res.status_code == 200
    result = DocumentResult.model_validate(res.json())
    assert result.extractor == "llm" and result.doc_type == "paystub"
    (rec,) = result.records
    assert rec.hours.verification == "ungrounded" and rec.hours.confidence == "low"
    assert any(f.code == "UNGROUNDED_VALUE" and f.field == "hours" for f in rec.flags)
    assert rec.gross_cents.verification == "grounded"
    assert rec.person_name.verification == "grounded"
    verify_stage = next(s for s in result.pipeline if s.stage == "verify")
    assert verify_stage.status == "warning"


def test_upload_image_without_reader_asks_for_manual_entry(client):
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "white").save(buf, format="PNG")
    app.dependency_overrides[get_llm_client] = lambda: None
    res = client.post(
        "/api/documents",
        files={"file": ("scan.png", buf.getvalue(), "image/png")},
        data={"doc_id": "doc-2", "doc_type_hint": "paystub"},
    )
    result = DocumentResult.model_validate(res.json())
    assert result.doc_type == "paystub" and result.extractor == "none"
    assert result.records == [] and "Enter the values manually." in result.warnings
    stages = {s.stage: s.status for s in result.pipeline}
    assert stages["normalize"] == stages["verify"] == "skipped"
