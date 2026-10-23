"""Hierarchical retrieval with fake storage and validated parent-child links."""

import pytest

from rag_factory.core.index_manifest import IndexManifest
from rag_factory.strategies.hierarchical_rag.indexer import HierarchicalIndexer
from rag_factory.strategies.hierarchical_rag.retriever import HierarchicalRetriever
from tests.mocks.services import MockDocumentStore, MockKeywordStore, MockTokenizer


def build():
    keywords, documents = MockKeywordStore(), MockDocumentStore()
    manifest, hierarchy = HierarchicalIndexer(keywords, documents).index(
        parents={"p1": "Parent on planets", "p2": "Parent on animals"},
        children={"c1": "Mars planet", "c2": "Saturn planet", "c3": "cat animal"},
        child_to_parent={"c1": "p1", "c2": "p1", "c3": "p2"},
        artifact_id="hierarchical-index",
    )
    return HierarchicalRetriever(keywords, documents, MockTokenizer(), hierarchy), manifest


def test_searches_children_and_expands_original_parents_once():
    retriever, manifest = build()
    assert retriever.retrieve("planet", manifest) == [("p1", "Parent on planets")]
    assert retriever.retrieve("animal", manifest) == [("p2", "Parent on animals")]
    assert retriever.retrieve("", manifest) == []


def test_rejects_invalid_hierarchy_and_missing_parent():
    indexer = HierarchicalIndexer(MockKeywordStore(), MockDocumentStore())
    with pytest.raises(ValueError, match="unknown parent"):
        indexer.index({"p": "parent"}, {"c": "child"}, {"c": "absent"}, "idx")
    with pytest.raises(ValueError, match="exactly one parent"):
        indexer.index({"p": "parent"}, {"c": "child"}, {}, "idx")
    with pytest.raises(ValueError, match="own parent"):
        indexer.index({"p": "text"}, {"p": "text"}, {"p": "p"}, "idx")


def test_rejects_incompatible_index_manifest():
    retriever, _ = build()
    with pytest.raises(ValueError, match="Missing index capabilities"):
        retriever.retrieve("planet", IndexManifest("bad", frozenset({"keywords"}), "1"))


def test_missing_parent_document_is_explicit_error():
    retriever, manifest = build()
    retriever.documents.documents.clear()
    with pytest.raises(ValueError, match="Missing parent document"):
        retriever.retrieve("planet", manifest)
