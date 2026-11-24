"""Validated offline loaders and deterministic character chunking."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MAX_BYTES = 10 * 1024 * 1024
SUPPORTED_TYPES = {".md": "markdown", ".txt": "text", ".pdf": "pdf"}


class DocumentLoadError(ValueError):
    """Raised when a source cannot safely become an ingestible document."""


@dataclass(frozen=True)
class SourceSection:
    content: str
    page: int | None = None


@dataclass(frozen=True)
class LoadedDocument:
    id: str
    title: str
    source_name: str
    document_type: str
    content: str
    content_sha256: str
    sections: tuple[SourceSection, ...]


@dataclass(frozen=True)
class DocumentChunkData:
    id: str
    document_id: str
    ordinal: int
    content: str
    metadata: dict[str, Any]


PdfPageReader = Callable[[Path], list[str]]


def _read_pdf_pages(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise DocumentLoadError("PDF loading requires the 'pypdf' package") from exc
    try:
        reader = PdfReader(path)
        return [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:
        raise DocumentLoadError("PDF could not be parsed") from exc


def load_document(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    pdf_page_reader: PdfPageReader | None = None,
) -> LoadedDocument:
    """Load one supported local file without leaking its parent path into metadata."""

    path = Path(path)
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    document_type = SUPPORTED_TYPES.get(path.suffix.lower())
    if document_type is None:
        raise DocumentLoadError(f"Unsupported document type: {path.suffix or '<none>'}")
    if not path.is_file():
        raise DocumentLoadError("Document path must be an existing file")
    size = path.stat().st_size
    if size == 0:
        raise DocumentLoadError("Document is empty")
    if size > max_bytes:
        raise DocumentLoadError("Document exceeds the maximum allowed size")

    if document_type == "pdf":
        pages = (pdf_page_reader or _read_pdf_pages)(path)
        sections = tuple(
            SourceSection(content=text.strip(), page=index)
            for index, text in enumerate(pages, start=1)
            if text.strip()
        )
    else:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DocumentLoadError("Text documents must use UTF-8") from exc
        sections = (SourceSection(content=text.strip()),) if text.strip() else ()

    if not sections:
        raise DocumentLoadError("Document is empty or contains no extractable text")
    content = "\n\n".join(section.content for section in sections)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    source_name = Path(path.name).name
    identity = hashlib.sha256(source_name.casefold().encode()).hexdigest()[:24]
    title = _title_for(source_name, document_type, sections[0].content)
    return LoadedDocument(
        id=f"doc-{identity}",
        title=title,
        source_name=source_name,
        document_type=document_type,
        content=content,
        content_sha256=digest,
        sections=sections,
    )


def _title_for(source_name: str, document_type: str, content: str) -> str:
    if document_type == "markdown":
        for line in content.splitlines():
            if line.startswith("# ") and line[2:].strip():
                return line[2:].strip()[:240]
    return Path(source_name).stem.replace("-", " ").replace("_", " ").strip()[:240]


def chunk_document(
    document: LoadedDocument,
    *,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[DocumentChunkData]:
    """Split each page/section deterministically while preserving source locators."""

    if not 32 <= chunk_size <= 100_000:
        raise ValueError("chunk_size must be between 32 and 100000")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    step = chunk_size - overlap
    chunks: list[DocumentChunkData] = []
    ordinal = 0
    for section in document.sections:
        start = 0
        while start < len(section.content):
            content = section.content[start : start + chunk_size]
            if content.strip():
                chunk_hash = hashlib.sha256(
                    f"{document.id}\0{ordinal}\0{content}".encode()
                ).hexdigest()[:24]
                chunks.append(
                    DocumentChunkData(
                        id=f"chunk-{chunk_hash}",
                        document_id=document.id,
                        ordinal=ordinal,
                        content=content,
                        metadata={
                            "source": document.source_name,
                            "page": section.page,
                            "chunk": ordinal,
                            "start": start,
                        },
                    )
                )
                ordinal += 1
            if start + chunk_size >= len(section.content):
                break
            start += step
    if not chunks:
        raise DocumentLoadError("Document produced no non-empty chunks")
    return chunks
