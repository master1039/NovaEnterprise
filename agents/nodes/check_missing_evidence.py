"""Detect routed sub-questions that still have no evidence."""

from __future__ import annotations

from agents.contracts import ResearchState, WorkflowNode
from agents.nodes._trace import trace


def check_missing_evidence(state: ResearchState) -> ResearchState:
    missing = tuple(
        route.subquestion_id
        for route in state.retrieval_plan
        if not state.evidence_by_subquestion.get(route.subquestion_id)
    )
    decisions = tuple(
        dict.fromkeys(
            (*state.decisions, "missing_evidence_detected" if missing else "evidence_complete")
        )
    )
    updated = state.model_copy(update={"missing_subquestions": missing, "decisions": decisions})
    return trace(
        updated,
        WorkflowNode.CHECK_MISSING_EVIDENCE,
        status="partial" if missing else "completed",
        metadata={"missing_count": len(missing)},
    )


__all__ = ["check_missing_evidence"]
