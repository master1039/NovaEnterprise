"""Safe workflow trace helpers."""

from __future__ import annotations

from typing import Any

from agents.contracts import ResearchState, WorkflowNode, WorkflowTrace


def trace(
    state: ResearchState,
    node: WorkflowNode,
    *,
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
) -> ResearchState:
    item = WorkflowTrace(
        sequence=len(state.traces) + 1,
        node=node,
        status=status,
        metadata=metadata or {},
    )
    return state.model_copy(update={"current_node": node, "traces": (*state.traces, item)})


__all__ = ["trace"]
