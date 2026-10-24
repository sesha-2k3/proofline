"""Run the document pipeline over backend/samples and compare it with synthetic/ground_truth.json.

Reports classification accuracy, field accuracy, grounding rate, and false-pass count
(months the ledger on extracted records calls "meets" that the ledger on ground truth does not).
Prints the report and writes docs/eval_report.md.
"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.ledger.evaluate import evaluate_case
from app.mocks.jorge import JORGE_CASE
from app.pipeline.orchestrator import process_document
from app.schemas.evidence import EvidenceRecord
from app.settings import get_settings
from app.validation.checks import validate_records

GROUND_TRUTH = BACKEND_DIR / "synthetic" / "ground_truth.json"
REPORT = BACKEND_DIR.parent / "docs" / "eval_report.md"


@dataclass
class EvalResult:
    files: int = 0
    classified_ok: int = 0
    fields_total: int = 0
    fields_ok: int = 0
    values_extracted: int = 0
    values_grounded: int = 0
    false_pass: dict[str, int] = field(default_factory=dict)
    month_status: dict[str, list[tuple[str, str, str]]] = field(default_factory=dict)
    mismatches: list[str] = field(default_factory=list)

    @property
    def classification_accuracy(self) -> float:
        return self.classified_ok / self.files if self.files else 0.0

    @property
    def field_accuracy(self) -> float:
        return self.fields_ok / self.fields_total if self.fields_total else 0.0

    @property
    def grounding_rate(self) -> float:
        return self.values_grounded / self.values_extracted if self.values_extracted else 0.0

    @property
    def false_pass_count(self) -> int:
        return sum(self.false_pass.values())


def _fields(item: dict) -> dict[str, dict]:
    """Field-shaped entries (dicts with a "value") of a record or notice dumped by alias."""
    return {k: v for k, v in item.items() if isinstance(v, dict) and "value" in v}


def _compare(label: str, truth: dict, got: dict | None, res: EvalResult) -> None:
    truth_fields = _fields(truth)
    got_fields = _fields(got) if got else {}
    for name, t in truth_fields.items():
        res.fields_total += 1
        g = got_fields.get(name)
        if g is not None and g["value"] == t["value"] and g["confidence"] == t["confidence"]:
            res.fields_ok += 1
        else:
            res.mismatches.append(f"{label}.{name}: expected {t['value']!r}, got {g and g['value']!r}")
    for g in got_fields.values():
        if g["value"] is not None:
            res.values_extracted += 1
            res.values_grounded += g["verification"] == "grounded"


def _confirm_low(records: list[EvidenceRecord]) -> list[EvidenceRecord]:
    """Navigator confirms every low-confidence field (the 'after confirmation' scenario)."""
    out = []
    for r in records:
        updates = {}
        for name in type(r).model_fields:
            f = getattr(r, name)
            if hasattr(f, "confidence") and f.confidence == "low" and not f.confirmed:
                updates[name] = f.model_copy(update={"confirmed": True})
        out.append(r.model_copy(update=updates))
    return out


def _ledger(records: list[EvidenceRecord]) -> dict[str, str]:
    months, _ = evaluate_case(JORGE_CASE, validate_records(JORGE_CASE, records))
    return {m.month: m.status for m in months}


def run_eval(samples_dir: Path | None = None) -> EvalResult:
    settings = get_settings()
    samples_dir = samples_dir or settings.samples_dir
    truth_files = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["files"]
    res = EvalResult()
    extracted: list[EvidenceRecord] = []
    truth_records: list[EvidenceRecord] = []

    for name, truth in truth_files.items():
        res.files += 1
        doc = process_document(
            file_name=name,
            content_type="application/pdf",
            data=(samples_dir / name).read_bytes(),
            doc_id=name,
            settings=settings,
        )
        if doc.doc_type == truth["docType"]:
            res.classified_ok += 1
        else:
            res.mismatches.append(f"{name}: classified {doc.doc_type}, expected {truth['docType']}")
        got_by_id = {r.id: r.model_dump(mode="json", by_alias=True) for r in doc.records}
        for t in truth["records"]:
            _compare(f"{name}:{t['id']}", t, got_by_id.pop(t["id"], None), res)
        for extra_id, extra in got_by_id.items():
            _compare(f"{name}:{extra_id}", {}, extra, res)
            res.mismatches.append(f"{name}: unexpected record {extra_id}")
        if truth.get("notice"):
            got_notice = doc.notice.model_dump(mode="json", by_alias=True) if doc.notice else None
            _compare(f"{name}:notice", truth["notice"], got_notice, res)
        extracted += doc.records
        truth_records += [EvidenceRecord.model_validate(t) for t in truth["records"]]

    scenarios = {
        "as extracted": (extracted, truth_records),
        "after navigator confirmation": (_confirm_low(extracted), _confirm_low(truth_records)),
    }
    for scenario, (got, want) in scenarios.items():
        got_status, want_status = _ledger(got), _ledger(want)
        res.month_status[scenario] = [(m, got_status.get(m, "-"), s) for m, s in want_status.items()]
        res.false_pass[scenario] = sum(
            1 for m, s in got_status.items() if s == "meets" and want_status.get(m) != "meets"
        )
    return res


def format_report(res: EvalResult) -> str:
    lines = [
        "# Proofline pipeline evaluation",
        "",
        f"Samples: {res.files} synthetic PDFs in backend/samples, compared with backend/synthetic/ground_truth.json.",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Classification accuracy | {res.classified_ok}/{res.files} ({res.classification_accuracy:.1%}) |",
        f"| Field accuracy (value and confidence) | {res.fields_ok}/{res.fields_total} ({res.field_accuracy:.1%}) |",
        f"| Grounding rate (non-null extracted values) | {res.values_grounded}/{res.values_extracted} ({res.grounding_rate:.1%}) |",
        f"| False-pass count (extracted 'meets' where ground truth is not) | {res.false_pass_count} |",
        "",
    ]
    for scenario, rows in res.month_status.items():
        lines += [
            f"## Ledger by month, {scenario} (false passes: {res.false_pass[scenario]})",
            "",
            "| Month | Extracted | Ground truth |",
            "|---|---|---|",
            *[f"| {m} | {g} | {w} |" for m, g, w in rows],
            "",
        ]
    lines += ["## Mismatches", ""]
    lines += [f"- {m}" for m in res.mismatches] or ["None."]
    return "\n".join(lines) + "\n"


def main() -> None:
    report = format_report(run_eval())
    print(report)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(report, encoding="utf-8")
    print(f"Wrote {REPORT}")


if __name__ == "__main__":
    main()
