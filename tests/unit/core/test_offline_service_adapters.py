"""Provider-neutral test coverage for new offline adapters."""
from rag_factory.services.graph.memory import MemoryGraphStore
from rag_factory.services.document.memory import MemoryDocumentStore
from rag_factory.services.vector.memory import MemoryVectorStore
from rag_factory.factory.service_registry import default_registry, ServiceConfig

def test_memory_graph_and_document_provider_contracts():
    registry = default_registry()
    _, graph = registry.resolve(ServiceConfig("graph_store", "memory"))
    _, docs = registry.resolve(ServiceConfig("document_store", "memory"))
    assert isinstance(graph, MemoryGraphStore)
    assert isinstance(docs, MemoryDocumentStore)
    graph.add_edge("a", "b")
    graph.add_edge("a", "b")
    assert graph.neighbors("a") == ["b"]
    docs.upsert({"b": "body"})
    assert docs.get("b") == "body"

def test_memory_vector_provider_contract():
    _, store = default_registry().resolve(ServiceConfig("vector_store", "memory"))
    assert isinstance(store, MemoryVectorStore)
    store.upsert({"a": [1., 2.], "b": [3., 4.]})
    assert store.search([1., 2.], 2) == ["a", "b"]
