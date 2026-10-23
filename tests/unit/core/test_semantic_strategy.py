"""Semantic indexing/retrieval without real external services."""

import pytest

from rag_factory.strategies.semantic_search.indexer import SemanticIndexer, REQUIREMENTS
from rag_factory.strategies.semantic_search.retriever import SemanticRetriever
from tests.mocks.services import MockEmbedding, MockVectorStore


def test_semantic_index_and_cross_instance_retrieval():
    embedder, store = MockEmbedding(), MockVectorStore()
    manifest = SemanticIndexer(embedder, store, "deterministic-v1").index(
        {"first": "cat", "second": "elephant"}, "index-one"
    )
    assert manifest.embedding_dimensions == 2
    assert manifest.artifact_id == "index-one"
    assert REQUIREMENTS.indexing != REQUIREMENTS.retrieval
    assert SemanticRetriever(embedder, store, "deterministic-v1").retrieve(
        "cat", manifest, limit=1
    ) == ["first"]


def test_semantic_retrieval_rejects_incompatible_metadata():
    embedder, store = MockEmbedding(), MockVectorStore()
    manifest = SemanticIndexer(embedder, store, "model-a").index({"a": "cat"}, "idx")
    with pytest.raises(ValueError, match="embedding_model"):
        SemanticRetriever(embedder, store, "model-b").retrieve("cat", manifest)
    with pytest.raises(ValueError, match="distance_metric"):
        SemanticRetriever(embedder, store, "model-a", "cosine").retrieve("cat", manifest)


def test_semantic_strategy_rejects_bad_documents_and_limits():
    embedder, store = MockEmbedding(), MockVectorStore()
    indexer = SemanticIndexer(embedder, store, "model-a")
    with pytest.raises(ValueError, match="empty"):
        indexer.index({}, "idx")
    with pytest.raises(ValueError, match="identifiers"):
        indexer.index({"": "cat"}, "idx")
    manifest = indexer.index({"a": "cat"}, "idx")
    with pytest.raises(ValueError, match="positive"):
        SemanticRetriever(embedder, store, "model-a").retrieve("cat", manifest, limit=0)


def test_semantic_index_validates_provider_outputs():
    class BrokenEmbedding:
        def embed(self, texts):
            return [[1.0], [1.0, 2.0]]

    with pytest.raises(ValueError, match="consistent"):
        SemanticIndexer(BrokenEmbedding(), MockVectorStore(), "bad").index(
            {"a": "one", "b": "two"}, "idx"
        )
