"""Deterministic rules that constrain query analysis, decomposition, and routing."""

from __future__ import annotations

import re
from datetime import date

from agents.contracts import (
    QueryAnalysis,
    QueryComplexity,
    QueryIntent,
    QueryTimeRange,
    RetrievalStrategy,
)

_ENTITY = re.compile(
    r"\b([A-Z][A-Za-z0-9-]*(?:\s+[A-Z][A-Za-z0-9-]*)*\s+"
    r"(?:API|Service|Engine|Bank|Portal|Dashboard|Pipeline))\b"
)
_EXPLICIT_RANGE = re.compile(
    r"\b(?:from\s+)?(\d{4}-\d{2}-\d{2})\s+(?:to|through|until)\s+"
    r"(\d{4}-\d{2}-\d{2})\b",
    re.IGNORECASE,
)
_RELATIVE_TIME = re.compile(
    r"\b(last quarter|this quarter|last month|this month|last year|this year)\b",
    re.IGNORECASE,
)


def extract_entities(question: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(1).strip() for match in _ENTITY.finditer(question)))


def extract_time_range(question: str) -> QueryTimeRange | None:
    explicit = _EXPLICIT_RANGE.search(question)
    if explicit:
        start = date.fromisoformat(explicit.group(1))
        end = date.fromisoformat(explicit.group(2))
        if end < start:
            raise ValueError("query time range end must not precede start")
        return QueryTimeRange(expression=explicit.group(0), start=start, end=end)
    relative = _RELATIVE_TIME.search(question)
    if relative:
        return QueryTimeRange(expression=relative.group(1).casefold(), relative=True)
    return None


def infer_intents(question: str) -> tuple[QueryIntent, ...]:
    lowered = question.casefold()
    intents: list[QueryIntent] = []
    if re.search(r"\b(how many|count|total|average|sum)\b", lowered):
        intents.append(QueryIntent.AGGREGATION)
    if re.search(r"\b(incident|ticket|customer|project|record)s?\b", lowered):
        intents.append(QueryIntent.RECORDS)
    if re.search(
        r"\b(impact(?:ed|s)?|affect(?:ed|s)?|own(?:s|ed|er|ership)?|depends?|relationship|team)s?\b",
        lowered,
    ):
        intents.append(QueryIntent.RELATIONSHIP)
    if re.search(
        r"\b(why|decision|prevent|recurrence|rationale|postmortem|policy|runbook)\b", lowered
    ):
        intents.append(QueryIntent.NARRATIVE)
    if not intents:
        intents.append(QueryIntent.LOOKUP)
    return tuple(dict.fromkeys(intents))


def choose_strategy(question: str) -> tuple[RetrievalStrategy, str]:
    lowered = question.casefold()
    if re.search(
        r"\b(impact(?:ed|s)?|affect(?:ed|s)?|own(?:s|ed|er|ership)?|relationship|depends?)\b",
        lowered,
    ):
        return RetrievalStrategy.GRAPH, "relationship_traversal"
    if re.search(r"\b(how many|count|total|average|sum|incident|ticket|record)s?\b", lowered):
        return RetrievalStrategy.SQL, "structured_records"
    if re.search(r"\b(why|decision|prevent|recurrence|rationale|postmortem|root cause)\b", lowered):
        return RetrievalStrategy.HYBRID, "narrative_with_exact_terms"
    return RetrievalStrategy.VECTOR, "semantic_document_lookup"


def assess_query_complexity(question: str, intents: tuple[QueryIntent, ...]) -> QueryComplexity:
    probes = {
        choose_strategy(part.strip())[0]
        for part in re.split(r",|\band\b", question, flags=re.IGNORECASE)
        if part.strip()
    }
    if len(probes) >= 3:
        return QueryComplexity.COMPLEX
    elif len(probes) == 2 or len(intents) >= 2:
        return QueryComplexity.MODERATE
    return QueryComplexity.SIMPLE


def analyze_deterministically(question: str) -> QueryAnalysis:
    intents = infer_intents(question)
    return QueryAnalysis(
        complexity=assess_query_complexity(question, intents),
        intents=intents,
        entities=extract_entities(question),
        time_range=extract_time_range(question),
    )


__all__ = [
    "analyze_deterministically",
    "assess_query_complexity",
    "choose_strategy",
    "extract_entities",
    "extract_time_range",
    "infer_intents",
]
