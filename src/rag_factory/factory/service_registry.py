"""Explicit provider registry; metadata validation before instantiation."""

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from rag_factory.core.service_contracts import ProviderDescriptor


@dataclass(frozen=True)
class ServiceConfig:
    interface: str
    implementation: str
    parameters: Mapping[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    def __init__(self):
        self._providers: dict[tuple[str, str], tuple[ProviderDescriptor, Callable[..., object]]] = {}

    def register(self, descriptor: ProviderDescriptor, constructor: Callable[..., object]) -> None:
        key = (descriptor.interface, descriptor.implementation)
        if key in self._providers:
            raise ValueError(f"Duplicate provider registration: {key}")
        self._providers[key] = (descriptor, constructor)

    def descriptor(self, config: ServiceConfig) -> ProviderDescriptor:
        key = (config.interface, config.implementation)
        if key not in self._providers:
            raise ValueError(f"Unknown provider: {key}")
        return self._providers[key][0]

    def resolve(self, config: ServiceConfig) -> tuple[ProviderDescriptor, object]:
        descriptor = self.descriptor(config)
        return descriptor, self._providers[(config.interface, config.implementation)][1](**config.parameters)


def default_registry() -> ServiceRegistry:
    from rag_factory.services.keyword.memory import MemoryKeywordStore
    from rag_factory.services.tokenizer.regex import RegexTokenizer

    from rag_factory.services.document.memory import MemoryDocumentStore
    from rag_factory.services.graph.memory import MemoryGraphStore
    from rag_factory.services.vector.memory import MemoryVectorStore

    registry = ServiceRegistry()
    registry.register(
        ProviderDescriptor("keyword_store", "memory", frozenset({"upsert", "search"})),
        MemoryKeywordStore,
    )
    registry.register(
        ProviderDescriptor("tokenizer", "regex", frozenset({"tokenize"})),
        RegexTokenizer,
    )
    registry.register(
        ProviderDescriptor("document_store", "memory", frozenset({"upsert", "get"})),
        MemoryDocumentStore,
    )
    registry.register(
        ProviderDescriptor("graph_store", "memory", frozenset({"add_edge", "neighbors"})),
        MemoryGraphStore,
    )
    registry.register(
        ProviderDescriptor("vector_store", "memory", frozenset({"upsert", "search"})),
        MemoryVectorStore,
    )
    return registry
