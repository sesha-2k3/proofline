"""B6: synthetic sample PDFs have real text layers with the banner and every ground-truth evidence line."""

import json
import re

import pypdfium2 as pdfium

from app.mocks.jorge import JORGE_NOTICE, JORGE_RECORDS, JORGE_SAMPLES
from scripts.generate_synthetic import BANNER, generate


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _page_texts(path) -> list[str]:
    pdf = pdfium.PdfDocument(str(path))
    try:
        return [_norm(pdf[i].get_textpage().get_text_range()) for i in range(len(pdf))]
    finally:
        pdf.close()


def _evidence_lines(model) -> list[str]:
    dumped = model.model_dump()
    return [v["evidence"] for v in dumped.values() if isinstance(v, dict) and v.get("evidence")]


def test_generates_seven_pdfs_with_banner_and_grounded_lines(tmp_path):
    truth_path = tmp_path / "ground_truth.json"
    written = generate(tmp_path / "samples", truth_path)

    assert sorted(p.name for p in written) == sorted(s.name for s in JORGE_SAMPLES)
    assert len(written) == 7

    for path in written:
        pages = _page_texts(path)
        assert pages, path.name
        for text in pages:
            assert text.startswith(BANNER), path.name
        full = " ".join(pages)
        models = [r for r in JORGE_RECORDS if r.doc_id == path.name]
        if path.name == "rfi_notice.pdf":
            models.append(JORGE_NOTICE)
        assert models, path.name
        for model in models:
            for line in _evidence_lines(model):
                assert _norm(line) in full, f"{path.name}: missing {line!r}"


def test_ground_truth_matches_jorge_scenario(tmp_path):
    truth_path = tmp_path / "ground_truth.json"
    generate(tmp_path / "samples", truth_path)
    truth = json.loads(truth_path.read_text(encoding="utf-8"))["files"]

    assert set(truth) == {s.name for s in JORGE_SAMPLES}
    record_ids = sorted(r["id"] for f in truth.values() for r in f["records"])
    assert record_ids == sorted(r.id for r in JORGE_RECORDS)

    pantry_may = next(r for r in truth["pantry_letter.pdf"]["records"] if r["periodStart"]["value"] == "2027-05-01")
    assert pantry_may["hours"] == {**pantry_may["hours"], "value": 24.0, "confidence": "low"}
    assert truth["quickdash_2027-05.pdf"]["records"][0]["grossCents"]["value"] == 56000
    assert truth["rfi_notice.pdf"]["notice"]["responseDeadline"]["value"] == "2027-07-12"
