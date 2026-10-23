"""Reranking tests use only offline mock services."""

import pytest

from rag_factory.strategies.reranking.retriever import RerankingRetriever, REQUIREMENTS
from tests.mocks.services import MockDocumentStore, MockReranker


def test_reranking_reorders_candidates_and_preserves_limit():
    documents = MockDocumentStore()
    documents.upsert({"a": "bird", "b": "cat", "c": "cat dog"})
    requested = []

    def search(query, limit):
        requested.append((query, limit))
        return ["a", "b", "c", "c"]

    reranker = RerankingRetriever(search, documents, MockReranker())
    assert reranker.retrieve("cat", 2) == ["b", "c"]
    assert requested == [("cat", 6)]
    assert REQUIREMENTS.retrieval[0].interface == "document_store"


def test_empty_query_never_calls_search():
    assert RerankingRetriever(
        lambda query, limit: (_ for _ in ()).throw(AssertionError("called")),
        MockDocumentStore(), MockReranker(),
    ).retrieve("  ") == []


def test_missing_document_and_invalid_options():
    retriever = RerankingRetriever(lambda query, limit: ["missing"],
                                   MockDocumentStore(), MockReranker())
    with pytest.raises(ValueError, match="Missing candidate"):
        retriever.retrieve("cat")
    with pytest.raises(ValueError, match="positive"):
        retriever.retrieve("cat", 0)
    with pytest.raises(ValueError, match="positive"):
        RerankingRetriever(lambda q, n: [], MockDocumentStore(), MockReranker(), 0).retrieve("cat")


@pytest.mark.parametrize("ranking", [["unknown"], ["a", "a"], []])
def test_reranker_cannot_introduce_or_drop_candidates(ranking):
    class BrokenReranker:
        def rerank(self, query, documents):
            return ranking

    documents = MockDocumentStore()
    documents.upsert({"a": "cat", "b": "dog"})
    retriever = RerankingRetriever(lambda q, n: ["a", "b"], documents, BrokenReranker())
    with pytest.raises(ValueError, match="exactly"):
        retriever.retrieve("cat")
