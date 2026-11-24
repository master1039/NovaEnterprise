"""Tenant-scoped coordination of relational, vector, and graph indexing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.embeddings import EmbeddingModel
from backend.app.core.guardrails import redact_secrets
from backend.app.ingestion.extraction import extract_knowledge
from backend.app.ingestion.loaders import LoadedDocument, chunk_document
from backend.app.models import Document, DocumentChunk
from rag.graph_store import GraphEdge, GraphNode, GraphStore
from rag.vector_store import VectorRecord, VectorStore

IngestionStatus = Literal["completed", "partial", "failed"]


@dataclass(frozen=True)
class IngestionResult:
    document_id: str
    status: IngestionStatus
    chunk_count: int
    hostile_chunk_count: int
    entity_count: int
    relationship_count: int
    relational_indexed: bool
    vector_indexed: bool
    graph_indexed: bool
    errors: tuple[str, ...] = ()


class IngestionPipeline:
    def __init__(
        self,
        *,
        session: Session,
        tenant_id: str,
        embeddings: EmbeddingModel,
        vector_store: VectorStore,
        graph_store: GraphStore,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be blank")
        self.session = session
        self.tenant_id = tenant_id
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.graph_store = graph_store
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def index(self, document: LoadedDocument) -> IngestionResult:
        database_id = self._resolve_document_id(document)
        raw_chunks = chunk_document(
            document,
            chunk_size=self.chunk_size,
            overlap=self.chunk_overlap,
        )
        chunks = [
            replace(
                chunk,
                id=self._tenant_id("chunk", chunk.id),
                document_id=database_id,
            )
            for chunk in raw_chunks
        ]
        extracted = [extract_knowledge(chunk, tenant_id=self.tenant_id) for chunk in chunks]
        hostile_count = sum(item.flagged for item in extracted)
        current_ids = {chunk.id for chunk in chunks}
        existing_ids = set(
            self.session.scalars(
                select(DocumentChunk.id).where(
                    DocumentChunk.tenant_id == self.tenant_id,
                    DocumentChunk.document_id == database_id,
                )
            )
        )
        stale_ids = sorted(existing_ids - current_ids)

        try:
            self.session.merge(
                Document(
                    id=database_id,
                    tenant_id=self.tenant_id,
                    title=redact_secrets(document.title),
                    source_path=redact_secrets(document.source_name),
                    document_type=document.document_type,
                    content=redact_secrets(document.content),
                    content_sha256=document.content_sha256,
                    is_untrusted=bool(hostile_count),
                )
            )
            if stale_ids:
                stale_rows = self.session.scalars(
                    select(DocumentChunk).where(
                        DocumentChunk.tenant_id == self.tenant_id,
                        DocumentChunk.id.in_(stale_ids),
                    )
                )
                for row in stale_rows:
                    self.session.delete(row)
            for chunk, item in zip(chunks, extracted, strict=True):
                self.session.merge(
                    DocumentChunk(
                        id=chunk.id,
                        tenant_id=self.tenant_id,
                        document_id=database_id,
                        ordinal=chunk.ordinal,
                        content=item.safe_content,
                        metadata_json={
                            **chunk.metadata,
                            "guardrail_flagged": item.flagged,
                            "guardrail_reasons": list(item.reasons),
                        },
                    )
                )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            return IngestionResult(
                document_id=database_id,
                status="failed",
                chunk_count=len(chunks),
                hostile_chunk_count=hostile_count,
                entity_count=0,
                relationship_count=0,
                relational_indexed=False,
                vector_indexed=False,
                graph_indexed=False,
                errors=(f"relational: {redact_secrets(str(exc))}",),
            )

        errors: list[str] = []
        vector_ok = True
        try:
            if stale_ids:
                self.vector_store.delete(stale_ids)
            vectors = self.embeddings.embed([item.safe_content for item in extracted])
            if len(vectors) != len(chunks):
                raise ValueError("embedding provider returned an unexpected vector count")
            self.vector_store.upsert(
                [
                    VectorRecord(
                        id=chunk.id,
                        tenant_id=self.tenant_id,
                        vector=vector,
                        content=item.safe_content,
                        metadata={
                            **chunk.metadata,
                            "document_id": database_id,
                            "guardrail_flagged": item.flagged,
                        },
                    )
                    for chunk, item, vector in zip(chunks, extracted, vectors, strict=True)
                ]
            )
        except Exception as exc:
            vector_ok = False
            errors.append(f"vector: {redact_secrets(str(exc))}")

        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        for item in extracted:
            nodes.update((node.id, node) for node in item.nodes)
            edges.update((edge.id, edge) for edge in item.edges)
        graph_ok = True
        try:
            self.graph_store.upsert_nodes(list(nodes.values()))
            self.graph_store.upsert_edges(list(edges.values()))
        except Exception as exc:
            graph_ok = False
            errors.append(f"graph: {redact_secrets(str(exc))}")

        return IngestionResult(
            document_id=database_id,
            status="completed" if not errors else "partial",
            chunk_count=len(chunks),
            hostile_chunk_count=hostile_count,
            entity_count=max(0, len(nodes) - 1),
            relationship_count=len(edges),
            relational_indexed=True,
            vector_indexed=vector_ok,
            graph_indexed=graph_ok,
            errors=tuple(errors),
        )

    def _tenant_id(self, prefix: str, value: str) -> str:
        digest = hashlib.sha256(f"{self.tenant_id}\0{value}".encode()).hexdigest()[:24]
        return f"{prefix}-{digest}"

    def _resolve_document_id(self, document: LoadedDocument) -> str:
        """Reuse a Phase 2 seeded source before creating an ingestion-owned ID."""

        source_candidates = (f"documents/{document.source_name}", document.source_name)
        for source_path in source_candidates:
            existing_id = self.session.scalar(
                select(Document.id)
                .where(
                    Document.tenant_id == self.tenant_id,
                    Document.source_path == source_path,
                )
                .limit(1)
            )
            if existing_id is not None:
                return existing_id
        return self._tenant_id("doc", document.id)
