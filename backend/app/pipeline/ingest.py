"""Ingest stage: file type/size checks, sha256, page count. In memory only."""

import hashlib
import io
from dataclasses import dataclass
from pathlib import PurePath
from typing import Literal

import pypdfium2 as pdfium
from PIL import Image

from app.errors import ApiError

FileKind = Literal["pdf", "image"]

MAX_PDF_PAGES = 10
_EXT_KIND: dict[str, FileKind] = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
}
_MIME_KIND: dict[str, FileKind] = {
    "application/pdf": "pdf",
    "image/png": "image",
    "image/jpeg": "image",
    "image/jpg": "image",
}
# Clients often send these when they don't know the type; the extension decides then.
_GENERIC_MIME = {"", "application/octet-stream"}


@dataclass(frozen=True)
class IngestedFile:
    file_name: str
    kind: FileKind
    data: bytes
    sha256: str
    size_bytes: int
    page_count: int


def _unsupported(message: str, **details: object) -> ApiError:
    return ApiError("UNSUPPORTED_FILE", message, status=415, details=details or None)


def ingest(
    file_name: str, content_type: str | None, data: bytes, max_upload_mb: int
) -> IngestedFile:
    ext = PurePath(file_name or "").suffix.lower()
    kind = _EXT_KIND.get(ext)
    if kind is None:
        raise _unsupported("Upload a PDF, PNG, or JPG file.", extension=ext or None)

    mime = (content_type or "").split(";")[0].strip().lower()
    if mime not in _GENERIC_MIME and _MIME_KIND.get(mime) != kind:
        raise _unsupported("The file type does not match its name.", contentType=mime)

    size = len(data)
    if size == 0:
        raise _unsupported("The file is empty.")
    if size > max_upload_mb * 1024 * 1024:
        raise _unsupported(
            f"The file is larger than {max_upload_mb} MB.", sizeBytes=size
        )

    if kind == "pdf":
        page_count = _pdf_page_count(data)
        if page_count < 1 or page_count > MAX_PDF_PAGES:
            raise _unsupported(
                f"PDFs must have 1 to {MAX_PDF_PAGES} pages.", pageCount=page_count
            )
    else:
        _check_image(data)
        page_count = 1

    return IngestedFile(
        file_name=file_name,
        kind=kind,
        data=data,
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=size,
        page_count=page_count,
    )


def _pdf_page_count(data: bytes) -> int:
    try:
        pdf = pdfium.PdfDocument(data)
    except Exception as exc:  # pypdfium2 raises PdfiumError for unreadable files
        raise _unsupported("The PDF could not be opened.") from exc
    try:
        return len(pdf)
    finally:
        pdf.close()


def _check_image(data: bytes) -> None:
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format not in {"PNG", "JPEG"}:
                raise _unsupported("Upload a PDF, PNG, or JPG file.", format=img.format)
            img.verify()
    except ApiError:
        raise
    except Exception as exc:
        raise _unsupported("The image could not be opened.") from exc
