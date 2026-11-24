"""Embedding output is deterministic and swappable behind one contract."""

import pytest

from backend.app.core.config import Settings
from backend.app.core.embeddings import ProviderConfigurationError, get_embedding_model


class StubEmbeddingClient:
    def embed(self, **kwargs):
        return [[0.25, 0.75] for _ in kwargs["texts"]]


def test_fake_embeddings_are_stable_normalized_and_dimensioned() -> None:
    model = get_embedding_model(Settings(embedding_provider="fake", embedding_dimension=12))
    first = model.embed(["payments incident", "payments incident", "other"])
    second = model.embed(["payments incident"])

    assert len(first) == 3
    assert len(first[0]) == 12
    assert first[0] == first[1] == second[0]
    assert first[0] != first[2]
    assert sum(value * value for value in first[0]) == pytest.approx(1.0)


def test_fake_embeddings_preserve_empty_batch() -> None:
    model = get_embedding_model(Settings(embedding_provider="fake"))
    assert model.embed([]) == []
    empty_text = model.embed([""])[0]
    assert sum(value * value for value in empty_text) == pytest.approx(1.0)


def test_fake_embeddings_give_shared_tokens_more_similarity() -> None:
    model = get_embedding_model(Settings(embedding_provider="fake", embedding_dimension=64))
    payments_incident, payments_outage, identity_login = model.embed(
        ["payments incident", "payments outage", "identity login"]
    )
    related = sum(a * b for a, b in zip(payments_incident, payments_outage, strict=True))
    unrelated = sum(a * b for a, b in zip(payments_incident, identity_login, strict=True))
    assert related > unrelated


def test_external_embedding_client_is_injected_or_fails_clearly() -> None:
    settings = Settings(embedding_provider="openai", embedding_model="embed-test")
    model = get_embedding_model(settings, clients={"openai": StubEmbeddingClient()})
    assert model.embed(["one", "two"]) == [[0.25, 0.75], [0.25, 0.75]]

    with pytest.raises(ProviderConfigurationError, match="openai"):
        get_embedding_model(settings)
