"""Collect and normalize evidence from isolated retrieval executors."""

from __future__ import annotations

from collections.abc import Iterable

from agents.contracts import ResearchState, RetrievalRoute, WorkflowNode
from agents.nodes._trace import trace
from agents.runtime import WorkflowRuntime
from backend.app.core.guardrails import redact_secrets
from backend.app.schemas.common import Evidence


def _safe_value(value: object) -> object:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, dict):
        return {redact_secrets(str(key)): _safe_value(item) for key, item in value.items()}
    return value


def _normalize_evidence(item: Evidence) -> Evidence:
    return item.model_copy(
        update={
            "source_id": redact_secrets(item.source_id),
            "locator": redact_secrets(item.locator),
            "content": redact_secrets(item.content),
            "title": redact_secrets(item.title) if item.title else None,
            "query": redact_secrets(item.query) if item.query else None,
            "metadata": _safe_value(item.metadata),
        }
    )


def _evidence_key(item: Evidence) -> tuple[str, str, str]:
    return item.source_type.value, item.source_id, item.locator


def merge_evidence(
    state: ResearchState,
    additions: dict[str, Iterable[Evidence]],
) -> tuple[tuple[Evidence, ...], dict[str, tuple[str, ...]]]:
    existing = tuple(_normalize_evidence(item) for item in state.evidence)
    by_key = {_evidence_key(item): item for item in existing}
    subquestion_keys: dict[str, list[tuple[str, str, str]]] = {}
    id_to_key = {item.id: _evidence_key(item) for item in existing}
    for subquestion_id, evidence_ids in state.evidence_by_subquestion.items():
        subquestion_keys[subquestion_id] = [
            id_to_key[item_id] for item_id in evidence_ids if item_id in id_to_key
        ]

    for subquestion_id, items in additions.items():
        keys = subquestion_keys.setdefault(subquestion_id, [])
        for item in items:
            item = _normalize_evidence(item)
            key = _evidence_key(item)
            current = by_key.get(key)
            if current is None or item.id < current.id:
                by_key[key] = item
            if key not in keys:
                keys.append(key)

    ordered = tuple(sorted(by_key.values(), key=lambda item: item.id))
    canonical_ids = {_evidence_key(item): item.id for item in ordered}
    mapping = {
        subquestion_id: tuple(canonical_ids[key] for key in keys if key in canonical_ids)
        for subquestion_id, keys in sorted(subquestion_keys.items())
    }
    return ordered, mapping


def _retrieve(
    route: RetrievalRoute,
    runtime: WorkflowRuntime,
    *,
    corrective: bool,
) -> tuple[tuple[Evidence, ...], str | None]:
    try:
        batch = runtime.retrieve(route, corrective=corrective)
    except Exception as exc:
        return (), redact_secrets(str(exc))
    error = "; ".join(redact_secrets(value) for value in batch.errors) or None
    if batch.status != "completed" and error is None:
        error = f"retrieval returned {batch.status} status"
    return tuple(sorted(batch.evidence, key=lambda item: item.id)), error


def collect_evidence(state: ResearchState, *, runtime: WorkflowRuntime) -> ResearchState:
    additions: dict[str, tuple[Evidence, ...]] = {}
    failures: dict[str, str] = {}
    for route in state.retrieval_plan:
        items, error = _retrieve(route, runtime, corrective=False)
        additions[route.subquestion_id] = items
        if error:
            failures[route.subquestion_id] = error
    evidence, mapping = merge_evidence(state, additions)
    updated = state.model_copy(
        update={
            "evidence": evidence,
            "evidence_by_subquestion": mapping,
            "retrieval_failures": failures,
        }
    )
    status = "partial" if failures else "completed"
    return trace(
        updated,
        WorkflowNode.COLLECT_EVIDENCE,
        status=status,
        metadata={"evidence_count": len(evidence), "failure_count": len(failures)},
    )


__all__ = ["collect_evidence", "merge_evidence"]
