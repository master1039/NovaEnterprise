"""LangGraph wiring for bounded, checkpointed enterprise research."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agents.contracts import ResearchState, WorkflowNode
from agents.nodes._trace import trace
from agents.nodes.analyze_query import analyze_query
from agents.nodes.assess_complexity import assess_complexity
from agents.nodes.check_missing_evidence import check_missing_evidence
from agents.nodes.collect_evidence import collect_evidence
from agents.nodes.corrective_retrieval import corrective_retrieval
from agents.nodes.decompose import decompose_query
from agents.nodes.route_retrieval import route_retrieval
from agents.nodes.synthesize_answer import synthesize_answer
from agents.nodes.verify_citations import verify_citations
from agents.nodes.verify_evidence import verify_evidence
from agents.runtime import WorkflowRuntime


def _state(value: ResearchState | dict[str, Any]) -> ResearchState:
    return value if isinstance(value, ResearchState) else ResearchState.model_validate(value)


def _output(value: ResearchState) -> dict[str, Any]:
    return value.model_dump(mode="python")


def _phase10_node(
    operation: Callable[[ResearchState], ResearchState],
    node: WorkflowNode,
) -> Callable[[ResearchState | dict[str, Any]], dict[str, Any]]:
    def run(value: ResearchState | dict[str, Any]) -> dict[str, Any]:
        updated = operation(_state(value))
        updated = trace(updated, node, metadata={"decision_count": len(updated.decisions)})
        return _output(updated)

    return run


def build_graph(
    runtime: WorkflowRuntime,
    *,
    checkpointer: Any | None = None,
) -> Any:
    """Compile the complete bounded workflow with thread-scoped checkpoints."""

    builder = StateGraph(ResearchState)
    builder.add_node(
        WorkflowNode.ANALYZE_QUERY.value,
        _phase10_node(analyze_query, WorkflowNode.ANALYZE_QUERY),
    )
    builder.add_node(
        WorkflowNode.ASSESS_COMPLEXITY.value,
        _phase10_node(assess_complexity, WorkflowNode.ASSESS_COMPLEXITY),
    )
    builder.add_node(
        WorkflowNode.DECOMPOSE.value,
        _phase10_node(decompose_query, WorkflowNode.DECOMPOSE),
    )
    builder.add_node(
        WorkflowNode.ROUTE_RETRIEVAL.value,
        _phase10_node(route_retrieval, WorkflowNode.ROUTE_RETRIEVAL),
    )
    builder.add_node(
        WorkflowNode.COLLECT_EVIDENCE.value,
        lambda value: _output(collect_evidence(_state(value), runtime=runtime)),
    )
    builder.add_node(
        WorkflowNode.CHECK_MISSING_EVIDENCE.value,
        lambda value: _output(check_missing_evidence(_state(value))),
    )
    builder.add_node(
        WorkflowNode.CORRECTIVE_RETRIEVAL.value,
        lambda value: _output(corrective_retrieval(_state(value), runtime=runtime)),
    )
    builder.add_node(
        WorkflowNode.VERIFY_EVIDENCE.value,
        lambda value: _output(verify_evidence(_state(value))),
    )
    builder.add_node(
        WorkflowNode.SYNTHESIZE_ANSWER.value,
        lambda value: _output(synthesize_answer(_state(value))),
    )
    builder.add_node(
        WorkflowNode.VERIFY_CITATIONS.value,
        lambda value: _output(verify_citations(_state(value))),
    )

    sequence = (
        WorkflowNode.ANALYZE_QUERY,
        WorkflowNode.ASSESS_COMPLEXITY,
        WorkflowNode.DECOMPOSE,
        WorkflowNode.ROUTE_RETRIEVAL,
        WorkflowNode.COLLECT_EVIDENCE,
        WorkflowNode.CHECK_MISSING_EVIDENCE,
    )
    builder.add_edge(START, sequence[0].value)
    for current, following in zip(sequence, sequence[1:], strict=False):
        builder.add_edge(current.value, following.value)

    def after_missing(value: ResearchState | dict[str, Any]) -> str:
        state = _state(value)
        assert runtime.max_corrective_rounds is not None
        if state.missing_subquestions and state.corrective_rounds < runtime.max_corrective_rounds:
            return WorkflowNode.CORRECTIVE_RETRIEVAL.value
        return WorkflowNode.VERIFY_EVIDENCE.value

    builder.add_conditional_edges(
        WorkflowNode.CHECK_MISSING_EVIDENCE.value,
        after_missing,
        {
            WorkflowNode.CORRECTIVE_RETRIEVAL.value: WorkflowNode.CORRECTIVE_RETRIEVAL.value,
            WorkflowNode.VERIFY_EVIDENCE.value: WorkflowNode.VERIFY_EVIDENCE.value,
        },
    )
    builder.add_edge(
        WorkflowNode.CORRECTIVE_RETRIEVAL.value,
        WorkflowNode.CHECK_MISSING_EVIDENCE.value,
    )
    builder.add_edge(WorkflowNode.VERIFY_EVIDENCE.value, WorkflowNode.SYNTHESIZE_ANSWER.value)
    builder.add_edge(WorkflowNode.SYNTHESIZE_ANSWER.value, WorkflowNode.VERIFY_CITATIONS.value)
    builder.add_edge(WorkflowNode.VERIFY_CITATIONS.value, END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())


__all__ = ["WorkflowRuntime", "build_graph"]
