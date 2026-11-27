"""Run at most the configured number of corrective retrieval rounds."""

from __future__ import annotations

from agents.contracts import ResearchState, WorkflowNode
from agents.nodes._trace import trace
from agents.nodes.collect_evidence import _retrieve, merge_evidence
from agents.runtime import WorkflowRuntime


def corrective_retrieval(state: ResearchState, *, runtime: WorkflowRuntime) -> ResearchState:
    assert runtime.max_corrective_rounds is not None
    if not state.missing_subquestions or state.corrective_rounds >= runtime.max_corrective_rounds:
        return state
    missing = set(state.missing_subquestions)
    additions = {}
    failures = dict(state.retrieval_failures)
    for route in state.retrieval_plan:
        if route.subquestion_id not in missing:
            continue
        items, error = _retrieve(route, runtime, corrective=True)
        additions[route.subquestion_id] = items
        if error:
            failures[route.subquestion_id] = error
        elif items:
            failures.pop(route.subquestion_id, None)
    evidence, mapping = merge_evidence(state, additions)
    updated = state.model_copy(
        update={
            "evidence": evidence,
            "evidence_by_subquestion": mapping,
            "retrieval_failures": failures,
            "corrective_rounds": state.corrective_rounds + 1,
        }
    )
    return trace(
        updated,
        WorkflowNode.CORRECTIVE_RETRIEVAL,
        status="partial" if failures else "completed",
        metadata={"round": updated.corrective_rounds, "retried_count": len(additions)},
    )


__all__ = ["corrective_retrieval"]
