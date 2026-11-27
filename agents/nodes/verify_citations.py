"""Verify every answer marker resolves to an attached evidence citation."""

from __future__ import annotations

import re

from agents.contracts import ResearchState, WorkflowNode
from agents.nodes._trace import trace

_MARKER = re.compile(r"\[[0-9]+\]")


def verify_citations(state: ResearchState) -> ResearchState:
    markers = tuple(dict.fromkeys(_MARKER.findall(state.answer or "")))
    evidence = {item.id: item for item in state.evidence}
    candidates: dict[str, list[str]] = {}
    evidence_markers: dict[str, set[str]] = {}
    for item in state.citations:
        linked = evidence.get(item.evidence_id)
        if (
            linked is not None
            and item.marker == f"[{item.index}]"
            and item.locator == linked.locator
        ):
            candidates.setdefault(item.marker, []).append(item.evidence_id)
            evidence_markers.setdefault(item.evidence_id, set()).add(item.marker)
    resolved = {
        marker
        for marker, candidate_ids in candidates.items()
        if len(candidate_ids) == 1
        and len(set(candidate_ids)) == 1
        and len(evidence_markers[candidate_ids[0]]) == 1
    }
    invalid = tuple(marker for marker in markers if marker not in resolved)
    unused = tuple(
        dict.fromkeys(item.marker for item in state.citations if item.marker not in markers)
    )
    updated = state.model_copy(update={"invalid_citations": invalid, "unused_citations": unused})
    return trace(
        updated,
        WorkflowNode.VERIFY_CITATIONS,
        status="partial" if invalid or unused else "completed",
        metadata={"invalid_count": len(invalid), "unused_count": len(unused)},
    )


__all__ = ["verify_citations"]
