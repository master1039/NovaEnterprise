"""Map typed sub-questions to implemented retrieval capabilities."""

from __future__ import annotations

from agents.contracts import ResearchState, RetrievalRoute, WorkflowNode
from agents.rules import choose_strategy


def route_retrieval(state: ResearchState) -> ResearchState:
    if not state.subquestions:
        raise ValueError("query must be decomposed before retrieval routing")
    routes: list[RetrievalRoute] = []
    for item in state.subquestions:
        strategy, reason = choose_strategy(item.question)
        routes.append(
            RetrievalRoute(
                subquestion_id=item.id,
                query=item.question,
                strategy=strategy,
                reason_code=reason,
            )
        )
    return state.model_copy(
        update={
            "retrieval_plan": tuple(routes),
            "current_node": WorkflowNode.ROUTE_RETRIEVAL,
            "decisions": tuple(dict.fromkeys((*state.decisions, "deterministic_routing"))),
        }
    )


__all__ = ["route_retrieval"]
