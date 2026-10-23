"""Configuration loading, validation order and service cleanup."""

import pytest

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.config import load_keyword_config
from rag_factory.factory.rag_factory import RAGFactory
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry
from rag_factory.services.keyword.memory import MemoryKeywordStore
from rag_factory.services.tokenizer.regex import RegexTokenizer


def test_yaml_keyword_configuration(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("""
services:
  index:
    interface: keyword_store
    implementation: memory
  tokens:
    interface: tokenizer
    implementation: regex
keyword:
  bindings:
    keyword_store: index
    tokenizer: tokens
""")
    config = load_keyword_config(path)
    with RAGFactory().build_keyword(config.services, config.bindings) as pipeline:
        pipeline.indexer.index({"doc": "composable retrieval"})
        assert pipeline.retriever.retrieve("RETRIEVAL") == ["doc"]


def test_yaml_rejects_invalid_documents_and_unset_variables(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("services: []\nkeyword: {}")
    with pytest.raises(ValueError, match="Expected services"):
        load_keyword_config(path)
    path.write_text("""
services:
  x:
    interface: keyword_store
    implementation: memory
    parameters:
      secret: ${RAG_FACTORY_TEST_UNSET_VARIABLE_XYZ}
keyword:
  bindings: {}
""")
    with pytest.raises(ValueError, match="Missing environment variable"):
        load_keyword_config(path)


def test_factory_validates_before_constructing_any_service():
    created = []
    registry = ServiceRegistry()
    registry.register(ProviderDescriptor("keyword_store", "tracked", frozenset({"upsert", "search"})),
                      lambda: created.append("created") or MemoryKeywordStore())
    registry.register(ProviderDescriptor("tokenizer", "limited", frozenset()),
                      RegexTokenizer)
    with pytest.raises(ValueError, match="does not satisfy"):
        RAGFactory(registry).build_keyword({
            "store": ServiceConfig("keyword_store", "tracked"),
            "tokens": ServiceConfig("tokenizer", "limited"),
        }, {"keyword_store": "store", "tokenizer": "tokens"})
    assert created == []


def test_factory_closes_owned_instances_after_error_and_context_exit():
    closed = []

    class ClosableStore(MemoryKeywordStore):
        def close(self):
            closed.append("store")

    registry = ServiceRegistry()
    registry.register(ProviderDescriptor("keyword_store", "closable", frozenset({"upsert", "search"})),
                      ClosableStore)
    registry.register(ProviderDescriptor("tokenizer", "bad", frozenset({"tokenize"})),
                      lambda: object())
    configs = {
        "store": ServiceConfig("keyword_store", "closable"),
        "tokens": ServiceConfig("tokenizer", "bad"),
    }
    bindings = {"keyword_store": "store", "tokenizer": "tokens"}
    with pytest.raises(TypeError, match="does not implement"):
        RAGFactory(registry).build_keyword(configs, bindings)
    assert closed == ["store"]
    registry2 = ServiceRegistry()
    registry2.register(ProviderDescriptor("keyword_store", "closable", frozenset({"upsert", "search"})),
                       ClosableStore)
    registry2.register(ProviderDescriptor("tokenizer", "regex", frozenset({"tokenize"})),
                       RegexTokenizer)
    with RAGFactory(registry2).build_keyword({
        "store": ServiceConfig("keyword_store", "closable"),
        "tokens": ServiceConfig("tokenizer", "regex"),
    }, bindings) as pipeline:
        pipeline.indexer.index({"a": "hello"})
        assert pipeline.retriever.retrieve("hello") == ["a"]
    pipeline.close()
    assert closed == ["store", "store"]
