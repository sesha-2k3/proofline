"""Prompts for the LLM classifier and extractor. The LLM only reads documents;
code decides everything about eligibility."""

from app.pipeline.render import PageContent
from app.schemas.common import DocType

CLASSIFY_DOC_TYPES: tuple[DocType, ...] = (
    "rfi_notice",
    "paystub",
    "employer_statement",
    "gig_earnings",
    "volunteer_letter",
    "school_letter",
    "unknown",
)

CLASSIFY_PROMPT = (
    "You are reading a document a benefits navigator uploaded for a client.\n"
    "Decide which type of document it is. Choose exactly one of: "
    + ", ".join(CLASSIFY_DOC_TYPES)
    + ".\n"
    "- rfi_notice: a MassHealth Request for Information or similar notice.\n"
    "- paystub: an employer pay stub for a pay period.\n"
    "- employer_statement: a signed statement of hours worked from an employer.\n"
    "- gig_earnings: an earnings summary from a gig or delivery app.\n"
    "- volunteer_letter: a letter from an organization about volunteer hours.\n"
    "- school_letter: a school or training enrollment letter.\n"
    "- unknown: anything else, or you cannot tell.\n"
    'Return JSON only, with no other text: {"doc_type": "<type>"}'
)

FIELD_RULES = (
    "Return JSON only, with no other text and no code fences.\n"
    "Every field is an object: "
    '{"value": ..., "confidence": "high" | "low", "page": <page number starting at 1>, '
    '"evidence": "<the exact text you read for this value>"}.\n'
    "Rules:\n"
    "- Use null for the value instead of guessing. Leave a field out if the document "
    "does not have it.\n"
    '- Use "low" confidence when the text is unclear, handwritten, or partially visible.\n'
    '- Copy money as printed (for example "$320.00"). Copy hours as a number '
    "(for example 14.00).\n"
    "- Write dates as YYYY-MM-DD.\n"
    '- Make one entry in "records" per month or pay period on the document.\n'
    "- Do not decide whether anyone qualifies for anything. Only report what the "
    "document says.\n"
)

_COMMON = ("person_name", "issuer", "period_start", "period_end", "document_date")

DOC_FIELDS: dict[DocType, tuple[str, ...]] = {
    "paystub": _COMMON + ("hours", "hourly_rate_cents", "gross_cents"),
    "employer_statement": _COMMON + ("hours", "gross_cents"),
    "gig_earnings": _COMMON + ("hours", "gross_cents", "expenses_cents"),
    "volunteer_letter": _COMMON + ("org_type", "non_partisan", "hours"),
    "school_letter": _COMMON + ("half_time_enrolled",),
}

FIELD_HELP: dict[str, str] = {
    "person_name": "the worker, volunteer, or student named on the document",
    "issuer": "the employer, company, school, or organization that issued it",
    "period_start": "first day of the period the entry covers",
    "period_end": "last day of the period the entry covers",
    "document_date": "the date the document was issued, signed, or paid",
    "hours": "hours for the period",
    "hourly_rate_cents": "hourly pay rate, as printed",
    "gross_cents": "gross pay or gross earnings for the period, as printed",
    "expenses_cents": "expenses listed for the period (for example mileage), as printed",
    "org_type": 'one of "public", "nonprofit", "for_profit", "political", "unknown"',
    "non_partisan": "true if the document says the organization is non-partisan, "
    "false if it says it is partisan",
    "half_time_enrolled": "true if the document says the student is enrolled at least "
    "half-time",
}

NOTICE_FIELDS: dict[str, str] = {
    "notice_date": "the date of the notice",
    "response_deadline": "the date the response is due",
    "request_summary": "one sentence that says what the notice asks for, "
    "in the notice's own words",
}

RETRY_NOTE = (
    "Your previous reply could not be read as the JSON described. "
    "Reply again with JSON only."
)


def _page_text_block(pages: list[PageContent]) -> str:
    parts = []
    for p in pages:
        text = p.text.strip() or "(no text layer; read the page image)"
        parts.append(f"--- Page {p.page} text ---\n{text}")
    return "\n".join(parts)


def extraction_prompt(doc_type: DocType, pages: list[PageContent]) -> str:
    """Per-doc-type extraction prompt. Page images are sent alongside this text."""
    if doc_type == "rfi_notice":
        fields = "\n".join(f'- "{k}": {v}' for k, v in NOTICE_FIELDS.items())
        shape = '{"records": [], "notice": {<fields>}}'
    else:
        names = DOC_FIELDS.get(doc_type, _COMMON)
        fields = "\n".join(f'- "{k}": {FIELD_HELP[k]}' for k in names)
        shape = '{"records": [{<fields>}, ...], "notice": null}'
    return (
        f"You are reading a document of type {doc_type}.\n"
        f"Extract these fields:\n{fields}\n\n"
        f"Answer with this shape: {shape}\n\n"
        f"{FIELD_RULES}\n"
        f"{_page_text_block(pages)}"
    )


def classification_prompt(pages: list[PageContent]) -> str:
    return f"{CLASSIFY_PROMPT}\n\n{_page_text_block(pages)}"


def rephrase_prompt(text: str, lang: str) -> str:
    """Ask the LLM to reword a code-written summary. It may not add, drop, or change facts or numbers."""
    language = "Spanish" if lang == "es" else "English"
    return (
        f"Rewrite this summary in plain {language} at about a 6th-grade reading level. "
        "Keep every number, date, and dollar amount exactly as written. "
        "Do not add facts, advice, or opinions. Do not say whether the person is eligible or exempt. "
        "Keep the sentence saying MassHealth makes the final decision. "
        'Return JSON only: {"text": "<rewritten summary>"}\n\n'
        f"Summary:\n{text}"
    )
