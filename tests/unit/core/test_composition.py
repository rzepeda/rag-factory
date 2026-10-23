"""Composed indexing, retrieval, fusion and offline evaluation."""

import pytest

from rag_factory.evaluation.metrics import recall_at_k, reciprocal_rank_at_k
from rag_factory.pipelines.indexing import IndexStep, IndexingPipeline
from rag_factory.pipelines.retrieval import RetrievalSource, RetrievalPipeline
from rag_factory.strategies.hybrid_search.retriever import HybridRetriever
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever
from rag_factory.strategies.semantic_search.indexer import SemanticIndexer
from rag_factory.strategies.semantic_search.retriever import SemanticRetriever
from tests.mocks.services import MockEmbedding, MockKeywordStore, MockTokenizer, MockVectorStore


def test_independent_indexing_and_hybrid_retrieval():
    keyword, vector, embedding = MockKeywordStore(), MockVectorStore(), MockEmbedding()
    documents = {"a": "cat", "b": "elephant", "c": "cat cat"}
    semantic = SemanticIndexer(embedding, vector, "fake-v1")
    indexed = IndexingPipeline((
        IndexStep("lexical", KeywordIndexer(keyword).index),
        IndexStep("semantic", lambda docs: semantic.index(docs, "vector-index")),
    )).run(documents)
    assert indexed["lexical"] == 3
    manifest = indexed["semantic"]
    retrieval = RetrievalPipeline((
        RetrievalSource("keyword", KeywordRetriever(keyword, MockTokenizer()).retrieve),
        RetrievalSource("semantic", lambda q, n: SemanticRetriever(
            embedding, vector, "fake-v1"
        ).retrieve(q, manifest, n)),
    ))
    hybrid = HybridRetriever(retrieval)
    result = hybrid.retrieve("cat", 3)
    assert result[0] == "a"
    assert set(result) == {"a", "b", "c"}
    assert recall_at_k(result, {"a", "c"}, 3) == 1.0
    assert reciprocal_rank_at_k(result, {"a"}, 3) == 1.0


def test_composition_rejects_invalid_inputs():
    with pytest.raises(ValueError, match="unique"):
        RetrievalPipeline((RetrievalSource("x", lambda q, n: []),
                           RetrievalSource("x", lambda q, n: []))).search("query")
    with pytest.raises(ValueError, match="positive"):
        HybridRetriever(RetrievalPipeline(())).retrieve("query", 0)
    with pytest.raises(ValueError, match="positive"):
        recall_at_k(["a"], {"a"}, 0)
    with pytest.raises(ValueError, match="relevant"):
        recall_at_k(["a"], set(), 1)


def test_rrf_deduplicates_per_source_and_is_order_independent():
    p = RetrievalPipeline((
        RetrievalSource("x", lambda q, n: ["a", "a", "b"]),
        RetrievalSource("y", lambda q, n: ["b", "a"]),
    ))
    assert HybridRetriever(p).retrieve("q", 2) == ["a", "b"]
