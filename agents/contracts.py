"""Typed state shared by Phase 10 query workflow nodes."""

from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class QueryComplexity(StrEnum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class QueryIntent(StrEnum):
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    RECORDS = "records"
    RELATIONSHIP = "relationship"
    NARRATIVE = "narrative"


class RetrievalStrategy(StrEnum):
    VECTOR = "vector"
    SQL = "sql"
    GRAPH = "graph"
    HYBRID = "hybrid"


class WorkflowNode(StrEnum):
    ANALYZE_QUERY = "analyze_query"
    ASSESS_COMPLEXITY = "assess_complexity"
    DECOMPOSE = "decompose"
    ROUTE_RETRIEVAL = "route_retrieval"


GRAPH_NODE_SEQUENCE = (
    WorkflowNode.ANALYZE_QUERY,
    WorkflowNode.ASSESS_COMPLEXITY,
    WorkflowNode.DECOMPOSE,
    WorkflowNode.ROUTE_RETRIEVAL,
)


class QueryTimeRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    expression: str = Field(min_length=1, max_length=120)
    start: date | None = None
    end: date | None = None
    relative: bool = False


class QueryAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    complexity: QueryComplexity
    intents: tuple[QueryIntent, ...]
    entities: tuple[str, ...] = ()
    time_range: QueryTimeRange | None = None


class SubQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^sq[1-9][0-9]*$")
    question: str = Field(min_length=1, max_length=2000)


class RetrievalRoute(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subquestion_id: str = Field(pattern=r"^sq[1-9][0-9]*$")
    query: str = Field(min_length=1, max_length=2000)
    strategy: RetrievalStrategy
    reason_code: str = Field(min_length=1, max_length=80)


class ResearchState(BaseModel):
    """Small immutable state passed between deterministic Phase 10 nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=1, max_length=2000)
    analysis: QueryAnalysis | None = None
    subquestions: tuple[SubQuestion, ...] = ()
    retrieval_plan: tuple[RetrievalRoute, ...] = ()
    current_node: WorkflowNode | None = None
    decisions: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("question must not be blank")
        return normalized


__all__ = [
    "GRAPH_NODE_SEQUENCE",
    "QueryAnalysis",
    "QueryComplexity",
    "QueryIntent",
    "QueryTimeRange",
    "ResearchState",
    "RetrievalRoute",
    "RetrievalStrategy",
    "SubQuestion",
    "WorkflowNode",
]
