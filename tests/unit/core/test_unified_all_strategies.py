"""Smoke-test every unified strategy kind with offline providers."""
import pytest

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.service_registry import ServiceRegistry, ServiceConfig
from rag_factory.factory.unified import (
    StrategySpec, UnifiedConfiguration, build_unified, RetrievalHit, normalize_hits,
)
from rag_factory.factory.unified_config import load_unified_config
from rag_factory.core.artifact_catalog import save_manifests, load_manifests
from tests.mocks.services import (
    MockKeywordStore, MockTokenizer, MockEmbedding, MockVectorStore,
    MockDocumentStore, MockGraphStore, MockReranker, MockLLM,
)


class ContextEncoder:
    def encode_tokens(self, tokens):
        return [[float(len(tokens)), float(i)] for i in range(len(tokens))]


def setup():
    implementations = {
        "keyword_store": (MockKeywordStore, {"upsert", "search"}),
        "tokenizer": (MockTokenizer, {"tokenize"}),
        "embedding": (MockEmbedding, {"embed"}),
        "vector_store": (MockVectorStore, {"upsert", "search"}),
        "document_store": (MockDocumentStore, {"upsert", "get"}),
        "graph_store": (MockGraphStore, {"add_edge", "neighbors"}),
        "reranker": (MockReranker, {"rerank"}),
        "llm": (lambda: MockLLM("YES"), {"generate"}),
        "contextual_token_encoder": (ContextEncoder, {"encode_tokens"}),
    }
    registry = ServiceRegistry()
    for interface, (factory, capabilities) in implementations.items():
        registry.register(ProviderDescriptor(interface, "mock", frozenset(capabilities)), factory)
    return registry, {key: ServiceConfig(key, "mock") for key in implementations}


def spec(kind, indexing=(), retrieval=(), **params):
    return StrategySpec(
        kind, {key: key for key in indexing},
        {key: key for key in retrieval}, params,
    )


def test_all_twelve_strategy_families():
    registry, services = setup()
    specs = {
        "keyword": spec("keyword", ["keyword_store"], ["keyword_store", "tokenizer"]),
        "semantic": spec("semantic", ["embedding", "vector_store"], ["embedding", "vector_store"], embedding_model="mock"),
        "contextual": spec("contextual", ["llm", "keyword_store", "document_store"], ["keyword_store", "document_store", "tokenizer"]),
        "hierarchy": spec("hierarchical", ["keyword_store", "document_store"], ["keyword_store", "document_store", "tokenizer"]),
        "graph": spec("knowledge_graph", ["graph_store", "document_store"], ["graph_store", "document_store"]),
        "late": spec("late_chunking", ["contextual_token_encoder", "vector_store"], ["embedding", "vector_store"], embedding_model="mock"),
        "rerank": spec("reranking", retrieval=["document_store", "reranker"], source="keyword"),
        "multi": spec("multi_query", retrieval=["llm"], source="keyword", max_variants=1),
        "expand": spec("query_expansion", retrieval=["llm"], source="keyword", max_variants=1),
        "reflect": spec("self_reflective", retrieval=["llm", "document_store"], source="keyword"),
        "agent": spec("agentic", retrieval=["llm"], sources=["keyword"]),
        "hybrid": spec("hybrid", sources=["keyword", "semantic"]),
    }
    with build_unified(UnifiedConfiguration(services, specs), registry) as pipeline:
        inputs = {
            "keyword": {"documents": {"a": "cat", "b": "dog"}},
            "semantic": {"documents": {"a": "cat", "b": "dog"}},
            "contextual": {"chunks": {"ctx": "cat"}, "source_document": "cat is a pet"},
            "hierarchy": {"parents": {"parent": "cat parent"}, "children": {"child": "cat"}, "child_to_parent": {"child": "parent"}},
            "graph": {"documents": {"node": "cat", "leaf": "dog"}, "edges": [("node", "leaf")]},
            "late": {"tokens": ["one", "two", "three"], "spans": {"first": (0, 2), "second": (2, 3)}},
        }
        for name, payload in inputs.items():
            assert pipeline.index(name, payload).artifact_id
        for name in ("keyword", "semantic", "contextual", "hierarchy", "graph", "late", "rerank", "multi", "expand", "reflect", "hybrid"):
            query = "node" if name == "graph" else "cat"
            assert isinstance(pipeline.retrieve(name, query), list)
        pipeline._instances["llm"].response = "keyword"
        assert pipeline.retrieve("agent", "cat")
    with pytest.raises(RuntimeError, match="closed"):
        pipeline.retrieve("keyword", "cat")


def test_stage_binding_separation_and_manifest_catalog(tmp_path):
    registry, _ = setup()
    path = tmp_path / "rag.yaml"
    path.write_text("""
services:
  writer: {interface: keyword_store, implementation: mock}
  reader: {interface: keyword_store, implementation: mock}
  tokens: {interface: tokenizer, implementation: mock}
strategies:
  lexical:
    kind: keyword
    indexing: {keyword_store: writer}
    retrieval: {keyword_store: reader, tokenizer: tokens}
""")
    config = load_unified_config(path)
    with build_unified(config, registry) as pipeline:
        artifact = pipeline.index("lexical", {"documents": {"a": "cat"}})
        save_manifests(tmp_path / "artifacts.json", {"lexical": artifact})
        pipeline.attach_artifacts(load_manifests(tmp_path / "artifacts.json"))
        assert pipeline.retrieve("lexical", "cat") == []


def test_rejects_cycles_unknown_references_and_bad_shapes():
    registry, services = setup()
    with pytest.raises(ValueError, match="Cyclic"):
        build_unified(UnifiedConfiguration(services, {
            "a": spec("hybrid", sources=["b"]), "b": spec("hybrid", sources=["a"]),
        }), registry)
    with pytest.raises(ValueError, match="invalid source"):
        build_unified(UnifiedConfiguration(services, {
            "a": spec("reranking", retrieval=["document_store", "reranker"], source="missing"),
        }), registry)
    assert normalize_hits(["a", ("a", "different"), ("b", "body")]) == [
        RetrievalHit("a"), RetrievalHit("b", "body")
    ]
    with pytest.raises(TypeError):
        normalize_hits([42])
