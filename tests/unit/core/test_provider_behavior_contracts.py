"""Reusable service behavior contracts across implementations.

These are behavioral assertions, not protocol/isinstance checks. External provider
adapters can join the same parameterized suites when test infrastructure exists.
"""

import pytest

from rag_factory.services.keyword.memory import MemoryKeywordStore
from rag_factory.services.tokenizer.regex import RegexTokenizer
from tests.mocks.services import (
    MockDocumentStore, MockEmbedding, MockGraphStore, MockKeywordStore,
    MockLLM, MockReranker, MockTokenizer, MockVectorStore,
)


@pytest.fixture(params=[MockKeywordStore, MemoryKeywordStore], ids=["mock", "memory"])
def keyword_store(request):
    return request.param()


@pytest.fixture(params=[MockTokenizer, RegexTokenizer], ids=["mock", "regex"])
def tokenizer(request):
    return request.param()


def test_keyword_store_shared_contract(keyword_store):
    keyword_store.upsert({"b": "cat", "a": "cat cat", "c": "dog"})
    assert keyword_store.search(["cat", "cat"], 2) == ["a", "b"]
    keyword_store.upsert({"a": "dog"})
    assert keyword_store.search(["cat"], 3) == ["b"]
    assert keyword_store.search([], 2) == []
    with pytest.raises(ValueError, match="positive"):
        keyword_store.search(["cat"], 0)


def test_tokenizer_shared_contract(tokenizer):
    assert list(tokenizer.tokenize("Hello, HELLO!")) == ["hello", "hello"]
    assert list(tokenizer.tokenize("")) == []


def test_embedding_mock_contract():
    embedder = MockEmbedding()
    assert embedder.embed([]) == []
    result = embedder.embed(["cat", "dog"])
    assert len(result) == 2
    assert all(len(vector) == 2 for vector in result)
    assert result == embedder.embed(["cat", "dog"])


def test_vector_store_mock_contract():
    store = MockVectorStore()
    store.upsert({"far": [3.0, 3.0], "near": [0.0, 0.0]})
    assert store.search([0.0, 0.0], 2) == ["near", "far"]
    store.upsert({"far": [0.0, 0.0]})
    assert store.search([0.0, 0.0], 2) == ["far", "near"]
    with pytest.raises(ValueError, match="positive"):
        store.search([0.0, 0.0], 0)
    with pytest.raises(ValueError, match="dimensions"):
        store.search([0.0], 1)


def test_document_store_mock_contract():
    store = MockDocumentStore()
    assert store.get("missing") is None
    store.upsert({"one": "initial"})
    store.upsert({"one": "changed"})
    assert store.get("one") == "changed"


def test_graph_store_mock_contract():
    store = MockGraphStore()
    assert store.neighbors("missing") == []
    store.add_edge("a", "b")
    store.add_edge("a", "c")
    store.add_edge("a", "b")
    assert store.neighbors("a") == ["b", "c"]


def test_llm_mock_contract():
    llm = MockLLM("result")
    assert llm.generate("question") == "result"
    assert llm.generate("other") == "result"
    assert llm.prompts == ["question", "other"]


def test_reranker_mock_contract():
    reranker = MockReranker()
    documents = {"z": "bird", "b": "cat", "a": "cat dog"}
    assert reranker.rerank("cat", documents) == ["a", "b", "z"]
