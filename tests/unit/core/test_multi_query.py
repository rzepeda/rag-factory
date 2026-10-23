"""Offline multi-query and expansion behavior using the shared LLM mock."""

import pytest
from rag_factory.strategies.multi_query.retriever import MultiQueryRetriever, REQUIREMENTS
from rag_factory.strategies.query_expansion.expansion.expander import QueryExpander
from rag_factory.strategies.query_expansion.retriever import QueryExpansionRetriever
from tests.mocks.services import MockLLM


def test_variants_deduplicated_and_bounded():
    llm = MockLLM("dog\nDOG\ncat\nfish")
    assert QueryExpander(llm, max_variants=2).expand("dog") == ["dog", "cat", "fish"]
    assert len(llm.prompts) == 1


def test_multi_query_fuses_results_from_distinct_queries():
    llm = MockLLM("cat\nkitten")
    calls = []

    def search(query, limit):
        calls.append(query)
        return {"feline": ["a", "b"], "cat": ["a"], "kitten": ["b", "c"]}.get(query, [])

    result = MultiQueryRetriever(QueryExpander(llm), search).retrieve("feline", 3)
    assert result == ["a", "b", "c"]
    assert calls == ["feline", "cat", "kitten"]
    assert REQUIREMENTS.retrieval[0].interface == "llm"


def test_expansion_strategy_and_blank_queries():
    llm = MockLLM("synonym")
    seen = []

    def search(query, limit):
        seen.append(query)
        return [query]

    retriever = QueryExpansionRetriever(llm, search)
    assert retriever.retrieve("") == []
    assert seen == []
    assert retriever.retrieve("original", 3) == ["original", "synonym"]


def test_invalid_configuration_and_llm_outputs():
    with pytest.raises(ValueError, match="positive"):
        QueryExpander(MockLLM(), 0).expand("hello")
    with pytest.raises(ValueError, match="positive"):
        MultiQueryRetriever(QueryExpander(MockLLM()), lambda q, n: []).retrieve("hello", 0)

    class InvalidLLM:
        def generate(self, prompt):
            return None

    with pytest.raises(TypeError, match="text"):
        QueryExpander(InvalidLLM()).expand("hello")
