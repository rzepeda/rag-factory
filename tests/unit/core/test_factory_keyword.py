"""Configuration-driven keyword pipeline tests; entirely offline."""

import pytest

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.rag_factory import RAGFactory
from rag_factory.factory.service_registry import (
    ServiceConfig, ServiceRegistry, default_registry,
)
from rag_factory.services.keyword.memory import MemoryKeywordStore
from rag_factory.services.tokenizer.regex import RegexTokenizer
from tests.mocks.services import MockKeywordStore, MockTokenizer


def settings(store_implementation="memory", tokenizer_implementation="regex"):
    return {
        "keyword_store_a": ServiceConfig("keyword_store", store_implementation),
        "tokenizer_a": ServiceConfig("tokenizer", tokenizer_implementation),
    }


BINDINGS = {"keyword_store": "keyword_store_a", "tokenizer": "tokenizer_a"}


def test_default_implementations_build_a_working_pipeline():
    pipeline = RAGFactory().build_keyword(settings(), BINDINGS)
    assert isinstance(pipeline.indexer.store, MemoryKeywordStore)
    assert isinstance(pipeline.retriever.tokenizer, RegexTokenizer)
    assert pipeline.indexer.store is pipeline.retriever.store
    pipeline.indexer.index({"one": "red cat", "two": "blue dog"})
    assert pipeline.retriever.retrieve("CAT") == ["one"]


def test_swapping_providers_is_configuration_only():
    registry = default_registry()
    registry.register(
        ProviderDescriptor("keyword_store", "mock", frozenset({"upsert", "search"})),
        MockKeywordStore,
    )
    registry.register(
        ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})),
        MockTokenizer,
    )
    pipeline = RAGFactory(registry).build_keyword(settings("mock", "mock"), BINDINGS)
    assert isinstance(pipeline.indexer.store, MockKeywordStore)
    pipeline.indexer.index({"a": "dog dog", "b": "dog"})
    assert pipeline.retriever.retrieve("dog", 1) == ["a"]


def test_named_instances_are_isolated():
    factory = RAGFactory()
    first = factory.build_keyword(settings(), BINDINGS)
    second = factory.build_keyword(settings(), BINDINGS)
    first.indexer.index({"one": "orange"})
    assert second.retriever.retrieve("orange") == []


def test_unknown_implementation_and_missing_binding_rejected():
    with pytest.raises(ValueError, match="Unknown provider"):
        RAGFactory().build_keyword(settings("unregistered"), BINDINGS)
    with pytest.raises(ValueError, match="Missing configured"):
        RAGFactory().build_keyword(settings(), {"keyword_store": "keyword_store_a"})


def test_incompatible_capabilities_and_duplicate_registration():
    registry = ServiceRegistry()
    registry.register(ProviderDescriptor("keyword_store", "readonly", frozenset({"search"})),
                      MockKeywordStore)
    registry.register(ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})),
                      MockTokenizer)
    with pytest.raises(ValueError, match="does not satisfy"):
        RAGFactory(registry).build_keyword(settings("readonly", "mock"), BINDINGS)
    with pytest.raises(ValueError, match="Duplicate provider"):
        registry.register(ProviderDescriptor("tokenizer", "mock"), MockTokenizer)


def test_bad_implementation_does_not_pass_runtime_contract():
    registry = ServiceRegistry()
    registry.register(ProviderDescriptor("keyword_store", "broken", frozenset({"upsert", "search"})),
                      lambda: object())
    registry.register(ProviderDescriptor("tokenizer", "regex", frozenset({"tokenize"})),
                      RegexTokenizer)
    with pytest.raises(TypeError, match="does not implement"):
        RAGFactory(registry).build_keyword(settings("broken"), BINDINGS)
