"""B7: ingest, render, classify on the generated samples (offline / demo mode)."""

import io
import random

import pytest
from hypothesis import given
from hypothesis import settings as hsettings
from hypothesis import strategies as st
from PIL import Image

from app.errors import ApiError
from app.mocks.jorge import JORGE_SAMPLES
from app.pipeline.classify import KEYWORDS, classify, classify_keywords, llm_classify
from app.pipeline.ingest import ingest
from app.pipeline.render import PageContent, render
from app.settings import Settings, get_settings

SAMPLES_DIR = get_settings().samples_dir
DEMO = Settings(llm_provider="", model_id="")


def _random_png(seed: int = 7) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (64, 48))
    img.putdata(
        [
            (rng.randrange(256), rng.randrange(256), rng.randrange(256))
            for _ in range(64 * 48)
        ]
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.mark.parametrize("sample", JORGE_SAMPLES, ids=lambda s: s.name)
def test_each_sample_classifies_offline(sample):
    data = (SAMPLES_DIR / sample.name).read_bytes()
    file = ingest(sample.name, "application/pdf", data, max_upload_mb=10)
    assert file.kind == "pdf" and file.page_count >= 1 and len(file.sha256) == 64
    pages = render(file, with_images=False)
    assert pages and all(p.image_png is None and p.text.strip() for p in pages)
    result = classify(pages, DEMO)
    assert (result.doc_type, result.method, result.confidence) == (
        sample.doc_type,
        "keywords",
        "high",
    )


def test_seven_samples_exist():
    assert len(JORGE_SAMPLES) == 7


def test_random_png_without_text_is_unknown_in_demo_mode():
    file = ingest("photo.png", "image/png", _random_png(), max_upload_mb=10)
    pages = render(file, with_images=True)
    assert pages[0].text == "" and pages[0].image_png.startswith(b"\x89PNG")
    result = classify(pages, DEMO)
    assert (result.doc_type, result.method) == ("unknown", "none")


def test_hint_wins_over_keywords():
    pages = [PageContent(1, "Harbor Cafe Pay Stub Pay period Gross pay", None)]
    assert (
        classify(pages, DEMO, doc_type_hint="school_letter").doc_type == "school_letter"
    )


def test_render_pdf_images_when_requested():
    data = (SAMPLES_DIR / "harbor_cafe_paystub.pdf").read_bytes()
    pages = render(ingest("x.pdf", None, data, 10), with_images=True)
    assert pages[0].image_png.startswith(b"\x89PNG")


class _FakeLlm:
    def __init__(self, answer):
        self.answer = answer
        self.calls = 0

    def classify(self, pages):
        self.calls += 1
        return self.answer


def test_llm_stub_returns_none_in_demo_mode():
    fake = _FakeLlm("paystub")
    assert llm_classify([], DEMO, fake) is None and fake.calls == 0


def test_llm_used_when_configured_and_no_keyword_match():
    live = Settings(llm_provider="anthropic", model_id="m")
    pages = [PageContent(1, "", b"png")]
    assert classify(pages, live, client=_FakeLlm("paystub")).method == "llm"
    assert classify(pages, live, client=_FakeLlm("not-a-type")).doc_type == "unknown"


def test_single_keyword_hit_is_not_enough():
    assert classify_keywords("Driver: Jorge Ramos") is None


@pytest.mark.parametrize(
    ("name", "ctype", "data"),
    [
        ("notes.txt", "text/plain", b"hello"),
        ("doc.pdf", "image/png", b"%PDF-1.4"),
        ("empty.pdf", "application/pdf", b""),
        ("broken.pdf", "application/pdf", b"not a pdf"),
        ("broken.png", "image/png", b"not an image"),
    ],
)
def test_ingest_rejects_unsupported(name, ctype, data):
    with pytest.raises(ApiError) as exc:
        ingest(name, ctype, data, max_upload_mb=10)
    assert exc.value.code == "UNSUPPORTED_FILE"


def test_ingest_rejects_oversize():
    with pytest.raises(ApiError) as exc:
        ingest("big.png", "image/png", b"\0" * (1024 * 1024 + 1), max_upload_mb=1)
    assert exc.value.code == "UNSUPPORTED_FILE"


_phrases = st.sampled_from(
    [kw for kws in KEYWORDS.values() for kw in kws] + ["hello", "Jorge Ramos"]
)


@hsettings(max_examples=200, deadline=None)
@given(st.lists(_phrases, max_size=8))
def test_keyword_classifier_needs_two_hits_and_unique_best(parts):
    """Offline classifier result has >= 2 hits and strictly beats every other type."""
    text = " ".join(parts)
    result = classify_keywords(text)
    lowered = text.lower()
    scores = {t: sum(kw in lowered for kw in kws) for t, kws in KEYWORDS.items()}
    if result is not None:
        assert scores[result] >= 2
        assert all(s < scores[result] for t, s in scores.items() if t != result)
    else:
        best = max(scores.values())
        assert best < 2 or sum(s == best for s in scores.values()) > 1
