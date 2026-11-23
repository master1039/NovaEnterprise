"""Provider-neutral embeddings with a deterministic normalized fake model."""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Protocol, runtime_checkable

from backend.app.core.config import Settings, get_settings
from backend.app.core.providers import ProviderConfigurationError


@runtime_checkable
class EmbeddingModel(Protocol):
    @property
    def dimension(self) -> int | None: ...

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class FakeEmbeddingModel:
    provider = "fake"

    def __init__(self, dimension: int = 32) -> None:
        if dimension < 1:
            raise ValueError("embedding dimension must be positive")
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        values = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9]+", text.lower()) or ["<empty>"]
        for token in tokens:
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values)) or 1.0
        return [value / norm for value in values]


class ExternalEmbeddingModel:
    def __init__(self, provider: str, model: str, client: Any) -> None:
        self.provider = provider
        self.model = model
        self.client = client

    @property
    def dimension(self) -> None:
        return None

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.client.embed(model=self.model, texts=texts)


def get_embedding_model(
    settings: Settings | None = None,
    *,
    clients: dict[str, Any] | None = None,
) -> EmbeddingModel:
    resolved = settings or get_settings()
    if resolved.embedding_provider == "fake":
        return FakeEmbeddingModel(resolved.embedding_dimension)
    client = (clients or {}).get(resolved.embedding_provider)
    if client is None:
        raise ProviderConfigurationError(
            f"{resolved.embedding_provider} embeddings require an explicitly configured "
            "optional client"
        )
    return ExternalEmbeddingModel(resolved.embedding_provider, resolved.embedding_model, client)


__all__ = [
    "EmbeddingModel",
    "ExternalEmbeddingModel",
    "FakeEmbeddingModel",
    "ProviderConfigurationError",
    "get_embedding_model",
]
