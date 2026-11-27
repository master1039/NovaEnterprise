"""Make query complexity an explicit, inspectable workflow transition."""

from __future__ import annotations

from agents.contracts import ResearchState, WorkflowNode
from agents.rules import assess_query_complexity


def assess_complexity(state: ResearchState) -> ResearchState:
    if state.analysis is None:
        raise ValueError("query must be analyzed before complexity assessment")
    analysis = state.analysis.model_copy(
        update={"complexity": assess_query_complexity(state.question, state.analysis.intents)}
    )
    return state.model_copy(
        update={
            "analysis": analysis,
            "current_node": WorkflowNode.ASSESS_COMPLEXITY,
            "decisions": tuple(
                dict.fromkeys((*state.decisions, f"complexity_{analysis.complexity.value}"))
            ),
        }
    )


__all__ = ["assess_complexity"]
