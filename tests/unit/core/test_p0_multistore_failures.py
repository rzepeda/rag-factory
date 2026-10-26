"""P0: multi-provider partial writes cannot publish successful index metadata."""
from dataclasses import replace

import pytest

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.factory.service_registry import ServiceConfig
from rag_factory.factory.unified import UnifiedConfiguration, build_unified
from tests.mocks.services import MockKeywordStore, MockDocumentStore, MockGraphStore
from tests.unit.core.test_unified_all_strategies import setup
from tests.unit.core.test_p0_index_contracts import all_indexed


class PartialKeyword(MockKeywordStore):
    def upsert(self, documents):
        super().upsert(documents)
        raise RuntimeError("injected keyword write error")


class PartialDocuments(MockDocumentStore):
    def upsert(self, documents):
        super().upsert(documents)
        raise RuntimeError("injected document write error")


class PartialGraph(MockGraphStore):
    def add_edge(self, source, target):
        super().add_edge(source, target)
        raise RuntimeError("injected graph write error")


@pytest.mark.parametrize("kind,interface,broken,payload", [
    ("hierarchical", "keyword_store", PartialKeyword,
     {"parents": {"parent": "cat parent"}, "children": {"child": "cat"},
      "child_to_parent": {"child": "parent"}}),
    ("contextual", "document_store", PartialDocuments,
     {"chunks": {"chunk": "cat"}, "source_document": "cats are pets"}),
    ("knowledge_graph", "graph_store", PartialGraph,
     {"documents": {"a": "cat", "b": "dog"}, "edges": [("a", "b")]}),
])
def test_partial_multistore_write_has_no_attached_artifact(kind, interface, broken, payload):
    registry, services = setup()
    instance = broken()
    descriptor = registry.descriptor(services[interface])
    registry.register(
        ProviderDescriptor(interface, "partial", descriptor.capabilities),
        lambda: instance,
    )
    services[interface] = ServiceConfig(interface, "partial")
    config = UnifiedConfiguration(services, {"indexed": all_indexed()[kind]})
    with build_unified(config, registry) as pipeline:
        with pytest.raises(RuntimeError, match="injected"):
            pipeline.index("indexed", payload)
        assert "indexed" not in pipeline._artifacts
        assert "indexed" not in pipeline._hierarchies
        with pytest.raises(ValueError, match="Missing index artifact"):
            pipeline.retrieve("indexed", "cat")
        # The provider *did* change; only metadata publication is protected.
        assert instance.documents if interface == "document_store" else (
            instance.edges if interface == "graph_store" else instance.documents
        )
