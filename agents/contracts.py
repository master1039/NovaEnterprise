"""Typed state shared by Phase 10 query workflow nodes."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.common import Evidence


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
    COLLECT_EVIDENCE = "collect_evidence"
    CHECK_MISSING_EVIDENCE = "check_missing_evidence"
    CORRECTIVE_RETRIEVAL = "corrective_retrieval"
    VERIFY_EVIDENCE = "verify_evidence"
    SYNTHESIZE_ANSWER = "synthesize_answer"
    VERIFY_CITATIONS = "verify_citations"


GRAPH_NODE_SEQUENCE = (
    WorkflowNode.ANALYZE_QUERY,
    WorkflowNode.ASSESS_COMPLEXITY,
    WorkflowNode.DECOMPOSE,
    WorkflowNode.ROUTE_RETRIEVAL,
)

WORKFLOW_NODE_SEQUENCE = (
    *GRAPH_NODE_SEQUENCE,
    WorkflowNode.COLLECT_EVIDENCE,
    WorkflowNode.CHECK_MISSING_EVIDENCE,
    WorkflowNode.CORRECTIVE_RETRIEVAL,
    WorkflowNode.VERIFY_EVIDENCE,
    WorkflowNode.SYNTHESIZE_ANSWER,
    WorkflowNode.VERIFY_CITATIONS,
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


class RetrievalBatch(BaseModel):
    """Store-neutral result returned by an injected retrieval executor."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["completed", "partial", "degraded"] = "completed"
    evidence: tuple[Evidence, ...] = ()
    errors: tuple[str, ...] = ()


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^claim-[a-f0-9]{16}$")
    text: str = Field(min_length=1, max_length=4000)
    evidence_ids: tuple[str, ...] = ()
    supported: bool = False
    unsupported_reason: str | None = Field(default=None, max_length=160)


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    index: int = Field(ge=1)
    marker: str = Field(pattern=r"^\[[1-9][0-9]*\]$")
    evidence_id: str = Field(min_length=1)
    locator: str = Field(min_length=1)


class WorkflowTrace(BaseModel):
    """Safe node transition metadata; never stores hidden reasoning."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=1)
    node: WorkflowNode
    status: str = Field(pattern=r"^(completed|partial|degraded)$")
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchState(BaseModel):
    """Immutable state shared by the Phase 10 and Phase 11 workflow nodes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    question: str = Field(min_length=1, max_length=2000)
    analysis: QueryAnalysis | None = None
    subquestions: tuple[SubQuestion, ...] = ()
    retrieval_plan: tuple[RetrievalRoute, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    evidence_by_subquestion: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    retrieval_failures: dict[str, str] = Field(default_factory=dict)
    missing_subquestions: tuple[str, ...] = ()
    corrective_rounds: int = Field(default=0, ge=0, le=3)
    claims: tuple[Claim, ...] = ()
    answer: str | None = None
    citations: tuple[Citation, ...] = ()
    invalid_citations: tuple[str, ...] = ()
    unused_citations: tuple[str, ...] = ()
    traces: tuple[WorkflowTrace, ...] = ()
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
    "WORKFLOW_NODE_SEQUENCE",
    "Citation",
    "Claim",
    "QueryAnalysis",
    "QueryComplexity",
    "QueryIntent",
    "QueryTimeRange",
    "ResearchState",
    "RetrievalBatch",
    "RetrievalRoute",
    "RetrievalStrategy",
    "SubQuestion",
    "WorkflowNode",
    "WorkflowTrace",
]
