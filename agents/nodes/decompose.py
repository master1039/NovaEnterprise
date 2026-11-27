"""Bounded deterministic sub-question decomposition."""

from __future__ import annotations

import re

from agents.contracts import ResearchState, SubQuestion, WorkflowNode
from backend.app.core.config import get_settings


def _context(state: ResearchState) -> str:
    assert state.analysis is not None
    entity = state.analysis.entities[0] if state.analysis.entities else ""
    time = state.analysis.time_range.expression if state.analysis.time_range else ""
    return " ".join(value for value in (entity, time) if value)


def _candidate_questions(state: ResearchState) -> list[str]:
    assert state.analysis is not None
    question = state.question
    lowered = question.casefold()
    context = _context(state)
    suffix = f" for {context}" if context else ""
    candidates: list[str] = []
    if re.search(r"\b(customer|impact|affect)", lowered):
        candidates.append(f"Which customers were impacted{suffix}?")
    if re.search(r"\bincident", lowered):
        candidates.append(f"What incidents occurred{suffix}?")
    if re.search(r"\b(team|own)", lowered):
        candidates.append(f"Which teams own the relevant services{suffix}?")
    if re.search(r"\b(decision|prevent|recurrence|rationale|postmortem)", lowered):
        candidates.append(f"What decisions were taken to prevent recurrence{suffix}?")
    if candidates:
        return candidates
    parts = re.split(
        r",\s*(?=(?:what|which|how|why)\b)|\band\b\s*(?=(?:what|which|how|why)\b)",
        question,
        flags=re.IGNORECASE,
    )
    return [part.strip(" ,") for part in parts if part.strip(" ,")]


def decompose_query(state: ResearchState, *, max_subquestions: int | None = None) -> ResearchState:
    resolved_max = get_settings().max_subquestions if max_subquestions is None else max_subquestions
    if not 1 <= resolved_max <= 8:
        raise ValueError("max_subquestions must be between 1 and 8")
    if state.analysis is None:
        raise ValueError("query must be analyzed before decomposition")
    raw = _candidate_questions(state)
    unique = list(dict.fromkeys(" ".join(item.split()) for item in raw))
    decisions = list(state.decisions)
    if len(unique) > resolved_max:
        decisions.append("decomposition_truncated")
    selected = unique[:resolved_max]
    subquestions = tuple(
        SubQuestion(id=f"sq{index}", question=question)
        for index, question in enumerate(selected, start=1)
    )
    return state.model_copy(
        update={
            "subquestions": subquestions,
            "retrieval_plan": (),
            "current_node": WorkflowNode.DECOMPOSE,
            "decisions": tuple(dict.fromkeys((*decisions, "bounded_decomposition"))),
        }
    )


__all__ = ["decompose_query"]
