"""P0: all 16 unified strategy kinds work together with offline providers."""
from dataclasses import replace

import pytest

from rag_factory.factory.service_registry import ServiceConfig
from rag_factory.factory.unified import RetrievalHit, UnifiedConfiguration, build_unified
from tests.unit.core.test_unified_all_strategies import setup, spec


def test_all_strategy_variants_in_one_offline_pipeline():
    registry, services = setup()
    strategies = {
        "keyword": spec("keyword", ["keyword_store"], ["keyword_store", "tokenizer"]),
        "semantic": spec("semantic", ["embedding", "vector_store"],
                         ["embedding", "vector_store"], embedding_model="mock"),
        "boundary": spec("semantic_chunking", ["embedding", "vector_store"],
                         ["embedding", "vector_store"], embedding_model="mock", max_sentences=1),
        "contextual": spec("contextual", ["llm", "keyword_store", "document_store"],
                           ["keyword_store", "document_store", "tokenizer"]),
        "hierarchical": spec("hierarchical", ["keyword_store", "document_store"],
                             ["keyword_store", "document_store", "tokenizer"]),
        "graph": spec("knowledge_graph", ["graph_store", "document_store"],
                      ["graph_store", "document_store"]),
        "late": spec("late_chunking", ["contextual_token_encoder", "vector_store"],
                     ["embedding", "vector_store"], embedding_model="mock"),
        "rerank": spec("reranking", retrieval=["document_store", "reranker"], source="keyword"),
        "multi": spec("multi_query", retrieval=["llm"], source="keyword", max_variants=1),
        "expand": spec("query_expansion", retrieval=["llm"], source="keyword", max_variants=1),
        "reflect": spec("self_reflective", retrieval=["llm", "document_store"], source="keyword"),
        "agent": spec("agentic", retrieval=["llm"], sources=["keyword"]),
        "hybrid": spec("hybrid", sources=["keyword", "semantic"]),
        "hyde": spec("hyde", retrieval=["llm"], source="keyword"),
        "rewrite": spec("query_refinement", retrieval=["llm"], source="keyword", max_rewrites=1),
        "graph_vector": spec("graph_vector_hybrid", sources=["graph", "semantic"]),
    }
    # Keep each indexed family's mutable in-memory data isolated.
    for name, interfaces in {
        "contextual": ("keyword_store", "document_store"),
        "hierarchical": ("keyword_store", "document_store"),
        "graph": ("document_store",),
        "late": ("vector_store",),
        "boundary": ("vector_store",),
    }.items():
        base = strategies[name]
        indexing, retrieval = dict(base.indexing), dict(base.retrieval)
        for interface in interfaces:
            binding = name + "_" + interface
            services[binding] = ServiceConfig(interface, "mock")
            if interface in indexing:
                indexing[interface] = binding
            if interface in retrieval:
                retrieval[interface] = binding
        strategies[name] = replace(base, indexing=indexing, retrieval=retrieval)

    inputs = {
        "keyword": {"documents": {"a": "cat", "b": "dog"}},
        "semantic": {"documents": {"vector-a": "cat"}},
        "boundary": {"documents": {"boundary-doc": "Cat naps. Dog runs."}},
        "contextual": {"chunks": {"ctx": "cat"}, "source_document": "cat is an animal"},
        "hierarchical": {"parents": {"parent": "cat parent"}, "children": {"child": "cat"},
                         "child_to_parent": {"child": "parent"}},
        "graph": {"documents": {"node": "cat", "leaf": "dog"}, "edges": [("node", "leaf")]},
        "late": {"tokens": ["cat", "dog"], "spans": {"first": (0, 1), "second": (1, 2)}},
    }
    with build_unified(UnifiedConfiguration(services, strategies), registry) as pipeline:
        with pytest.raises(ValueError, match="Missing index artifact"):
            pipeline.retrieve("keyword", "cat")
        pipeline._instances["document_store"].upsert({"a": "cat", "b": "dog"})
        for name, payload in inputs.items():
            assert pipeline.index(name, payload).artifact_id
        assert set(pipeline._artifacts) == set(inputs)

        pipeline._instances["llm"].response = "YES"
        assert pipeline.retrieve("reflect", "cat")[0].document_id == "a"

        pipeline._instances["llm"].response = "keyword"
        assert pipeline.retrieve("agent", "cat")[0].document_id == "a"

        pipeline._instances["llm"].response = "cat"
        for name in ("keyword", "semantic", "boundary", "contextual", "hierarchical",
                     "graph", "late", "rerank", "multi", "expand", "hybrid",
                     "hyde", "rewrite", "graph_vector"):
            query = "node" if name in ("graph", "graph_vector") else "cat"
            first = pipeline.retrieve(name, query, limit=3)
            second = pipeline.retrieve(name, query, limit=3)
            assert first, name
            assert first == second, name
            assert len(first) <= 3
            assert all(isinstance(hit, RetrievalHit) for hit in first)
        assert pipeline.retrieve("rewrite", "not-a-match")[0].document_id == "a"
    with pytest.raises(RuntimeError, match="closed"):
        pipeline.retrieve("keyword", "cat")
