"""End-to-end offline YAML workflow, provider validation and lifecycle."""

import pytest

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.runtime import build_pipeline, PipelineConfiguration
from rag_factory.factory.runtime_config import load_pipeline_config
from rag_factory.factory.service_registry import ServiceRegistry, ServiceConfig
from tests.mocks.services import MockEmbedding, MockVectorStore, MockKeywordStore, MockTokenizer


def registry():
    reg = ServiceRegistry()
    reg.register(ProviderDescriptor("embedding", "mock", frozenset({"embed"})), MockEmbedding)
    reg.register(ProviderDescriptor("vector_store", "mock", frozenset({"upsert", "search"})), MockVectorStore)
    reg.register(ProviderDescriptor("keyword_store", "mock", frozenset({"upsert", "search"})), MockKeywordStore)
    reg.register(ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})), MockTokenizer)
    return reg


def config():
    return PipelineConfiguration(
        services={
            "tokens": ServiceConfig("tokenizer", "mock"),
            "keywords": ServiceConfig("keyword_store", "mock"),
            "emb": ServiceConfig("embedding", "mock"),
            "vectors": ServiceConfig("vector_store", "mock"),
        },
        bindings={
            "tokenizer": "tokens", "keyword_store": "keywords",
            "embedding": "emb", "vector_store": "vectors",
        },
        strategies=("keyword", "semantic"),
        embedding_model="mock-v1",
    )


def test_hybrid_pipeline_indexes_and_retrieves_with_shared_services():
    with build_pipeline(config(), registry()) as pipeline:
        artifacts = pipeline.index({"a": "cat", "b": "dog", "c": "cat cat"})
        assert set(artifacts) == {"keyword", "semantic"}
        assert artifacts["semantic"].embedding_model == "mock-v1"
        results = pipeline.retrieve("cat", 3)
        assert results[0] == "a"
        assert set(results) == {"a", "b", "c"}
    with pytest.raises(RuntimeError, match="closed"):
        pipeline.retrieve("cat")


def test_semantic_requires_index_before_retrieval():
    with build_pipeline(config(), registry()) as pipeline:
        with pytest.raises(ValueError, match="index first"):
            pipeline.retrieve("cat")


def test_yaml_configuration_and_keyword_execution(tmp_path):
    path = tmp_path / "rag.yaml"
    path.write_text("""
services:
  keywords:
    interface: keyword_store
    implementation: mock
  tokenizer:
    interface: tokenizer
    implementation: mock
pipeline:
  strategies: [keyword]
  bindings:
    keyword_store: keywords
    tokenizer: tokenizer
""")
    cfg = load_pipeline_config(path)
    with build_pipeline(cfg, registry()) as pipeline:
        pipeline.index({"a": "cat", "b": "dog"})
        assert pipeline.retrieve("cat") == ["a"]


def test_missing_capability_fails_without_constructing():
    constructed = []
    reg = ServiceRegistry()
    reg.register(
        ProviderDescriptor("tokenizer", "mock", frozenset({"tokenize"})),
        lambda: constructed.append("tokenizer") or MockTokenizer(),
    )
    reg.register(
        ProviderDescriptor("keyword_store", "readonly", frozenset({"search"})),
        MockKeywordStore,
    )
    cfg = PipelineConfiguration(
        {"tokens": ServiceConfig("tokenizer", "mock"),
         "keywords": ServiceConfig("keyword_store", "readonly")},
        {"tokenizer": "tokens", "keyword_store": "keywords"},
        ("keyword",),
    )
    with pytest.raises(ValueError, match="does not satisfy"):
        build_pipeline(cfg, reg)
    assert constructed == []


def test_missing_provider_unknown_strategy_and_bad_yaml(tmp_path):
    with pytest.raises(ValueError, match="Unsupported"):
        PipelineConfiguration({}, {}, ("unknown",))
    with pytest.raises(ValueError, match="embedding_model"):
        PipelineConfiguration({}, {}, ("semantic",))
    path = tmp_path / "bad.yaml"
    path.write_text("pipeline: []")
    with pytest.raises(ValueError, match="Expected"):
        load_pipeline_config(path)
