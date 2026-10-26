"""P0: reject malformed strategies before constructing external providers."""
import pytest
from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration, build_unified
from rag_factory.factory.service_registry import ServiceRegistry

@pytest.mark.parametrize("kind,parameters,error", [
    ("hybrid", {"sources": ["leaf", "leaf"]}, "duplicate"),
    ("graph_vector_hybrid", {"sources": ["leaf"]}, "exactly two"),
    ("agentic", {"sources": ["leaf"], "max_steps": 0}, "max_steps"),
    ("hybrid", {"sources": ["leaf"], "rank_constant": 0}, "rank_constant"),
    ("hybrid", {"sources": ["leaf"], "rank_constant": True}, "rank_constant"),
])
def test_invalid_composite_rejected_without_provider_creation(kind, parameters, error):
    config = UnifiedConfiguration({}, {
        "leaf": StrategySpec("hybrid", parameters={"sources": ["other"]}),
        "other": StrategySpec("hybrid", parameters={"sources": ["leaf"]}),
        "root": StrategySpec(kind, parameters=parameters),
    })
    with pytest.raises(ValueError, match=error):
        build_unified(config, ServiceRegistry())

def test_bad_semantic_threshold_rejected_before_providers():
    from rag_factory.core.service_contracts import ProviderDescriptor
    from rag_factory.factory.service_registry import ServiceConfig
    registry = ServiceRegistry()
    constructed = []
    registry.register(ProviderDescriptor("embedding", "mock", frozenset({"embed"})),
                      lambda: constructed.append("embedding"))
    registry.register(ProviderDescriptor("vector_store", "mock", frozenset({"upsert", "search"})),
                      lambda: constructed.append("vector"))
    config = UnifiedConfiguration({
        "emb": ServiceConfig("embedding", "mock"),
        "vec": ServiceConfig("vector_store", "mock"),
    }, {"chunk": StrategySpec("semantic_chunking",
        {"embedding": "emb", "vector_store": "vec"},
        {"embedding": "emb", "vector_store": "vec"},
        {"embedding_model": "test", "threshold": 1.5})})
    with pytest.raises(ValueError, match="threshold"):
        build_unified(config, registry)
    assert constructed == []
