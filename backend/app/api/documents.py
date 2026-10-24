"""POST /documents: runs the document pipeline on one upload (in memory)."""
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.pipeline.extract.llm import LlmClient, make_llm_client
from app.pipeline.orchestrator import process_document
from app.schemas.api import DocumentResult
from app.schemas.common import DocType
from app.settings import get_settings

router = APIRouter(tags=["documents"])


def get_llm_client() -> LlmClient | None:
    """None in demo mode. Overridable in tests."""
    return make_llm_client(get_settings())


@router.post("/documents", response_model=DocumentResult)
async def post_document(
    file: Annotated[UploadFile, File()],
    doc_id: Annotated[str, Form()],
    llm: Annotated[LlmClient | None, Depends(get_llm_client)],
    doc_type_hint: Annotated[DocType | None, Form()] = None,
) -> DocumentResult:
    data = await file.read()
    return process_document(
        file_name=file.filename or "",
        content_type=file.content_type,
        data=data,
        doc_id=doc_id,
        settings=get_settings(),
        doc_type_hint=doc_type_hint,
        llm=llm,
    )
