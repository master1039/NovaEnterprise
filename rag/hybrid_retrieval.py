"""Tenant-scoped semantic and BM25 retrieval with deterministic rank fusion."""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.embeddings import EmbeddingModel
from backend.app.core.guardrails import inspect_untrusted_content, redact_secrets
from backend.app.models import Document, DocumentChunk
from backend.app.schemas.common import Evidence, EvidenceSourceType
from rag.vector_store import VectorMatch, VectorStore

MAX_RESULTS = 100
MAX_CANDIDATES = 200
RetrievalStatus = Literal["completed", "partial", "degraded"]
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class _Candidate:
    chunk_id: str
    document_id: str
    content: str
    title: str
    source: str
    page: int | None
    ordinal: int
    guardrail_flagged: bool
    guardrail_reasons: tuple[str, ...]
    semantic_score: float | None = None
    bm25_score: float | None = None
    fused_score: float = 0.0
    channels: tuple[str, ...] = ()


@dataclass(frozen=True)
class HybridRetrievalResult:
    status: RetrievalStatus
    evidence: tuple[Evidence, ...]
    strategies: tuple[str, ...]
    errors: tuple[str, ...] = ()


def _tokens(value: str) -> list[str]:
    return _TOKEN_PATTERN.findall(value.casefold())


def _safe_error(strategy: str, error: Exception) -> str:
    return f"{strategy}: {redact_secrets(str(error))}"


def _stable_evidence_id(tenant_id: str, chunk_id: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}\0document\0{chunk_id}".encode()).hexdigest()[:24]
    return f"evidence-{digest}"


class HybridRetriever:
    """Combine vector similarity and tenant-filtered BM25 without live services."""

    def __init__(
        self,
        *,
        session: Session,
        tenant_id: str,
        embeddings: EmbeddingModel,
        vector_store: VectorStore,
        rrf_k: int = 60,
    ) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be blank")
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        self.session = session
        self.tenant_id = tenant_id
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.rrf_k = rrf_k

    def retrieve(
        self,
        query: str,
        *,
        limit: int = 10,
        candidate_limit: int | None = None,
        score_cutoff: float = 0.0,
    ) -> HybridRetrievalResult:
        if not 1 <= limit <= MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")
        if not 0.0 <= score_cutoff <= 1.0:
            raise ValueError("score_cutoff must be between 0 and 1")
        clean_query = query.strip()
        if not clean_query:
            return HybridRetrievalResult("completed", (), ("bm25", "semantic"))
        resolved_candidates = max(20, limit * 2) if candidate_limit is None else candidate_limit
        if not 1 <= resolved_candidates <= MAX_CANDIDATES:
            raise ValueError(f"candidate_limit must be between 1 and {MAX_CANDIDATES}")

        ranked: dict[str, list[_Candidate]] = {}
        errors: list[str] = []
        try:
            ranked["semantic"] = self._semantic(clean_query, resolved_candidates)
        except Exception as exc:
            errors.append(_safe_error("semantic", exc))
        try:
            ranked["bm25"] = self._bm25(clean_query, resolved_candidates)
        except Exception as exc:
            errors.append(_safe_error("bm25", exc))

        strategies = tuple(sorted(ranked))
        if not strategies:
            return HybridRetrievalResult("degraded", (), (), tuple(errors))
        fused = self._fuse_and_rerank(clean_query, ranked)
        evidence = tuple(
            self._to_evidence(candidate, clean_query)
            for candidate in fused
            if candidate.fused_score >= score_cutoff
        )[:limit]
        status: RetrievalStatus = "partial" if errors else "completed"
        return HybridRetrievalResult(status, evidence, strategies, tuple(errors))

    def _semantic(self, query: str, limit: int) -> list[_Candidate]:
        vectors = self.embeddings.embed([query])
        if len(vectors) != 1 or not vectors[0]:
            raise ValueError("embedding provider returned an invalid query vector")
        matches = self.vector_store.search(vectors[0], limit=limit)
        return [self._from_vector(match) for match in matches]

    def _from_vector(self, match: VectorMatch) -> _Candidate:
        metadata = match.metadata
        document_id = str(metadata.get("document_id", "")).strip()
        source = redact_secrets(str(metadata.get("source", "")).strip())
        if not document_id or not source:
            raise ValueError("vector match is missing document source metadata")
        page_value = metadata.get("page")
        page = int(page_value) if page_value is not None else None
        return _Candidate(
            chunk_id=match.id,
            document_id=document_id,
            content=redact_secrets(match.content),
            title=redact_secrets(str(metadata.get("title") or source)),
            source=source,
            page=page,
            ordinal=int(metadata.get("chunk", 0)),
            guardrail_flagged=bool(metadata.get("guardrail_flagged", False)),
            guardrail_reasons=tuple(metadata.get("guardrail_reasons", ())),
            semantic_score=max(0.0, min(1.0, float(match.score))),
            channels=("semantic",),
        )

    def _bm25(self, query: str, limit: int) -> list[_Candidate]:
        query_terms = sorted(set(_tokens(query)))
        if not query_terms:
            return []
        rows = list(
            self.session.execute(
                select(DocumentChunk, Document)
                .join(
                    Document,
                    (Document.id == DocumentChunk.document_id)
                    & (Document.tenant_id == DocumentChunk.tenant_id),
                )
                .where(DocumentChunk.tenant_id == self.tenant_id)
                .order_by(DocumentChunk.id)
            )
        )
        if not rows:
            return []
        tokenized = [_tokens(chunk.content) for chunk, _document in rows]
        average_length = sum(len(tokens) for tokens in tokenized) / len(tokenized) or 1.0
        frequencies = {
            term: sum(term in set(tokens) for tokens in tokenized) for term in query_terms
        }
        candidates: list[_Candidate] = []
        for (chunk, document), tokens in zip(rows, tokenized, strict=True):
            counts = Counter(tokens)
            score = 0.0
            for term in query_terms:
                frequency = counts[term]
                if not frequency:
                    continue
                document_frequency = frequencies[term]
                inverse_frequency = math.log(
                    1 + (len(rows) - document_frequency + 0.5) / (document_frequency + 0.5)
                )
                denominator = frequency + 1.5 * (0.25 + 0.75 * len(tokens) / average_length)
                score += inverse_frequency * frequency * 2.5 / denominator
            if score <= 0:
                continue
            metadata = chunk.metadata_json or {}
            candidates.append(
                _Candidate(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    content=redact_secrets(chunk.content),
                    title=redact_secrets(document.title),
                    source=redact_secrets(str(metadata.get("source") or document.source_path)),
                    page=int(metadata["page"]) if metadata.get("page") is not None else None,
                    ordinal=int(metadata.get("chunk", chunk.ordinal)),
                    guardrail_flagged=bool(
                        metadata.get("guardrail_flagged", document.is_untrusted)
                    ),
                    guardrail_reasons=tuple(metadata.get("guardrail_reasons", ())),
                    bm25_score=score,
                    channels=("bm25",),
                )
            )
        return sorted(candidates, key=lambda item: (-float(item.bm25_score or 0), item.chunk_id))[
            :limit
        ]

    def _fuse_and_rerank(self, query: str, ranked: dict[str, list[_Candidate]]) -> list[_Candidate]:
        merged: dict[str, _Candidate] = {}
        contributions: dict[str, float] = {}
        for channel in sorted(ranked):
            for rank, candidate in enumerate(ranked[channel], start=1):
                contributions[candidate.chunk_id] = contributions.get(candidate.chunk_id, 0.0) + (
                    1.0 / (self.rrf_k + rank)
                )
                current = merged.get(candidate.chunk_id)
                if current is None:
                    merged[candidate.chunk_id] = candidate
                else:
                    # Prefer relational source metadata while preserving both native scores.
                    primary = candidate if channel == "bm25" else current
                    merged[candidate.chunk_id] = replace(
                        primary,
                        semantic_score=(
                            candidate.semantic_score
                            if candidate.semantic_score is not None
                            else current.semantic_score
                        ),
                        bm25_score=(
                            candidate.bm25_score
                            if candidate.bm25_score is not None
                            else current.bm25_score
                        ),
                        guardrail_flagged=(
                            candidate.guardrail_flagged or current.guardrail_flagged
                        ),
                        guardrail_reasons=tuple(
                            sorted(set(candidate.guardrail_reasons + current.guardrail_reasons))
                        ),
                        channels=tuple(sorted(set(candidate.channels + current.channels))),
                    )
        maximum_rrf = len(ranked) / (self.rrf_k + 1)
        query_terms = set(_tokens(query))
        output: list[_Candidate] = []
        for chunk_id, candidate in merged.items():
            overlap = len(query_terms & set(_tokens(candidate.content))) / max(1, len(query_terms))
            native = max(candidate.semantic_score or 0.0, 0.0)
            if candidate.bm25_score is not None:
                native = max(native, candidate.bm25_score / (1.0 + candidate.bm25_score))
            score = 0.75 * contributions[chunk_id] / maximum_rrf + 0.15 * overlap + 0.10 * native
            output.append(replace(candidate, fused_score=min(score, 0.999999)))
        return sorted(output, key=lambda item: (-item.fused_score, item.chunk_id))

    def _to_evidence(self, candidate: _Candidate, query: str) -> Evidence:
        content = candidate.content
        if candidate.guardrail_flagged:
            content = inspect_untrusted_content(
                content, source_id=candidate.chunk_id
            ).wrapped_content
        page_suffix = f"?page={candidate.page}" if candidate.page is not None else ""
        return Evidence(
            id=_stable_evidence_id(self.tenant_id, candidate.chunk_id),
            source_type=EvidenceSourceType.DOCUMENT,
            source_id=candidate.document_id,
            locator=(
                f"document://{candidate.document_id}/chunks/{candidate.chunk_id}{page_suffix}"
            ),
            content=content,
            title=candidate.title,
            score=candidate.fused_score,
            query=query,
            metadata={
                "chunk_id": candidate.chunk_id,
                "chunk_ordinal": candidate.ordinal,
                "source": candidate.source,
                "page": candidate.page,
                "retrieval_channels": list(candidate.channels),
                "semantic_score": candidate.semantic_score,
                "bm25_score": candidate.bm25_score,
                "guardrail_flagged": candidate.guardrail_flagged,
                "guardrail_reasons": list(candidate.guardrail_reasons),
                "content_treatment": "untrusted_data",
            },
        )


__all__ = ["HybridRetrievalResult", "HybridRetriever", "MAX_CANDIDATES", "MAX_RESULTS"]
