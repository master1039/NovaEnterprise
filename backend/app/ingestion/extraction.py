"""Deterministic, guardrail-first extraction for canonical enterprise entities."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from backend.app.core.guardrails import inspect_untrusted_content, redact_secrets
from backend.app.ingestion.loaders import DocumentChunkData
from rag.graph_store import GraphEdge, GraphNode

_CANONICAL_ENTITIES = {
    "Service": ("Payments API", "Identity Service", "Fraud Detection Service"),
    "Customer": ("Acme Bank", "Globex Retail", "Initech"),
    "Team": ("Payments Platform", "Identity Platform", "Fraud Platform"),
}
_IDENTIFIER_PATTERN = re.compile(r"\b(?P<kind>INC|ADR)-(?P<number>\d{3,6})\b", re.IGNORECASE)


@dataclass(frozen=True)
class ExtractionResult:
    safe_content: str
    flagged: bool
    reasons: tuple[str, ...]
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]


def _stable_id(prefix: str, tenant_id: str, value: str) -> str:
    digest = hashlib.sha256(f"{tenant_id}\0{value.casefold()}".encode()).hexdigest()[:24]
    return f"{prefix}-{digest}"


def extract_knowledge(chunk: DocumentChunkData, *, tenant_id: str) -> ExtractionResult:
    """Inspect first, then extract only known data patterns; embedded commands are inert."""

    inspected = inspect_untrusted_content(chunk.content, source_id=chunk.id)
    safe_content = redact_secrets(chunk.content)
    document_node_id = _stable_id("document", tenant_id, chunk.document_id)
    nodes: dict[str, GraphNode] = {
        document_node_id: GraphNode(
            id=document_node_id,
            tenant_id=tenant_id,
            label="Document",
            properties={
                "name": redact_secrets(str(chunk.metadata.get("source", chunk.document_id)))
            },
        )
    }
    found: list[tuple[str, str]] = []
    for match in _IDENTIFIER_PATTERN.finditer(safe_content):
        kind = "Incident" if match.group("kind").upper() == "INC" else "Decision"
        found.append((kind, match.group(0).upper()))
    lowered = safe_content.casefold()
    for label, names in _CANONICAL_ENTITIES.items():
        found.extend((label, name) for name in names if name.casefold() in lowered)

    edges = []
    for label, name in sorted(set(found)):
        node_id = _stable_id(label.lower(), tenant_id, name)
        nodes[node_id] = GraphNode(
            id=node_id,
            tenant_id=tenant_id,
            label=label,
            properties={"name": name},
        )
        edge_id = _stable_id("mentions", tenant_id, f"{chunk.id}:{node_id}")
        edges.append(
            GraphEdge(
                id=edge_id,
                tenant_id=tenant_id,
                source_id=document_node_id,
                target_id=node_id,
                relationship="MENTIONS",
                properties={"chunk_id": chunk.id},
            )
        )
    return ExtractionResult(
        safe_content=safe_content,
        flagged=inspected.flagged,
        reasons=inspected.reasons,
        nodes=tuple(nodes.values()),
        edges=tuple(edges),
    )
