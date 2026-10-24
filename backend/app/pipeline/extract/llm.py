"""LLM classifier/extractor (anthropic or Bedrock). Disabled when LLM_PROVIDER is empty.

The LLM only reads documents and reports values with confidence, page, and evidence.
It never decides eligibility. Replies are parsed as JSON and validated with the raw
Pydantic models; one retry on a bad reply, then give up (None).
"""

import base64
import json
import re
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from app.pipeline.extract.models import RawExtraction
from app.pipeline.extract.prompts import (
    CLASSIFY_DOC_TYPES,
    RETRY_NOTE,
    classification_prompt,
    extraction_prompt,
    rephrase_prompt,
)
from app.pipeline.render import PageContent
from app.schemas.common import DocType
from app.settings import Settings

MAX_TOKENS = 4096
MAX_ATTEMPTS = 2  # first try + one retry


class Transport(Protocol):
    """Sends one user turn (page images + prompt text) and returns the reply text."""

    def send(self, prompt: str, images: list[bytes]) -> str: ...


class AnthropicTransport:
    def __init__(self, api_key: str, model_id: str, client: Any = None):
        if client is None:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
        self._client = client
        self._model_id = model_id

    def send(self, prompt: str, images: list[bytes]) -> str:
        content: list[dict[str, Any]] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.b64encode(png).decode("ascii"),
                },
            }
            for png in images
        ]
        content.append({"type": "text", "text": prompt})
        response = self._client.messages.create(
            model=self._model_id,
            max_tokens=MAX_TOKENS,
            temperature=0,
            messages=[{"role": "user", "content": content}],
        )
        return "".join(
            getattr(block, "text", "")
            for block in response.content
            if getattr(block, "type", "text") == "text"
        )


class BedrockTransport:
    def __init__(self, region: str, model_id: str, client: Any = None):
        if client is None:
            import boto3

            client = boto3.client("bedrock-runtime", region_name=region)
        self._client = client
        self._model_id = model_id

    def send(self, prompt: str, images: list[bytes]) -> str:
        content: list[dict[str, Any]] = [
            {"image": {"format": "png", "source": {"bytes": png}}} for png in images
        ]
        content.append({"text": prompt})
        response = self._client.converse(
            modelId=self._model_id,
            messages=[{"role": "user", "content": content}],
            inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": 0},
        )
        blocks = response["output"]["message"]["content"]
        return "".join(block.get("text", "") for block in blocks)


class _ClassifyReply(BaseModel):
    doc_type: str


class _RephraseReply(BaseModel):
    text: str


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


def parse_json_object(text: str) -> Any:
    """Parse the first JSON object in a reply (tolerates code fences and stray text)."""
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in reply")
    return json.loads(cleaned[start : end + 1])


class LlmClient:
    def __init__(self, transport: Transport):
        self._transport = transport

    def _ask[M: BaseModel](
        self, prompt: str, pages: list[PageContent], model: type[M]
    ) -> M | None:
        images = [p.image_png for p in pages if p.image_png]
        current = prompt
        for _ in range(MAX_ATTEMPTS):
            try:
                reply = self._transport.send(current, images)
                return model.model_validate(parse_json_object(reply))
            except (ValueError, ValidationError):
                current = f"{prompt}\n\n{RETRY_NOTE}"
            except Exception:  # noqa: BLE001 - any SDK/network error: give up, caller warns
                return None
        return None

    def classify(self, pages: list[PageContent]) -> str | None:
        reply = self._ask(classification_prompt(pages), pages, _ClassifyReply)
        if reply is None or reply.doc_type not in CLASSIFY_DOC_TYPES:
            return None
        return reply.doc_type

    def extract(
        self, doc_type: DocType, pages: list[PageContent]
    ) -> RawExtraction | None:
        return self._ask(extraction_prompt(doc_type, pages), pages, RawExtraction)

    def rephrase(self, text: str, lang: str) -> str | None:
        """Reword a code-written summary (the caller checks that every number is unchanged)."""
        reply = self._ask(rephrase_prompt(text, lang), [], _RephraseReply)
        return None if reply is None else reply.text


def make_llm_client(settings: Settings) -> LlmClient | None:
    """None in demo mode (no provider or model id)."""
    if settings.demo_mode:
        return None
    if settings.llm_provider == "anthropic":
        return LlmClient(
            AnthropicTransport(settings.anthropic_api_key, settings.model_id)
        )
    if settings.llm_provider == "bedrock":
        return LlmClient(BedrockTransport(settings.aws_region, settings.model_id))
    return None
