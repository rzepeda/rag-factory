"""Mock-only tests for allowlisted agentic retrieval routing."""

import pytest

from rag_factory.strategies.agentic_rag.retriever import AgenticRAGRetriever, REQUIREMENTS
from tests.mocks.services import MockLLM


def test_routes_to_allowlisted_tool_and_respects_limit():
    llm = MockLLM("keyword")
    calls = []
    def search(query, limit):
        calls.append((query, limit))
        return ["a", "b", "a"]
    agent = AgenticRAGRetriever(llm, {"keyword": search})
    assert agent.retrieve("cats", 2) == ["a", "b"]
    assert calls == [("cats", 2)]
    assert REQUIREMENTS.retrieval[0].interface == "llm"


def test_multiple_tools_deduplicate_and_observe_step_bound():
    class SequentialLLM:
        def __init__(self):
            self.choices = iter(["lexical", "semantic"])
            self.prompts = []
        def generate(self, prompt):
            self.prompts.append(prompt)
            return next(self.choices)

    llm = SequentialLLM()
    agent = AgenticRAGRetriever(
        llm,
        {"lexical": lambda q, n: ["a"], "semantic": lambda q, n: ["a", "b"]},
        max_steps=2,
    )
    assert agent.retrieve("cats", 3) == ["a", "b"]
    assert len(llm.prompts) == 2
    assert "semantic" in llm.prompts[1] and "lexical" not in llm.prompts[1]


def test_rejects_unauthorized_and_duplicate_tool_choice():
    for response in ("shell", "keyword\nother"):
        agent = AgenticRAGRetriever(MockLLM(response), {"keyword": lambda q, n: []})
        with pytest.raises(ValueError, match="unknown or unavailable"):
            agent.retrieve("cats")


def test_rejects_invalid_limits_tools_and_outputs():
    with pytest.raises(ValueError, match="positive"):
        AgenticRAGRetriever(MockLLM("x"), {"x": lambda q, n: []}).retrieve("cats", 0)
    with pytest.raises(ValueError, match="positive"):
        AgenticRAGRetriever(MockLLM("x"), {"x": lambda q, n: []}, 0).retrieve("cats")
    with pytest.raises(ValueError, match="Tools"):
        AgenticRAGRetriever(MockLLM("x"), {}).retrieve("cats")
    with pytest.raises(ValueError, match="document IDs"):
        AgenticRAGRetriever(MockLLM("x"), {"x": lambda q, n: [""]}).retrieve("cats")
    assert AgenticRAGRetriever(MockLLM("x"), {"x": lambda q, n: []}).retrieve("") == []
