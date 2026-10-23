"""Offline self-correcting search query rewrites."""
import pytest
from rag_factory.strategies.self_reflective.refinement import QueryRefinementRetriever
from tests.mocks.services import MockLLM

def test_retries_with_a_distinct_rewritten_query():
    queries = []
    def search(q, limit):
        queries.append(q)
        return ["found"] if q == "corrected" else []
    result = QueryRefinementRetriever(MockLLM("corrected"), search).retrieve("initial")
    assert result == ["found"]
    assert queries == ["initial", "corrected"]

def test_stops_on_duplicate_rewrites_and_invalid_output():
    calls = []
    def empty(q, n):
        calls.append(q)
        return []
    assert QueryRefinementRetriever(MockLLM("same"), empty, 3).retrieve("same") == []
    assert calls == ["same"]
    with pytest.raises(ValueError, match="nonempty"):
        QueryRefinementRetriever(MockLLM(" "), empty).retrieve("query")

def test_zero_rewrites_and_invalid_limits():
    llm = MockLLM("unused")
    assert QueryRefinementRetriever(llm, lambda q, n: [], 0).retrieve("query") == []
    assert llm.prompts == []
    with pytest.raises(ValueError):
        QueryRefinementRetriever(llm, lambda q, n: []).retrieve("query", 0)
