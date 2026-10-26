"""Reusable behavioral conformance checks for provider-neutral interfaces.

Pass a *fresh-instance factory* to avoid state leaking between tests.
These are lightweight offline baselines, not external connectivity or security tests.
"""
from collections.abc import Callable
from math import isfinite

from rag_factory.core.interfaces import services


def check_provider_contract(interface: str, factory: Callable[[], object]) -> None:
    """Run interface-level smoke contracts, raising AssertionError on violations."""
    protocols = {
        "keyword_store": services.KeywordStoreService,
        "tokenizer": services.TokenizerService,
        "embedding": services.EmbeddingService,
        "vector_store": services.VectorStoreService,
        "document_store": services.DocumentStoreService,
        "graph_store": services.GraphStoreService,
        "llm": services.LLMService,
        "reranker": services.RerankerService,
    }
    if interface not in protocols:
        raise ValueError(f"Unknown provider contract interface: {interface}")
    if not callable(factory):
        raise TypeError("Provider factory must be callable")
    provider = factory()
    try:
        assert isinstance(provider, protocols[interface]), (
            f"{interface} provider does not expose required operations"
        )
        if interface == "keyword_store":
            provider.upsert({"match": "cats purr", "other": "dogs bark"})
            hits = list(provider.search(["cats"], 3))
            assert hits and hits[0] == "match" and "other" not in hits
            provider.upsert({"match": "dogs bark"})
            assert "match" not in list(provider.search(["cats"], 3))
            assert list(provider.search([], 3)) == []
        elif interface == "tokenizer":
            assert list(provider.tokenize("Cats cats")) == ["cats", "cats"]
            assert list(provider.tokenize("")) == []
        elif interface == "embedding":
            assert list(provider.embed([])) == []
            output = list(provider.embed(["cats", "dogs"]))
            assert len(output) == 2
            widths = [len(vector) for vector in output]
            assert widths[0] > 0 and widths[0] == widths[1]
            assert all(isfinite(number) for vector in output for number in vector)
            assert output == list(provider.embed(["cats", "dogs"]))
        elif interface == "vector_store":
            provider.upsert({"near": [0., 0.], "far": [4., 4.]})
            assert list(provider.search([0., 0.], 2))[0] == "near"
            provider.upsert({"far": [0., 0.]})
            assert set(provider.search([0., 0.], 2)) == {"far", "near"}
        elif interface == "document_store":
            assert provider.get("missing") is None
            provider.upsert({"a": "original"})
            assert provider.get("a") == "original"
            provider.upsert({"a": "replacement"})
            assert provider.get("a") == "replacement"
        elif interface == "graph_store":
            assert list(provider.neighbors("missing")) == []
            provider.add_edge("a", "b")
            provider.add_edge("a", "b")
            provider.add_edge("a", "c")
            assert set(provider.neighbors("a")) == {"b", "c"}
            assert len(list(provider.neighbors("a"))) == 2
        elif interface == "llm":
            assert isinstance(provider.generate("short question"), str)
            assert isinstance(provider.generate("different question"), str)
        elif interface == "reranker":
            candidates = {"a": "cats", "b": "dogs"}
            ranked = list(provider.rerank("cats", candidates))
            assert len(ranked) == 2 and set(ranked) == set(candidates), (
                "Reranker must return exactly the candidate IDs"
            )
    finally:
        closer = getattr(provider, "close", None)
        if callable(closer):
            closer()
