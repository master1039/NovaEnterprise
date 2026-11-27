"""Synthesize a deterministic answer from verified claims only."""

from __future__ import annotations

from agents.contracts import Citation, ResearchState, WorkflowNode
from agents.nodes._trace import trace

_INSUFFICIENT = "Insufficient verified evidence to answer the question."


def synthesize_answer(state: ResearchState) -> ResearchState:
    evidence = {item.id: item for item in state.evidence}
    supported = [claim for claim in state.claims if claim.supported]
    citation_ids: list[str] = []
    for claim in supported:
        for evidence_id in claim.evidence_ids:
            if evidence_id in evidence and evidence_id not in citation_ids:
                citation_ids.append(evidence_id)
    citations = tuple(
        Citation(
            index=index,
            marker=f"[{index}]",
            evidence_id=evidence_id,
            locator=evidence[evidence_id].locator,
        )
        for index, evidence_id in enumerate(citation_ids, start=1)
    )
    marker_by_id = {item.evidence_id: item.marker for item in citations}
    lines = []
    for claim in supported:
        markers = "".join(
            marker_by_id[item_id] for item_id in claim.evidence_ids if item_id in marker_by_id
        )
        if markers:
            lines.append(f"{claim.text} {markers}")
    answer = "\n\n".join(lines) if lines else _INSUFFICIENT
    updated = state.model_copy(update={"answer": answer, "citations": citations})
    return trace(
        updated,
        WorkflowNode.SYNTHESIZE_ANSWER,
        status="completed" if lines else "partial",
        metadata={"supported_claim_count": len(lines), "citation_count": len(citations)},
    )


__all__ = ["synthesize_answer"]
