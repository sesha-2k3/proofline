"""B8: template extraction equals ground truth; LLM client with a fake transport."""

import json
import re
from datetime import datetime

import pytest

from app.mocks.jorge import JORGE_SAMPLES
from app.pipeline.extract import MANUAL_ENTRY_WARNING, extract
from app.pipeline.extract.llm import (
    AnthropicTransport,
    BedrockTransport,
    LlmClient,
    make_llm_client,
)
from app.pipeline.extract.models import RawField
from app.pipeline.extract.template import extract_template
from app.pipeline.ingest import ingest
from app.pipeline.render import PageContent, render
from app.settings import BACKEND_DIR, Settings, get_settings

SAMPLES_DIR = get_settings().samples_dir
GROUND_TRUTH = json.loads(
    (BACKEND_DIR / "synthetic" / "ground_truth.json").read_text()
)["files"]
DEMO = Settings(llm_provider="", model_id="")

RECORD_FIELDS = {
    "personName": "person_name",
    "issuer": "issuer",
    "orgType": "org_type",
    "nonPartisan": "non_partisan",
    "periodStart": "period_start",
    "periodEnd": "period_end",
    "hours": "hours",
    "hourlyRateCents": "hourly_rate_cents",
    "grossCents": "gross_cents",
    "expensesCents": "expenses_cents",
    "halfTimeEnrolled": "half_time_enrolled",
    "documentDate": "document_date",
}
NOTICE_FIELDS = {
    "noticeDate": "notice_date",
    "responseDeadline": "response_deadline",
    "requestSummary": "request_summary",
}


def _canon(name: str, value):
    """Minimal test-side conversion of raw template strings to ground-truth types."""
    if not isinstance(value, str):
        return value
    if name.endswith("_cents"):
        return round(float(value.replace("$", "").replace(",", "")) * 100)
    if name == "hours":
        return float(value)
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return datetime.strptime(value, "%m/%d/%Y").date().isoformat()
    return value


def _assert_field(name: str, raw: RawField | None, truth: dict | None):
    if truth is None:
        assert raw is None, name
        return
    assert raw is not None, name
    assert _canon(name, raw.value) == truth["value"], name
    assert (raw.confidence, raw.page, raw.evidence) == (
        truth["confidence"],
        truth["page"],
        truth["evidence"],
    ), name


def _pages(name: str) -> list[PageContent]:
    data = (SAMPLES_DIR / name).read_bytes()
    return render(
        ingest(name, "application/pdf", data, max_upload_mb=10), with_images=False
    )


@pytest.mark.parametrize("sample", JORGE_SAMPLES, ids=lambda s: s.name)
def test_template_matches_ground_truth(sample):
    truth = GROUND_TRUTH[sample.name]
    result = extract_template(truth["docType"], _pages(sample.name))
    assert result is not None
    assert len(result.records) == len(truth["records"])
    for raw, expected in zip(result.records, truth["records"], strict=True):
        for wire, attr in RECORD_FIELDS.items():
            _assert_field(attr, getattr(raw, attr), expected[wire])
    if truth["notice"] is None:
        assert result.notice is None
    else:
        for wire, attr in NOTICE_FIELDS.items():
            _assert_field(attr, getattr(result.notice, attr), truth["notice"][wire])


def test_pantry_may_hours_low_confidence():
    result = extract_template("volunteer_letter", _pages("pantry_letter.pdf"))
    april, may = result.records
    assert april.hours.confidence == "high"
    assert may.hours.confidence == "low" and may.hours.value == "24.00"


def test_dispatcher_uses_template_for_samples():
    outcome = extract("paystub", _pages("harbor_cafe_paystub.pdf"))
    assert outcome.extractor == "template" and outcome.warnings == []


def test_no_extractor_returns_no_records_and_manual_warning():
    pages = [PageContent(page=1, text="", image_png=b"\x89PNG")]
    for doc_type in ("school_letter", "unknown", "paystub"):
        outcome = extract(doc_type, pages, make_llm_client(DEMO))
        assert outcome.extractor == "none"
        assert outcome.result.records == [] and outcome.result.notice is None
        assert MANUAL_ENTRY_WARNING in outcome.warnings


def test_template_rejects_text_that_does_not_match_layout():
    pages = [PageContent(page=1, text="Pay stub\nsomething else", image_png=None)]
    assert extract_template("paystub", pages) is None


# ---------------------------------------------------------------- LLM (fake transport)

LLM_JSON = {
    "records": [
        {
            "person_name": {
                "value": "Jorge Ramos",
                "confidence": "high",
                "page": 1,
                "evidence": "Employee: Jorge Ramos",
            },
            "hours": {
                "value": 20.0,
                "confidence": "low",
                "page": 1,
                "evidence": "Hours: 20",
            },
            "gross_cents": {
                "value": "$310.00",
                "confidence": "high",
                "page": 1,
                "evidence": "Gross pay: $310.00",
            },
        }
    ],
    "notice": None,
}


class FakeTransport:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.calls: list[tuple[str, list[bytes]]] = []

    def send(self, prompt: str, images: list[bytes]) -> str:
        self.calls.append((prompt, images))
        return self.replies.pop(0)


IMAGE_PAGES = [PageContent(page=1, text="", image_png=b"\x89PNGfake")]


def test_llm_extract_parses_fixed_json():
    transport = FakeTransport([f"```json\n{json.dumps(LLM_JSON)}\n```"])
    result = LlmClient(transport).extract("paystub", IMAGE_PAGES)
    assert result is not None
    rec = result.records[0]
    assert rec.person_name.value == "Jorge Ramos"
    assert (rec.hours.value, rec.hours.confidence, rec.hours.evidence) == (
        20.0,
        "low",
        "Hours: 20",
    )
    prompt, images = transport.calls[0]
    assert images == [b"\x89PNGfake"]
    assert "JSON only" in prompt and "evidence" in prompt


def test_llm_retries_once_then_succeeds():
    transport = FakeTransport(["not json", json.dumps(LLM_JSON)])
    outcome = extract("paystub", IMAGE_PAGES, LlmClient(transport))
    assert outcome.extractor == "llm" and len(transport.calls) == 2
    assert len(outcome.result.records) == 1


def test_llm_gives_up_after_retry():
    bad = json.dumps({"records": [{"hours": {"confidence": "maybe"}}]})
    transport = FakeTransport(["oops", bad])
    outcome = extract("paystub", IMAGE_PAGES, LlmClient(transport))
    assert len(transport.calls) == 2
    assert outcome.extractor == "none" and outcome.result.records == []
    assert MANUAL_ENTRY_WARNING in outcome.warnings


def test_llm_classify():
    client = LlmClient(
        FakeTransport(['{"doc_type": "paystub"}', '{"doc_type": "letter"}'])
    )
    assert client.classify(IMAGE_PAGES) == "paystub"
    assert client.classify(IMAGE_PAGES) is None


def test_make_llm_client_disabled_in_demo_mode():
    assert make_llm_client(DEMO) is None
    assert make_llm_client(Settings(llm_provider="anthropic", model_id="")) is None


class _Obj:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_anthropic_transport_sends_base64_image_blocks():
    captured = {}

    class Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Obj(content=[_Obj(type="text", text='{"doc_type": "paystub"}')])

    transport = AnthropicTransport("k", "model-x", client=_Obj(messages=Messages()))
    assert LlmClient(transport).classify(IMAGE_PAGES) == "paystub"
    content = captured["messages"][0]["content"]
    assert captured["model"] == "model-x"
    assert content[0]["type"] == "image" and content[0]["source"]["type"] == "base64"
    assert content[-1]["type"] == "text"


def test_bedrock_transport_uses_converse_with_image_blocks():
    captured = {}

    class Runtime:
        def converse(self, **kwargs):
            captured.update(kwargs)
            return {
                "output": {
                    "message": {"content": [{"text": '{"doc_type": "rfi_notice"}'}]}
                }
            }

    transport = BedrockTransport("us-east-1", "model-y", client=Runtime())
    assert LlmClient(transport).classify(IMAGE_PAGES) == "rfi_notice"
    content = captured["messages"][0]["content"]
    assert captured["modelId"] == "model-y"
    assert content[0]["image"]["format"] == "png" and "text" in content[-1]
