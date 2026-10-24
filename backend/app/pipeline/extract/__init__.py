"""Extract stage: template parser first, then the LLM (if configured), else none."""

from dataclasses import dataclass, field
from typing import Literal

from app.pipeline.extract.llm import LlmClient
from app.pipeline.extract.models import RawExtraction
from app.pipeline.extract.template import extract_template
from app.pipeline.render import PageContent
from app.schemas.common import DocType

Extractor = Literal["template", "llm", "none"]

MANUAL_ENTRY_WARNING = "Enter the values manually."
LLM_FAILED_WARNING = "The document reader could not read this document."


@dataclass
class ExtractOutcome:
    extractor: Extractor
    result: RawExtraction
    warnings: list[str] = field(default_factory=list)


def extract(
    doc_type: DocType, pages: list[PageContent], llm: LlmClient | None = None
) -> ExtractOutcome:
    """Template when the text matches a known layout; otherwise the LLM; otherwise none
    (no records and a warning asking for manual entry)."""
    if doc_type != "unknown":
        templated = extract_template(doc_type, pages)
        if templated is not None:
            return ExtractOutcome("template", templated)
        if llm is not None:
            result = llm.extract(doc_type, pages)
            if result is not None and (result.records or result.notice):
                return ExtractOutcome("llm", result)
            return ExtractOutcome(
                "none", RawExtraction(), [LLM_FAILED_WARNING, MANUAL_ENTRY_WARNING]
            )
    return ExtractOutcome("none", RawExtraction(), [MANUAL_ENTRY_WARNING])


__all__ = ["MANUAL_ENTRY_WARNING", "ExtractOutcome", "Extractor", "extract"]
