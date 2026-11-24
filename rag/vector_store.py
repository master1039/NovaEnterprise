"""Tenant-scoped vector-store contract with memory and Qdrant adapters."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from uuid import NAMESPACE_URL, uuid5

from backend.app.core.config import Settings, get_settings


@dataclass(frozen=True)
class VectorRecord:
    id: str
    tenant_id: str
    vector: list[float]
    content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class VectorMatch:
    id: str
    score: float
    content: str
    metadata: dict[str, Any]


@runtime_checkable
class VectorStore(Protocol):
    def upsert(self, records: list[VectorRecord]) -> None: ...

    def search(
        self, vector: list[float], *, limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[VectorMatch]: ...

    def delete(self, record_ids: list[str]) -> int: ...


def _cosine(left: list[float], right: list[float]) -> float:
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)


class InMemoryVectorStore:
    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self._records: dict[str, VectorRecord] = {}
        self._dimension: int | None = None

    def upsert(self, records: list[VectorRecord]) -> None:
        for record in records:
            if record.tenant_id != self.tenant_id:
                raise ValueError("record tenant does not match vector store tenant")
            if not record.vector:
                raise ValueError("vector must not be empty")
            if self._dimension is None:
                self._dimension = len(record.vector)
            if len(record.vector) != self._dimension:
                raise ValueError("vector dimension does not match collection dimension")
            self._records[record.id] = record

    def search(
        self, vector: list[float], *, limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[VectorMatch]:
        if limit < 1:
            raise ValueError("limit must be positive")
        if self._dimension is not None and len(vector) != self._dimension:
            raise ValueError("query dimension does not match collection dimension")
        filters = filters or {}
        candidates = (
            record
            for record in self._records.values()
            if all(record.metadata.get(key) == value for key, value in filters.items())
        )
        matches = [
            VectorMatch(
                id=record.id,
                score=_cosine(vector, record.vector),
                content=record.content,
                metadata=dict(record.metadata),
            )
            for record in candidates
        ]
        return sorted(matches, key=lambda match: (-match.score, match.id))[:limit]

    def delete(self, record_ids: list[str]) -> int:
        deleted = 0
        for record_id in record_ids:
            deleted += int(self._records.pop(record_id, None) is not None)
        return deleted


class QdrantVectorStore:
    def __init__(
        self,
        tenant_id: str,
        *,
        client: Any,
        collection_name: str,
        models: Any | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.client = client
        self.collection_name = collection_name
        self.models = models

    def _point_id(self, record_id: str) -> str:
        return str(uuid5(NAMESPACE_URL, f"novaenterprise:{self.tenant_id}:{record_id}"))

    def upsert(self, records: list[VectorRecord]) -> None:
        points = []
        for record in records:
            if record.tenant_id != self.tenant_id:
                raise ValueError("record tenant does not match vector store tenant")
            values = {
                "id": self._point_id(record.id),
                "vector": record.vector,
                "payload": {
                    **record.metadata,
                    "record_id": record.id,
                    "tenant_id": self.tenant_id,
                    "content": record.content,
                },
            }
            points.append(self.models.PointStruct(**values) if self.models else values)
        if points:
            self.client.upsert(collection_name=self.collection_name, points=points, wait=True)

    def search(
        self, vector: list[float], *, limit: int = 10, filters: dict[str, Any] | None = None
    ) -> list[VectorMatch]:
        values = [("tenant_id", self.tenant_id), *((filters or {}).items())]
        if self.models:
            conditions = [
                self.models.FieldCondition(
                    key=key,
                    match=self.models.MatchValue(value=value),
                )
                for key, value in values
            ]
            query_filter = self.models.Filter(must=conditions)
        else:
            conditions = [{"key": key, "match": {"value": value}} for key, value in values]
            query_filter = {"must": conditions}
        result = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [
            VectorMatch(
                id=point.payload.get("record_id", str(point.id)),
                score=float(point.score),
                content=point.payload.get("content", ""),
                metadata={
                    key: value
                    for key, value in point.payload.items()
                    if key not in {"record_id", "tenant_id", "content"}
                },
            )
            for point in result.points
            if point.payload.get("tenant_id") == self.tenant_id
        ]

    def delete(self, record_ids: list[str]) -> int:
        if not record_ids:
            return 0
        point_ids = [self._point_id(record_id) for record_id in record_ids]
        selector = self.models.PointIdsList(points=point_ids) if self.models else point_ids
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=selector,
            wait=True,
        )
        return len(record_ids)


def get_vector_store(
    settings: Settings | None,
    tenant_id: str,
    *,
    client: Any | None = None,
    models: Any | None = None,
) -> VectorStore:
    resolved = settings or get_settings()
    if resolved.vector_store == "memory":
        return InMemoryVectorStore(tenant_id)
    if models is None:
        try:
            from qdrant_client import models as qdrant_models
        except ImportError:
            qdrant_models = None
        models = qdrant_models
    if client is None:
        try:
            from qdrant_client import QdrantClient
        except ImportError as exc:
            raise RuntimeError("Qdrant requires the optional 'qdrant-client' package") from exc
        client = QdrantClient(url=resolved.qdrant_url, api_key=resolved.qdrant_api_key)
    return QdrantVectorStore(
        tenant_id,
        client=client,
        collection_name=resolved.qdrant_collection,
        models=models,
    )
