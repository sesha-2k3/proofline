"""Classify stage: hint > offline keywords > LLM (when configured) > "unknown"."""

from dataclasses import dataclass
from typing import Literal, Protocol, get_args

from app.pipeline.render import PageContent
from app.schemas.common import Confidence, DocType
from app.settings import Settings

ClassifyMethod = Literal["hint", "keywords", "llm", "none"]

# BUILD_PLAN Appendix "Keywords": case-insensitive, highest score wins, need >= 2 hits.
KEYWORDS: dict[DocType, tuple[str, ...]] = {
    "rfi_notice": ("request for information", "masshealth", "respond by"),
    "gig_earnings": ("earnings summary", "active hours", "driver"),
    "employer_statement": ("statement of hours", "hours worked", "employer"),
    "volunteer_letter": ("volunteer", "organization", "service letter"),
    "paystub": ("pay stub", "pay period", "gross pay"),
    "school_letter": ("enrollment", "half-time", "registrar"),
}
MIN_KEYWORD_HITS = 2
_DOC_TYPES: frozenset[str] = frozenset(get_args(DocType))


@dataclass(frozen=True)
class Classification:
    doc_type: DocType
    confidence: Confidence
    method: ClassifyMethod


class LlmClassifier(Protocol):
    def classify(self, pages: list[PageContent]) -> str | None: ...


def keyword_scores(text: str) -> dict[DocType, int]:
    lowered = text.lower()
    return {
        doc_type: sum(1 for kw in kws if kw in lowered)
        for doc_type, kws in KEYWORDS.items()
    }


def classify_keywords(text: str) -> DocType | None:
    """Return the single best-scoring type with >= 2 hits; None if no match or a tie."""
    scores = keyword_scores(text)
    best = max(scores.values(), default=0)
    if best < MIN_KEYWORD_HITS:
        return None
    winners = [doc_type for doc_type, score in scores.items() if score == best]
    return winners[0] if len(winners) == 1 else None


def llm_classify(
    pages: list[PageContent], settings: Settings, client: LlmClassifier | None = None
) -> DocType | None:
    """LLM classification on page images. None in demo mode, without a client, or on bad output."""
    if settings.demo_mode or client is None:
        return None
    result = client.classify(pages)
    return result if result in _DOC_TYPES else None  # type: ignore[return-value]


def classify(
    pages: list[PageContent],
    settings: Settings,
    doc_type_hint: DocType | None = None,
    client: LlmClassifier | None = None,
) -> Classification:
    if doc_type_hint:
        return Classification(doc_type_hint, "high", "hint")

    text = "\n".join(p.text for p in pages)
    if text.strip():
        doc_type = classify_keywords(text)
        if doc_type is not None:
            return Classification(doc_type, "high", "keywords")

    llm_type = llm_classify(pages, settings, client)
    if llm_type is not None and llm_type != "unknown":
        return Classification(llm_type, "low", "llm")

    return Classification("unknown", "low", "none")
