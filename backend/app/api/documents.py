"""Mock POST /documents (B4). Replaced by the real pipeline in B9."""

from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile

from app.mocks.jorge import JORGE_NOTICE, JORGE_RECORDS, JORGE_SAMPLES
from app.rules import accessors
from app.schemas.api import DocumentResult
from app.schemas.common import DocType
from app.schemas.evidence import PipelineStage
from app.settings import get_settings

router = APIRouter(tags=["documents"])

UNKNOWN_WARNING = "Could not recognize this document. Choose its type."
_STAGES = ("ingest", "render", "classify", "extract", "normalize", "verify")


def _trace(recognized: bool) -> list[PipelineStage]:
    stages = []
    for name in _STAGES:
        status = "ok" if recognized or name in ("ingest", "render") else "skipped"
        stages.append(PipelineStage(stage=name, status=status, duration_ms=1, detail="mock"))
    return stages


@router.post("/documents", response_model=DocumentResult)
async def post_document(
    file: Annotated[UploadFile, File()],
    doc_id: Annotated[str, Form()],
    doc_type_hint: Annotated[DocType | None, Form()] = None,
) -> DocumentResult:
    await file.read()
    name = file.filename or ""
    sample = next((s for s in JORGE_SAMPLES if s.name == name), None)
    common = {"doc_id": doc_id, "file_name": name, "demo_mode": get_settings().demo_mode,
              "rules_version": accessors.rules_version()}
    if sample is None:
        return DocumentResult(
            **common,
            doc_type=doc_type_hint or "unknown",
            classification_confidence="low",
            extractor="none",
            records=[],
            pipeline=_trace(False),
            warnings=[UNKNOWN_WARNING],
        )
    records = [r.model_copy(update={"doc_id": doc_id}, deep=True) for r in JORGE_RECORDS if r.doc_id == name]
    return DocumentResult(
        **common,
        doc_type=sample.doc_type,
        classification_confidence="high",
        extractor="template",
        records=records,
        notice=JORGE_NOTICE if sample.doc_type == "rfi_notice" else None,
        pipeline=_trace(True),
        warnings=[],
    )
