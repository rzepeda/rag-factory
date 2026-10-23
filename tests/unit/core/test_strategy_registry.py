"""Strategy registration and YAML composition, no real services."""

import pytest

from rag_factory.factory.retrieval_config import load_retrieval_config
from rag_factory.factory.strategy_manager import StrategyConfig, StrategyRegistry
from rag_factory.strategies.keyword_search.retriever import KeywordRetriever
from rag_factory.strategies.hybrid_search.retriever import HybridRetriever
from tests.mocks.services import MockKeywordStore, MockTokenizer


def test_configured_strategy_composition_and_fusion(tmp_path):
    store = MockKeywordStore()
    store.upsert({"a": "cat dog", "b": "dog", "c": "cat"})
    registry = StrategyRegistry()
    registry.register("keyword", lambda params: KeywordRetriever(store, MockTokenizer()))
    path = tmp_path / "retrieval.yaml"
    path.write_text("""
retrieval:
  lexical_a:
    implementation: keyword
  lexical_b:
    implementation: keyword
""")
    cfg = load_retrieval_config(path)
    retrieval = registry.compose(cfg.strategies)
    assert retrieval.search("cat", 3) == {
        "lexical_a": ["a", "c"], "lexical_b": ["a", "c"]
    }
    assert HybridRetriever(retrieval).retrieve("cat", 2) == ["a", "c"]


def test_unknown_strategy_rejected_before_builders_run():
    created = []
    registry = StrategyRegistry()
    registry.register("known", lambda params: created.append(1))
    with pytest.raises(ValueError, match="Unknown retrieval"):
        registry.compose({
            "first": StrategyConfig("known"),
            "bad": StrategyConfig("missing"),
        })
    assert created == []


def test_invalid_registration_and_retriever_shape():
    registry = StrategyRegistry()
    registry.register("invalid", lambda params: object())
    with pytest.raises(TypeError, match="retrieve"):
        registry.build(StrategyConfig("invalid"))
    with pytest.raises(ValueError, match="duplicate"):
        registry.register("invalid", lambda params: object())


def test_retrieval_yaml_rejects_bad_fields(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("retrieval: []")
    with pytest.raises(ValueError, match="nonempty mapping"):
        load_retrieval_config(path)
    path.write_text("retrieval:\n  x:\n    implementation: keyword\n    parameters: []\n")
    with pytest.raises(ValueError, match="Parameters"):
        load_retrieval_config(path)
