"""Verify candidate claims against explicitly linked evidence."""

from __future__ import annotations

import hashlib
import re

from agents.contracts import Claim, ResearchState, WorkflowNode
from agents.nodes._trace import trace
from backend.app.core.guardrails import inspect_untrusted_content
from backend.app.schemas.common import Evidence

_WORDS = re.compile(r"[a-z0-9]+")
_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "to",
    "was",
    "were",
    "with",
}


def make_claim(text: str, evidence_ids: tuple[str, ...]) -> Claim:
    normalized = " ".join(text.split()).strip()
    digest = hashlib.sha256(
        f"{normalized}\0{'|'.join(sorted(set(evidence_ids)))}".encode()
    ).hexdigest()[:16]
    return Claim(
        id=f"claim-{digest}",
        text=normalized,
        evidence_ids=tuple(dict.fromkeys(evidence_ids)),
    )


def _tokens(value: str) -> set[str]:
    return {token for token in _WORDS.findall(value.casefold()) if token not in _STOP_WORDS}


def _is_hostile(item: Evidence) -> bool:
    return (
        bool(item.metadata.get("guardrail_flagged"))
        or inspect_untrusted_content(
            item.content,
            source_id=item.id,
        ).flagged
    )


def _generated_claims(state: ResearchState) -> tuple[Claim, ...]:
    return tuple(
        make_claim(item.content[:4000], (item.id,))
        for item in state.evidence
        if not _is_hostile(item)
    )


def verify_evidence(state: ResearchState) -> ResearchState:
    evidence = {item.id: item for item in state.evidence}
    candidates = state.claims or _generated_claims(state)
    verified: list[Claim] = []
    for claim in candidates:
        linked = [evidence[item_id] for item_id in claim.evidence_ids if item_id in evidence]
        if not claim.evidence_ids or len(linked) != len(claim.evidence_ids):
            verified.append(
                claim.model_copy(
                    update={"supported": False, "unsupported_reason": "unresolved_evidence"}
                )
            )
            continue
        if any(_is_hostile(item) for item in linked):
            verified.append(
                claim.model_copy(
                    update={"supported": False, "unsupported_reason": "hostile_evidence"}
                )
            )
            continue
        claim_tokens = _tokens(claim.text)
        evidence_tokens = _tokens(" ".join(item.content for item in linked))
        supported = bool(claim_tokens) and claim_tokens <= evidence_tokens
        verified.append(
            claim.model_copy(
                update={
                    "supported": supported,
                    "unsupported_reason": None if supported else "insufficient_content_support",
                }
            )
        )

    decisions = list(state.decisions)
    if any(_is_hostile(item) for item in state.evidence):
        decisions.append("hostile_evidence_excluded_from_claims")
    unsupported = sum(not item.supported for item in verified)
    updated = state.model_copy(
        update={"claims": tuple(verified), "decisions": tuple(dict.fromkeys(decisions))}
    )
    return trace(
        updated,
        WorkflowNode.VERIFY_EVIDENCE,
        status="partial" if unsupported else "completed",
        metadata={"claim_count": len(verified), "unsupported_count": unsupported},
    )


__all__ = ["make_claim", "verify_evidence"]
