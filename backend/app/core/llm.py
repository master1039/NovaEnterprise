"""Provider-neutral text generation with a deterministic offline default."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from backend.app.core.config import Settings, get_settings
from backend.app.core.providers import ProviderConfigurationError


@dataclass(frozen=True)
class LLMResult:
    content: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int


@runtime_checkable
class LLM(Protocol):
    def complete(self, prompt: str, *, system: str | None = None) -> LLMResult: ...


class FakeLLM:
    provider = "fake"

    def __init__(self, model: str = "fake-v1") -> None:
        self.model = model

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResult:
        normalized_prompt = " ".join(prompt.split())
        normalized_system = " ".join((system or "").split())
        material = f"{normalized_system}\n{normalized_prompt}".encode()
        digest = hashlib.sha256(material).hexdigest()[:16]
        content = f"Deterministic offline response [{digest}]"
        return LLMResult(
            content=content,
            provider=self.provider,
            model=self.model,
            input_tokens=len((normalized_system + " " + normalized_prompt).split()),
            output_tokens=len(content.split()),
        )


class ExternalLLM:
    """Thin adapter for an injected provider client; performs no SDK import."""

    def __init__(self, provider: str, model: str, client: Any) -> None:
        self.provider = provider
        self.model = model
        self.client = client

    def complete(self, prompt: str, *, system: str | None = None) -> LLMResult:
        response = self.client.complete(model=self.model, prompt=prompt, system=system)
        content = response["content"] if isinstance(response, dict) else str(response.content)
        model = response.get("model", self.model) if isinstance(response, dict) else self.model
        return LLMResult(
            content=content,
            provider=self.provider,
            model=model,
            input_tokens=len(prompt.split()) + len((system or "").split()),
            output_tokens=len(content.split()),
        )


def get_llm(
    settings: Settings | None = None,
    *,
    clients: dict[str, Any] | None = None,
) -> LLM:
    resolved = settings or get_settings()
    if resolved.llm_provider == "fake":
        return FakeLLM(resolved.llm_model)
    client = (clients or {}).get(resolved.llm_provider)
    if client is None:
        raise ProviderConfigurationError(
            f"{resolved.llm_provider} LLM requires an explicitly configured optional client"
        )
    return ExternalLLM(resolved.llm_provider, resolved.llm_model, client)


__all__ = [
    "ExternalLLM",
    "FakeLLM",
    "LLM",
    "LLMResult",
    "ProviderConfigurationError",
    "get_llm",
]
