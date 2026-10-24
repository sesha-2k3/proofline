"""Runs the document pipeline for one upload, in memory, and records a stage trace.

ingest -> render -> classify -> extract -> normalize -> verify.
Nothing is written to disk or kept after the request.
"""
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeVar

from app.pipeline.classify import classify
from app.pipeline.extract import MANUAL_ENTRY_WARNING, extract
from app.pipeline.extract.llm import LlmClient
from app.pipeline.ingest import ingest
from app.pipeline.normalize import normalize
from app.pipeline.render import render
from app.pipeline.verify import verify
from app.rules import accessors
from app.schemas.api import DocumentResult
from app.schemas.common import DocType
from app.schemas.evidence import PipelineStage
from app.settings import Settings

UNKNOWN_WARNING = "Could not recognize this document. Choose its type."

T = TypeVar("T")
StageName = Literal["ingest", "render", "classify", "extract", "normalize", "verify"]
Status = Literal["ok", "warning", "failed", "skipped"]


@dataclass
class _Trace:
    stages: list[PipelineStage]

    def run(self, name: StageName, fn: Callable[[], T]) -> tuple[T, int]:
        start = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:
            self.add(name, "failed", _ms(start), str(exc) or type(exc).__name__)
            raise
        return result, _ms(start)

    def add(self, name: StageName, status: Status, duration_ms: int, detail: str) -> None:
        self.stages.append(
            PipelineStage(stage=name, status=status, duration_ms=duration_ms, detail=detail)
        )


def _ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def process_document(
    *,
    file_name: str,
    content_type: str | None,
    data: bytes,
    doc_id: str,
    settings: Settings,
    doc_type_hint: DocType | None = None,
    llm: LlmClient | None = None,
) -> DocumentResult:
    """Raises ApiError(UNSUPPORTED_FILE) from ingest; every later stage is traced."""
    trace = _Trace([])
    warnings: list[str] = []

    file, ms = trace.run(
        "ingest",
        lambda: ingest(file_name, content_type, data, settings.max_upload_mb),
    )
    trace.add("ingest", "ok", ms, f"{file.kind}, {file.page_count} page(s), sha256 {file.sha256[:12]}")

    pages, ms = trace.run("render", lambda: render(file, with_images=llm is not None))
    with_text = sum(1 for p in pages if p.text.strip())
    trace.add("render", "ok", ms, f"{len(pages)} page(s), {with_text} with a text layer")

    cls, ms = trace.run("classify", lambda: classify(pages, settings, doc_type_hint, llm))
    if cls.doc_type == "unknown":
        warnings.append(UNKNOWN_WARNING)
        trace.add("classify", "warning", ms, "unknown document type")
    else:
        trace.add("classify", "ok", ms, f"{cls.doc_type} ({cls.method})")

    outcome, ms = trace.run("extract", lambda: extract(cls.doc_type, pages, llm))
    for w in outcome.warnings:
        if w not in warnings:
            warnings.append(w)
    extracted = bool(outcome.result.records or outcome.result.notice)
    if outcome.extractor == "none":
        trace.add("extract", "warning" if cls.doc_type != "unknown" else "skipped", ms,
                  MANUAL_ENTRY_WARNING)
    else:
        trace.add("extract", "ok", ms, f"{outcome.extractor} extractor")

    records, notice = [], None
    if extracted:
        (records, notice), ms = trace.run(
            "normalize", lambda: normalize(cls.doc_type, outcome.result, doc_id)
        )
        trace.add("normalize", "ok", ms, f"{len(records)} record(s)" + (", notice" if notice else ""))
        (records, notice, report), ms = trace.run(
            "verify", lambda: verify(records, notice, pages)
        )
        clean = report.ungrounded == 0 and report.flags == 0 and not report.notes
        trace.add("verify", "ok" if clean else "warning", ms, report.detail)
    else:
        trace.add("normalize", "skipped", 0, "nothing extracted")
        trace.add("verify", "skipped", 0, "nothing extracted")

    return DocumentResult(
        doc_id=doc_id,
        file_name=file_name,
        doc_type=cls.doc_type,
        classification_confidence=cls.confidence,
        extractor=outcome.extractor,
        records=records,
        notice=notice,
        pipeline=trace.stages,
        warnings=warnings,
        demo_mode=settings.demo_mode,
        rules_version=accessors.rules_version(),
    )
