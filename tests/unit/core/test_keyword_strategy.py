"""Contract behavior and keyword indexing/retrieval tests, offline."""

import pytest

from rag_factory.core.interfaces.services import (
    DocumentStoreService, EmbeddingService, GraphStoreService,
    KeywordStoreService, LLMService, RerankerService,
    TokenizerService, VectorStoreService,
)
from rag_factory.strategies.keyword_search.indexer import KeywordIndexer, REQUIREMENTS
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever
from tests.mocks.services import (
    MockDocumentStore, MockEmbedding, MockGraphStore, MockKeywordStore,
    MockLLM, MockReranker, MockTokenizer, MockVectorStore,
)


def test_all_defined_service_interfaces_have_mock_implementations():
    pairs = [
        (LLMService, MockLLM()),
        (TokenizerService, MockTokenizer()),
        (EmbeddingService, MockEmbedding()),
        (VectorStoreService, MockVectorStore()),
        (KeywordStoreService, MockKeywordStore()),
        (GraphStoreService, MockGraphStore()),
        (RerankerService, MockReranker()),
        (DocumentStoreService, MockDocumentStore()),
    ]
    for interface, implementation in pairs:
        assert isinstance(implementation, interface)


def test_service_mocks_have_deterministic_behavior():
    llm = MockLLM("ok")
    assert llm.generate("question") == "ok"
    assert llm.prompts == ["question"]
    assert MockTokenizer().tokenize("Hello, HELLO!") == ["hello", "hello"]
    assert MockEmbedding().embed(["a"]) == MockEmbedding().embed(["a"])
    vectors = MockVectorStore()
    vectors.upsert({"near": [0.0, 0.0], "far": [4.0, 4.0]})
    assert vectors.search([0, 0], 2) == ["near", "far"]
    with pytest.raises(ValueError, match="dimensions"):
        vectors.search([0], 1)
    graph = MockGraphStore()
    graph.add_edge("a", "b")
    assert graph.neighbors("a") == ["b"]
    assert MockReranker().rerank("blue", {"a": "red", "b": "blue car"})[0] == "b"
    documents = MockDocumentStore()
    documents.upsert({"x": "text"})
    assert documents.get("x") == "text"
    assert documents.get("missing") is None


def test_keyword_index_and_retrieve_against_injected_store():
    store = MockKeywordStore()
    indexer = KeywordIndexer(store)
    retriever = KeywordRetriever(store, MockTokenizer())
    assert indexer.index({"d1": "blue car", "d2": "red car", "d3": "blue sky"}) == 3
    assert retriever.retrieve("BLUE", limit=5) == ["d1", "d3"]
    assert retriever.retrieve("missing") == []
    assert retriever.retrieve("") == []
    assert REQUIREMENTS.indexing != REQUIREMENTS.retrieval


def test_keyword_store_upsert_and_ranking():
    store = MockKeywordStore()
    indexer = KeywordIndexer(store)
    retriever = KeywordRetriever(store, MockTokenizer())
    indexer.index({"b": "dog", "a": "dog dog"})
    assert retriever.retrieve("dog dog", 1) == ["a"]
    indexer.index({"a": "cat"})
    assert retriever.retrieve("dog", 2) == ["b"]


def test_keyword_strategy_rejects_invalid_inputs():
    store = MockKeywordStore()
    indexer = KeywordIndexer(store)
    with pytest.raises(ValueError, match="nonempty"):
        indexer.index({"": "bad"})
    with pytest.raises(ValueError, match="string text"):
        indexer.index({"a": None})
    with pytest.raises(ValueError, match="positive"):
        KeywordRetriever(store, MockTokenizer()).retrieve("query", 0)
