"""Configuration-defined semantic strategy with offline mock providers."""

import pytest

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.rag_factory import RAGFactory
from rag_factory.factory.service_registry import ServiceConfig, ServiceRegistry
from tests.mocks.services import MockEmbedding, MockVectorStore


def _registry():
    registry = ServiceRegistry()
    registry.register(
        ProviderDescriptor("embedding", "fake", frozenset({"embed"})),
        MockEmbedding,
    )
    registry.register(
        ProviderDescriptor("vector_store", "fake", frozenset({"upsert", "search"})),
        MockVectorStore,
    )
    return registry


def _configs():
    return {
        "emb": ServiceConfig("embedding", "fake"),
        "vectors": ServiceConfig("vector_store", "fake"),
    }


def _bindings():
    return {"embedding": "emb", "vector_store": "vectors"}


def test_semantic_factory_uses_configured_mocks():
    with RAGFactory(_registry()).build_semantic(
        _configs(), _bindings(), "mock-model-v1"
    ) as pipeline:
        artifact = pipeline.indexer.index({"a": "cat", "b": "elephant"}, "idx")
        assert pipeline.retriever.retrieve("cat", artifact, 1) == ["a"]


def test_semantic_factory_checks_capabilities_before_construction():
    constructed = []
    registry = ServiceRegistry()
    registry.register(
        ProviderDescriptor("embedding", "fake", frozenset({"embed"})),
        lambda: constructed.append("created") or MockEmbedding(),
    )
    registry.register(
        ProviderDescriptor("vector_store", "read_only", frozenset({"search"})),
        MockVectorStore,
    )
    config = _configs()
    config["vectors"] = ServiceConfig("vector_store", "read_only")
    with pytest.raises(ValueError, match="does not satisfy"):
        RAGFactory(registry).build_semantic(config, _bindings(), "mock-model-v1")
    assert constructed == []
