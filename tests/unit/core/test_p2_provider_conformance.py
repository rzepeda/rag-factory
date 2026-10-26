"""Reusable P2 conformance harness exercised across mock and memory adapters."""
import pytest

from rag_factory.services.document.memory import MemoryDocumentStore
from rag_factory.services.graph.memory import MemoryGraphStore
from rag_factory.services.keyword.memory import MemoryKeywordStore
from rag_factory.services.tokenizer.regex import RegexTokenizer
from rag_factory.services.vector.memory import MemoryVectorStore
from rag_factory.testing.provider_contracts import check_provider_contract
from tests.mocks.services import (
    MockDocumentStore, MockEmbedding, MockGraphStore, MockKeywordStore,
    MockLLM, MockReranker, MockTokenizer, MockVectorStore,
)


@pytest.mark.parametrize("interface,factory", [
    ("keyword_store", MockKeywordStore),
    ("keyword_store", MemoryKeywordStore),
    ("tokenizer", MockTokenizer),
    ("tokenizer", RegexTokenizer),
    ("embedding", MockEmbedding),
    ("vector_store", MockVectorStore),
    ("vector_store", MemoryVectorStore),
    ("document_store", MockDocumentStore),
    ("document_store", MemoryDocumentStore),
    ("graph_store", MockGraphStore),
    ("graph_store", MemoryGraphStore),
    ("llm", lambda: MockLLM("test answer")),
    ("reranker", MockReranker),
])
def test_implementations_meet_shared_contract(interface, factory):
    check_provider_contract(interface, factory)


def test_bad_providers_and_unsupported_interfaces_fail():
    with pytest.raises(ValueError, match="Unknown provider"):
        check_provider_contract("unknown", lambda: object())
    with pytest.raises(AssertionError, match="required operations"):
        check_provider_contract("keyword_store", lambda: object())
    with pytest.raises(TypeError, match="factory"):
        check_provider_contract("keyword_store", object())


def test_conformance_always_cleans_up_even_on_failure():
    closed = []
    class BrokenKeyword:
        def upsert(self, documents):
            pass
        def search(self, query, k):
            return []
        def close(self):
            closed.append(True)

    with pytest.raises(AssertionError):
        check_provider_contract("keyword_store", BrokenKeyword)
    assert closed == [True]
