"""Safe, deterministic document loading and chunking tests."""

from pathlib import Path

import pytest

from backend.app.ingestion.loaders import DocumentLoadError, chunk_document, load_document


def test_markdown_loader_normalizes_source_and_creates_stable_chunks(tmp_path: Path) -> None:
    path = tmp_path / "../unsafe-name.md"
    path = tmp_path / "unsafe-name.md"
    path.write_text("# Safe title\n\n" + "alpha beta gamma " * 12, encoding="utf-8")

    first = load_document(path)
    second = load_document(path)
    chunks = chunk_document(first, chunk_size=64, overlap=16)

    assert first.source_name == "unsafe-name.md"
    assert first.title == "Safe title"
    assert first.id == second.id
    assert len(chunks) > 1
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))
    assert chunks[0].id == chunk_document(second, chunk_size=64, overlap=16)[0].id
    assert all(chunk.metadata["source"] == "unsafe-name.md" for chunk in chunks)


def test_text_loader_validates_boundaries_and_overlap(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("0123456789" * 12, encoding="utf-8")
    document = load_document(path)
    chunks = chunk_document(document, chunk_size=40, overlap=10)

    assert chunks[0].content[-10:] == chunks[1].content[:10]
    with pytest.raises(ValueError, match="overlap"):
        chunk_document(document, chunk_size=32, overlap=32)
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_document(document, chunk_size=8, overlap=0)


def test_pdf_loader_preserves_page_metadata_without_network(tmp_path: Path) -> None:
    path = tmp_path / "brief.pdf"
    path.write_bytes(b"%PDF-1.7 fake fixture")

    document = load_document(path, pdf_page_reader=lambda _: ["Page one", "Page two details"])
    chunks = chunk_document(document, chunk_size=64, overlap=8)

    assert document.document_type == "pdf"
    assert [chunk.metadata["page"] for chunk in chunks] == [1, 2]
    assert "Page one" in document.content


@pytest.mark.parametrize("name", ["empty.md", "empty.txt"])
def test_loader_rejects_empty_documents(tmp_path: Path, name: str) -> None:
    path = tmp_path / name
    path.write_text("   \n", encoding="utf-8")
    with pytest.raises(DocumentLoadError, match="empty"):
        load_document(path)


def test_loader_rejects_unsupported_and_oversized_input(tmp_path: Path) -> None:
    unsupported = tmp_path / "payload.exe"
    unsupported.write_bytes(b"not a document")
    with pytest.raises(DocumentLoadError, match="Unsupported"):
        load_document(unsupported)

    large = tmp_path / "large.txt"
    large.write_text("abcdef", encoding="utf-8")
    with pytest.raises(DocumentLoadError, match="maximum"):
        load_document(large, max_bytes=5)
