"""Repeatable offline command for canonical sample-document ingestion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.core.database import SessionLocal, engine
from backend.app.core.embeddings import get_embedding_model
from backend.app.ingestion.extraction import extract_knowledge
from backend.app.ingestion.loaders import chunk_document, load_document
from backend.app.ingestion.pipeline import IngestionPipeline
from backend.app.models import Base
from rag.graph_store import get_graph_store
from rag.vector_store import get_vector_store

DEFAULT_DOCUMENT_ROOT = Path(__file__).resolve().parents[3] / "sample_data" / "documents"


def _paths(values: list[str]) -> list[Path]:
    if values:
        return [Path(value) for value in values]
    return sorted(path for path in DEFAULT_DOCUMENT_ROOT.iterdir() if path.suffix.lower() == ".md")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest NovaEnterprise documents safely")
    parser.add_argument("paths", nargs="*", help="Markdown, text, or PDF files")
    parser.add_argument("--dry-run", action="store_true", help="validate without writing stores")
    args = parser.parse_args(argv)
    settings = get_settings()
    documents = [load_document(path) for path in _paths(args.paths)]

    if args.dry_run:
        results = []
        for document in documents:
            chunks = chunk_document(document)
            extractions = [
                extract_knowledge(chunk, tenant_id=settings.default_tenant_id) for chunk in chunks
            ]
            results.append(
                {
                    "document_id": document.id,
                    "source": document.source_name,
                    "chunks": len(chunks),
                    "hostile_chunks": sum(item.flagged for item in extractions),
                    "status": "validated",
                }
            )
    else:
        Base.metadata.create_all(engine)
        vector_store = get_vector_store(settings, settings.default_tenant_id)
        graph_store = get_graph_store(settings, settings.default_tenant_id)
        with SessionLocal() as session:
            pipeline = IngestionPipeline(
                session=session,
                tenant_id=settings.default_tenant_id,
                embeddings=get_embedding_model(settings),
                vector_store=vector_store,
                graph_store=graph_store,
            )
            results = [pipeline.index(document).__dict__ for document in documents]
    print(json.dumps(results, indent=2, sort_keys=True))
    return int(any(result["status"] in {"partial", "failed"} for result in results))


if __name__ == "__main__":
    raise SystemExit(main())
