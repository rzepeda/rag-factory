"""Graph-assisted retrieval using deterministic offline mocks."""

import pytest

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.strategies.knowledge_graph.indexer import KnowledgeGraphIndexer, REQUIREMENTS
from rag_factory.strategies.knowledge_graph.retriever import KnowledgeGraphRetriever
from tests.mocks.services import MockDocumentStore, MockGraphStore


def setup_graph():
    graph, documents = MockGraphStore(), MockDocumentStore()
    manifest = KnowledgeGraphIndexer(graph, documents).index(
        {"root": "main", "alpha": "first", "beta": "second", "leaf": "deep"},
        [("root", "beta"), ("root", "alpha"), ("alpha", "leaf"), ("leaf", "root")],
        "graph-1",
    )
    return KnowledgeGraphRetriever(graph, documents), manifest


def test_graph_traversal_bounded_deterministic_and_cycle_safe():
    retriever, manifest = setup_graph()
    assert retriever.retrieve("root", manifest, max_hops=0) == [("root", "main")]
    assert retriever.retrieve("root", manifest, max_hops=1) == [
        ("root", "main"), ("alpha", "first"), ("beta", "second")
    ]
    assert retriever.retrieve("root", manifest, limit=3, max_hops=5) == [
        ("root", "main"), ("alpha", "first"), ("beta", "second")
    ]
    assert len(retriever.retrieve("root", manifest, max_hops=5)) == 4
    assert REQUIREMENTS.indexing != REQUIREMENTS.retrieval


def test_rejects_unknown_edges_and_invalid_options():
    graph, documents = MockGraphStore(), MockDocumentStore()
    with pytest.raises(ValueError, match="known document"):
        KnowledgeGraphIndexer(graph, documents).index(
            {"a": "text"}, [("a", "missing")], "idx"
        )
    retriever, manifest = setup_graph()
    with pytest.raises(ValueError, match="positive"):
        retriever.retrieve("root", manifest, 0)
    with pytest.raises(ValueError, match="nonnegative"):
        retriever.retrieve("root", manifest, max_hops=-1)


def test_incompatible_manifest_and_missing_documents():
    retriever, _ = setup_graph()
    with pytest.raises(ValueError, match="Missing index capabilities"):
        retriever.retrieve("root", IndexManifest("other", frozenset({"documents"}), "1"))
    retriever.documents.documents.pop("root")
    manifest = IndexManifest("graph", frozenset({"graph", "documents"}), "1")
    with pytest.raises(ValueError, match="Missing graph document"):
        retriever.retrieve("root", manifest)
