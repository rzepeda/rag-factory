"""Late chunking indexes full-context token vectors rather than isolated chunks."""

import pytest

from rag_factory.strategies.late_chunking.indexer import LateChunkingIndexer, REQUIREMENTS
from rag_factory.strategies.late_chunking.retriever import LateChunkingRetriever
from tests.mocks.services import MockVectorStore


class ContextAwareEncoder:
    def __init__(self):
        self.calls = []

    def encode_tokens(self, tokens):
        self.calls.append(list(tokens))
        context = float(len(tokens))
        return [[context, float(i)] for i in range(len(tokens))]


class CompatibleQueryEncoder:
    def embed(self, texts):
        return [[4.0, 0.5] for _ in texts]


def test_pool_after_full_document_encoding_and_retrieve():
    encoder, store = ContextAwareEncoder(), MockVectorStore()
    manifest = LateChunkingIndexer(encoder, store, "reference-v1").index(
        ["one", "two", "three", "four"],
        {"first": (0, 2), "second": (2, 4)},
        "artifact-1",
    )
    assert encoder.calls == [["one", "two", "three", "four"]]
    assert store.records["first"] == (4.0, 0.5)
    assert store.records["second"] == (4.0, 2.5)
    assert LateChunkingRetriever(CompatibleQueryEncoder(), store, "reference-v1").retrieve(
        "query", manifest, 1
    ) == ["first"]
    assert REQUIREMENTS.indexing != REQUIREMENTS.retrieval


def test_rejects_invalid_spans_before_encoding():
    encoder = ContextAwareEncoder()
    indexer = LateChunkingIndexer(encoder, MockVectorStore(), "reference-v1")
    with pytest.raises(ValueError, match="half-open"):
        indexer.index(["a", "b"], {"bad": (1, 1)}, "artifact")
    assert encoder.calls == []


def test_incompatible_models_and_dimensions():
    encoder, store = ContextAwareEncoder(), MockVectorStore()
    manifest = LateChunkingIndexer(encoder, store, "reference-v1").index(
        ["a", "b"], {"a": (0, 2)}, "artifact"
    )
    with pytest.raises(ValueError, match="embedding_model"):
        LateChunkingRetriever(CompatibleQueryEncoder(), store, "other").retrieve("q", manifest)
    class WrongDimensions:
        def embed(self, texts):
            return [[1.0]]
    with pytest.raises(ValueError, match="dimensions"):
        LateChunkingRetriever(WrongDimensions(), store, "reference-v1").retrieve("q", manifest)


def test_inconsistent_token_vectors_rejected():
    class BrokenEncoder:
        def encode_tokens(self, tokens):
            return [[1.0], [1.0, 2.0]]
    with pytest.raises(ValueError, match="consistent"):
        LateChunkingIndexer(BrokenEncoder(), MockVectorStore(), "bad").index(
            ["a", "b"], {"x": (0, 2)}, "artifact"
        )
