"""LLM callers depend on one deterministic, provider-neutral contract."""

import pytest

from backend.app.core.config import Settings
from backend.app.core.llm import ProviderConfigurationError, get_llm


class StubLLMClient:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)
        return {"content": "external answer", "model": kwargs["model"]}


def test_fake_llm_is_repeatable_and_requires_no_client() -> None:
    llm = get_llm(Settings(llm_provider="fake", llm_model="fake-v1"))
    first = llm.complete("  Which customers were impacted?  ", system="Answer from evidence")
    second = llm.complete("Which customers were impacted?", system="Answer from evidence")

    assert first == second
    assert first.provider == "fake"
    assert first.model == "fake-v1"
    assert first.content


def test_external_llm_uses_injected_client_without_network() -> None:
    client = StubLLMClient()
    llm = get_llm(
        Settings(llm_provider="openai", llm_model="gpt-test"),
        clients={"openai": client},
    )

    result = llm.complete("question", system="policy")

    assert result.content == "external answer"
    assert client.calls == [{"model": "gpt-test", "prompt": "question", "system": "policy"}]


def test_external_llm_fails_clearly_without_optional_client() -> None:
    with pytest.raises(ProviderConfigurationError, match="openai"):
        get_llm(Settings(llm_provider="openai"))


def test_unknown_llm_provider_is_rejected_by_settings() -> None:
    with pytest.raises(ValueError, match="llm_provider"):
        Settings(llm_provider="unknown")
