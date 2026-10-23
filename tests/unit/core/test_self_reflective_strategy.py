"""Bounded retrieval-time relevance grading using deterministic mocks."""

import pytest

from rag_factory.strategies.self_reflective.grading.grader import RelevanceGrader
from rag_factory.strategies.self_reflective.retriever import SelfReflectiveRetriever
from tests.mocks.services import MockDocumentStore, MockLLM


def test_grader_filters_documents_and_avoids_duplicate_checks():
    documents = MockDocumentStore()
    documents.upsert({"one": "astronomy", "two": "dogs"})
    llm = MockLLM("YES")
    calls = []

    def search(query, limit):
        calls.append((query, limit))
        return ["one", "one", "two"]

    retrieval = SelfReflectiveRetriever(search, documents, RelevanceGrader(llm))
    assert retrieval.retrieve("astronomy", 2) == ["one", "two"]
    assert calls == [("astronomy", 2)]
    assert len(llm.prompts) == 2


def test_negative_grades_and_bounded_retries():
    documents = MockDocumentStore()
    documents.upsert({"a": "unrelated"})
    llm = MockLLM("NO")
    count = []
    def search(query, limit):
        count.append(1)
        return ["a"]
    retrieval = SelfReflectiveRetriever(search, documents, RelevanceGrader(llm), max_attempts=3)
    assert retrieval.retrieve("question", 2) == []
    assert len(count) == 3
    assert len(llm.prompts) == 1


def test_bad_grade_and_missing_document_fail():
    documents = MockDocumentStore()
    documents.upsert({"a": "text"})
    with pytest.raises(ValueError, match="YES or NO"):
        SelfReflectiveRetriever(
            lambda q, n: ["a"], documents, RelevanceGrader(MockLLM("maybe"))
        ).retrieve("query")
    with pytest.raises(ValueError, match="Missing candidate"):
        SelfReflectiveRetriever(
            lambda q, n: ["missing"], documents, RelevanceGrader(MockLLM("YES"))
        ).retrieve("query")


def test_empty_query_and_invalid_limits():
    strategy = SelfReflectiveRetriever(
        lambda q, n: [], MockDocumentStore(), RelevanceGrader(MockLLM("YES"))
    )
    assert strategy.retrieve("") == []
    with pytest.raises(ValueError, match="positive"):
        strategy.retrieve("query", 0)
