"""Shared fail-fast payload contract for the unified indexing entry point.

Validation is entirely side-effect-free: malformed payloads never reach providers.
Individual strategy indexers retain their own direct-API validation.
"""
from collections.abc import Mapping

FIELDS = {
    "keyword": frozenset({"documents"}),
    "semantic": frozenset({"documents"}),
    "semantic_chunking": frozenset({"documents"}),
    "contextual": frozenset({"chunks", "source_document"}),
    "hierarchical": frozenset({"parents", "children", "child_to_parent"}),
    "knowledge_graph": frozenset({"documents", "edges"}),
    "late_chunking": frozenset({"tokens", "spans"}),
}


def _texts(value, label):
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{label} must be a nonempty mapping")
    if any(not isinstance(key, str) or not key.strip()
           or not isinstance(text, str) or not text.strip()
           for key, text in value.items()):
        raise ValueError(f"{label} must contain nonempty string IDs and text")


def validate_index_payload(kind: str, payload: Mapping) -> None:
    """Validate required fields and cross-field relationships before any writes."""
    if kind not in FIELDS:
        raise ValueError(f"{kind} does not implement an indexing stage")
    if not isinstance(payload, Mapping):
        raise ValueError("Index payload must be a mapping")
    required = FIELDS[kind]
    missing = required.difference(payload)
    if missing:
        raise ValueError(f"Missing index payload fields: {', '.join(sorted(missing))}")
    extra = set(payload).difference(required | {"artifact_id"})
    if extra:
        raise ValueError(f"Unexpected index payload fields: {', '.join(sorted(map(str, extra)))}")
    if "artifact_id" in payload and (
        not isinstance(payload["artifact_id"], str) or not payload["artifact_id"].strip()
    ):
        raise ValueError("artifact_id must be a nonempty string")

    if kind in {"keyword", "semantic", "semantic_chunking", "knowledge_graph"}:
        _texts(payload["documents"], "documents")
    if kind == "contextual":
        _texts(payload["chunks"], "chunks")
        if not isinstance(payload["source_document"], str) or not payload["source_document"].strip():
            raise ValueError("source_document must be nonempty text")
    if kind == "hierarchical":
        _texts(payload["parents"], "parents")
        _texts(payload["children"], "children")
        relationships = payload["child_to_parent"]
        if not isinstance(relationships, Mapping) or set(relationships) != set(payload["children"]):
            raise ValueError("child_to_parent must map every child exactly once")
        if any(not isinstance(parent, str) or parent not in payload["parents"]
               or child == parent for child, parent in relationships.items()):
            raise ValueError("child_to_parent must reference known, distinct parents")
    if kind == "knowledge_graph":
        edges = payload["edges"]
        if not isinstance(edges, (list, tuple)):
            raise ValueError("edges must be a sequence of document-ID pairs")
        if any(not isinstance(edge, (list, tuple)) or len(edge) != 2
               or any(not isinstance(node, str) or node not in payload["documents"]
                      for node in edge) for edge in edges):
            raise ValueError("edges must connect known document IDs")
    if kind == "late_chunking":
        tokens, spans = payload["tokens"], payload["spans"]
        if not isinstance(tokens, (list, tuple)) or not tokens or any(
            not isinstance(token, str) or not token.strip() for token in tokens
        ):
            raise ValueError("tokens must be a nonempty sequence of strings")
        if not isinstance(spans, Mapping) or not spans:
            raise ValueError("spans must be a nonempty mapping")
        for identifier, bounds in spans.items():
            if (not isinstance(identifier, str) or not identifier.strip()
                or not isinstance(bounds, tuple) or len(bounds) != 2
                or any(type(n) is not int for n in bounds)
                or not 0 <= bounds[0] < bounds[1] <= len(tokens)):
                raise ValueError("spans must contain valid half-open token ranges")
