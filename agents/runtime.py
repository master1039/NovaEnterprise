"""Injected retrieval runtime used by the evidence workflow."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from agents.contracts import RetrievalBatch, RetrievalRoute, RetrievalStrategy
from backend.app.core.config import get_settings

RetrievalExecutor = Callable[..., RetrievalBatch]


@dataclass(frozen=True)
class WorkflowRuntime:
    executors: Mapping[RetrievalStrategy, RetrievalExecutor]
    max_corrective_rounds: int | None = None

    def __post_init__(self) -> None:
        resolved = (
            get_settings().max_corrective_rounds
            if self.max_corrective_rounds is None
            else self.max_corrective_rounds
        )
        if not 0 <= resolved <= 3:
            raise ValueError("max_corrective_rounds must be between 0 and 3")
        object.__setattr__(self, "max_corrective_rounds", resolved)

    def retrieve(self, route: RetrievalRoute, *, corrective: bool) -> RetrievalBatch:
        executor = self.executors.get(route.strategy)
        if executor is None:
            raise RuntimeError(f"no executor configured for {route.strategy.value} retrieval")
        result = executor(route, corrective=corrective)
        if not isinstance(result, RetrievalBatch):
            return RetrievalBatch.model_validate(result)
        return result


__all__ = ["RetrievalExecutor", "WorkflowRuntime"]
